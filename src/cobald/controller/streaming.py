import logging
import asyncio

from cobald.interfaces import Pool, Controller
from cobald.utility import enforce, InvariantError

from cobald.daemon import service

logger = logging.getLogger("cobald.controller.streaming")


@service(flavour=asyncio)
class StreamingController(Controller):
    """
    Controller that sets demand from a continuous stream of values emitted by an
    external script

    The ``script`` is repeatedly run as a subprocess via ``interpreter``.
    Each line the subprocess writes to stdout is parsed as a ``float`` and
    applied as the new demand of ``target``; lines that cannot be parsed are
    logged and skipped. Negative values are clamped to ``0`` and logged as a
    warning. If the subprocess exits or fails, it is restarted after waiting
    ``restart_delay`` seconds.

    :param target: the pool to manage
    :param script: path to the script producing demand values on stdout
    :param interpreter: interpreter used to run ``script``
    :param restart_delay: delay in seconds before restarting a stopped script
    """

    def __init__(
        self, target: Pool, script: str, interpreter: str, restart_delay: float = 3
    ):
        super().__init__(target=target)

        enforce(
            restart_delay >= 0, InvariantError("restart_delay must not be negative")
        )

        self.script = script
        self.interpreter = interpreter
        self.restart_delay = restart_delay

    async def run(self):
        while True:
            try:
                await self._stream_demand()
            except Exception:
                logger.exception("streaming controller subprocess failed")
            await asyncio.sleep(self.restart_delay)

    async def _stream_demand(self):
        proc = await asyncio.create_subprocess_exec(
            self.interpreter,
            "-u",
            self.script,
            stdout=asyncio.subprocess.PIPE,
        )

        try:
            # stream demand
            async for line in proc.stdout:
                try:
                    demand = float(line.decode().strip())
                except (ValueError, TypeError) as e:
                    logger.warning(e)
                    continue
                if demand < 0:
                    logger.warning("received negative demand %r, clamping to 0", demand)
                    demand = 0
                self.target.demand = demand
            await proc.wait()
        finally:
            # make sure subprocess is terminated
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
