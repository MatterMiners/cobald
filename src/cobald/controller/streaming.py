import logging
import asyncio

from cobald.interfaces import Pool, Controller

from cobald.daemon import service

logger = logging.getLogger("cobald.controller.streaming")

@service(flavour=asyncio)
class StreamingController(Controller):
    def __init__(
            self, target: Pool, script: str, interpreter: str, restart_delay: float = 3):
        super().__init__(target=target)

        assert restart_delay >= 0

        self.script = script
        self.interpreter = interpreter
        self.restart_delay = restart_delay


    async def run(self):
        while True:
            try:
                await self._regulate()
            except Exception as e:
                logger.exception(e)
            await asyncio.sleep(self.restart_delay)

    async def _regulate(self):
        proc = await asyncio.create_subprocess_exec(
            self.interpreter,
            "-u",
            self.script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        value = None

        try:
            async for line in proc.stdout:
                try:
                    value = float(line.decode().strip())
                except (ValueError, TypeError) as e:
                    logger.warning(e)
                    continue
                self.target.demand = value
            await proc.wait()
        finally:
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()






        
