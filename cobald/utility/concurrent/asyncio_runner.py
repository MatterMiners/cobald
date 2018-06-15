import asyncio

from .base_runner import CoroutineRunner


class AsyncioRunner(CoroutineRunner):
    flavour = asyncio

    def run(self):
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)
        event_loop.create_task(self.await_all())
        event_loop.run_forever()

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
