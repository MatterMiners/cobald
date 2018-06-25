import asyncio
import time

from .base_runner import CoroutineRunner


class AsyncioRunner(CoroutineRunner):
    flavour = asyncio

    def __init__(self):
        super().__init__()
        self.event_loop = asyncio.new_event_loop()

    def _run(self):
        asyncio.set_event_loop(self.event_loop)
        self.event_loop.create_task(self.await_all())
        self.event_loop.run_forever()

    async def await_all(self):
        self._running.set()
        while self._running.is_set():
            await self._start_outstanding()
            await asyncio.sleep(1)
        self._running.close()

    async def _start_outstanding(self):
        with self._lock:
            coroutines = self._payloads.copy()
            self._payloads.clear()
        if coroutines:
            await asyncio.wait([coro() for coro in coroutines], return_when=asyncio.FIRST_EXCEPTION)

    def stop(self):
        super().stop()
        self.event_loop.stop()
        while self.event_loop.is_running():
            time.sleep(0.1)
        self.event_loop.close()
