import asyncio
from functools import partial

from .base_runner import BaseRunner
from .async_tools import raise_return, AsyncExecution


class AsyncioRunner(BaseRunner):
    """Runner for coroutines with :py:mod:`asyncio`"""

    flavour = asyncio

    def __init__(self):
        super().__init__()
        self.event_loop = asyncio.new_event_loop()
        self._tasks = set()

    def register_payload(self, payload):
        super().register_payload(partial(raise_return, payload))

    def run_payload(self, payload):
        execution = AsyncExecution(payload)
        super().register_payload(execution.coroutine)
        return execution.wait()

    def _run(self):
        asyncio.set_event_loop(self.event_loop)
        self.event_loop.run_until_complete(self._run_payloads())

    async def _run_payloads(self):
        """Async component of _run"""
        delay = 0.0
        try:
            while self.running.is_set():
                await self._start_payloads()
                await self._reap_payloads()
                await asyncio.sleep(delay)
                delay = min(delay + 0.1, 1.0)
        except Exception:
            await self._cancel_payloads()
            raise

    async def _start_payloads(self):
        """Start all queued payloads"""
        with self._lock:
            for coroutine in self._payloads:
                task = self.event_loop.create_task(coroutine())
                self._tasks.add(task)
            self._payloads.clear()
        await asyncio.sleep(0)

    async def _reap_payloads(self):
        """Clean up all finished payloads"""
        for task in self._tasks.copy():
            if task.done():
                self._tasks.remove(task)
                if task.exception() is not None:
                    raise task.exception()
        await asyncio.sleep(0)

    async def _cancel_payloads(self):
        """Cancel all remaining payloads"""
        for task in self._tasks:
            task.cancel()
            await asyncio.sleep(0)
        for task in self._tasks:
            while not task.done():
                await asyncio.sleep(0.1)
                task.cancel()

    def stop(self):
        if not self.running.wait(0.2):
            return
        self._logger.debug("runner disabled: %s", self)
        with self._lock:
            self.running.clear()
            for task in self._tasks:
                task.cancel()
        self._stopped.wait()
        self.event_loop.stop()
        self.event_loop.close()
