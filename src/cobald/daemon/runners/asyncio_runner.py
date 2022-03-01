from typing import Optional, Callable, Awaitable
import asyncio

from .base_runner import BaseRunner
from .async_tools import OrphanedReturn, ensure_coroutine
from ._compat import asyncio_current_task


class AsyncioRunner(BaseRunner):
    """
    Runner for coroutines with :py:mod:`asyncio`

    All active payloads are actively cancelled when the runner is closed.
    """

    flavour = asyncio

    def __init__(self, asyncio_loop: asyncio.AbstractEventLoop):
        super().__init__(asyncio_loop)
        self._tasks = set()
        self._failure_queue: Optional[asyncio.Queue] = None

    def register_payload(self, payload: Callable[[], Awaitable]):
        self.asyncio_loop.call_soon_threadsafe(self._setup_payload, payload)

    def run_payload(self, payload: Callable[[], Awaitable]):
        future = asyncio.run_coroutine_threadsafe(
            ensure_coroutine(payload()), self.asyncio_loop
        )
        return future.result()

    def _setup_payload(self, payload: Callable[[], Awaitable]):
        task = self.asyncio_loop.create_task(self._monitor_payload(payload))
        self._tasks.add(task)

    async def _monitor_payload(self, payload: Callable[[], Awaitable]):
        try:
            result = payload()
        except BaseException as e:
            failure = e
        else:
            if result is None:
                return
            failure = OrphanedReturn(payload, result)
        finally:
            self._tasks.discard(asyncio_current_task())
        assert self._failure_queue is not None
        await self._failure_queue.put(failure)

    async def manage_payloads(self):
        self._failure_queue = asyncio.Queue()
        failure = await self._failure_queue.get()
        if failure is not None:
            raise failure

    async def aclose(self):
        self._running.clear()
        await self._failure_queue.put(None)
        while self._tasks:
            for task in self._tasks.copy():
                if task.done():
                    self._tasks.discard(task)
                task.cancel()
            await asyncio.sleep(0.5)
