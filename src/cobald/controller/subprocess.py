import asyncio
import logging
from typing import List

from cobald.daemon import service
from cobald.interfaces import Controller, Pool
from cobald.utility import InvariantError, enforce

logger = logging.getLogger("cobald.controller.subprocess")


@service(flavour=asyncio)
class SubprocessController(Controller):
    """
    Controller that sets demand from a continuous stream of values emitted by an
    external command

    The ``command`` is repeatedly run as a subprocess. Each line the subprocess
    writes to stdout is parsed as a ``float`` and applied as the new demand of
    ``target``. A line that cannot be parsed, or a negative demand, is treated
    as an invariant violation and crashes the service -- this is deliberate,
    since malformed output usually indicates a persistent bug in ``command``
    that restarting will not fix, and a crash is far more likely to be noticed
    than a warning buried in a log file. If the subprocess itself exits or
    fails to start, it is restarted after waiting ``restart_delay`` seconds.

    :param target: the pool to manage
    :param command: command producing demand values on stdout, as a list of
        the executable and its arguments, e.g. ``["python3", "-u", "script.py"]``
    :param restart_delay: delay in seconds before restarting a stopped command
    """

    def __init__(self, target: Pool, command: List[str], restart_delay: float = 3):
        super().__init__(target=target)

        assert restart_delay >= 0, "restart_delay must not be negative"

        self.command = command
        self.restart_delay = restart_delay

    async def run(self):
        while True:
            try:
                await self._stream_demand()
            except InvariantError:
                # a strict violation of the demand contract: retrying would
                # just repeat the same failure, so let this crash the service
                raise
            except Exception:
                logger.exception("subprocess controller subprocess failed")
            await asyncio.sleep(self.restart_delay)

    async def _stream_demand(self):
        proc = await asyncio.create_subprocess_exec(
            *self.command,
            stdout=asyncio.subprocess.PIPE,
        )

        try:
            # stream demand
            async for line in proc.stdout:
                try:
                    demand = float(line.decode().strip())
                except (ValueError, TypeError) as e:
                    raise InvariantError(
                        f"could not parse demand from line {line!r}"
                    ) from e
                enforce(
                    demand >= 0, InvariantError(f"received negative demand {demand!r}")
                )
                self.target.demand = demand
            # wait for process to finish
            await proc.wait()
        finally:
            # in case of not finishing properly, ensure proper temrination
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
