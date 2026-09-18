import asyncio
import logging

from cobald.daemon import service
from cobald.interfaces import Controller, Pool

logger = logging.getLogger("cobald.controller.subprocess")


@service(flavour=asyncio)
class SubprocessController(Controller):
    """
    Controller that sets demand from a continuous stream of values emitted by an
    external command

    The ``command`` is repeatedly run as a subprocess. Each line the subprocess
    writes to stdout is parsed as a ``float`` and applied as the new demand of
    ``target``. If the subprocess exits, fails to start, or writes a line that
    cannot be parsed as a demand, the failure is logged and the command is
    restarted after waiting ``restart_delay`` seconds. If ``restart_delay`` is
    ``None``, the command is not restarted and the failure is raised instead,
    crashing the service.

    ``command`` must write to stdout unbuffered, otherwise demand updates may be delayed.

    :param target: the pool to manage
    :param command: command producing demand values on stdout, as a list of
        the executable and its arguments, e.g. ``["python3", "-u", "script.py"]``
    :param restart_delay: delay in seconds before restarting a stopped command,
        or ``None`` to just let the service crash.
    """

    def __init__(
        self,
        target: Pool,
        command: "list[str]",
        restart_delay: "float | None" = 3,
    ):
        super().__init__(target=target)

        assert (
            restart_delay is None or restart_delay >= 0
        ), "restart_delay must not be negative"

        self.command = command
        self.restart_delay = restart_delay

    async def run(self):
        while True:
            try:
                await self._stream_demand()
            except Exception:
                logger.exception("subprocess controller subprocess failed")
                if self.restart_delay is None:
                    raise
            await asyncio.sleep(self.restart_delay)

    async def _stream_demand(self):
        proc = await asyncio.create_subprocess_exec(
            *self.command,
            stdout=asyncio.subprocess.PIPE,
        )

        try:
            # stream demand
            async for line in proc.stdout:
                self.target.demand = float(line)
            # wait for process to clean up
            await proc.wait()
        finally:
            # in case of not finishing properly, ensure proper termination
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
