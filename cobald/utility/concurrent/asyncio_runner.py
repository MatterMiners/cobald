import asyncio
import time

from .base_runner import CoroutineRunner, OrphanedReturn


async def return_trap(payload):
    """Wrapper to raise exception on unhandled return values"""
    value = await payload
    if value is not None:
        raise OrphanedReturn(payload, value)


class AsyncioRunner(CoroutineRunner):
    flavour = asyncio

    def __init__(self):
        super().__init__()
        self.event_loop = asyncio.new_event_loop()
        self._tasks = set()

    def _run(self):
        asyncio.set_event_loop(self.event_loop)
        self.event_loop.run_until_complete(self.await_all())

    async def await_all(self):
        try:
            while self._running.is_set():
                await self._start_outstanding()
                await self._manage_running()
                await asyncio.sleep(1)
        except Exception:
            await self._cancel_running()
            raise

    async def _start_outstanding(self):
        with self._lock:
            for coroutine in self._payloads:
                task = self.event_loop.create_task(return_trap(coroutine()))
                self._tasks.add(task)
            self._payloads.clear()
        await asyncio.sleep(0)

    async def _manage_running(self):
        for task in self._tasks.copy():
            if task.done():
                self._tasks.remove(task)
                if task.exception() is not None:
                    raise task.exception()
        await asyncio.sleep(0)

    async def _cancel_running(self):
        for task in self._tasks:
            task.cancel()
            await asyncio.sleep(0)
        for task in self._tasks:
            while not task.done():
                await asyncio.sleep(0.1)

    def stop(self):
        super().stop()
        self.event_loop.stop()
        while self.event_loop.is_running():
            time.sleep(0.1)
        self.event_loop.close()
