from typing import Optional, Callable, Awaitable
import asyncio

from .base_runner import BaseRunner
from .async_tools import raise_return, ensure_coroutine


class AsyncioRunner(BaseRunner):
    """Runner for coroutines with :py:mod:`asyncio`"""

    flavour = asyncio

    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        super().__init__()
        self.event_loop = loop if loop is not None else asyncio.new_event_loop()
        self._tasks = set()

    def register_payload(self, payload: Callable[[], Awaitable]):
        self.event_loop.call_soon_threadsafe(
            lambda: self._tasks.add(self.event_loop.create_task(raise_return(payload)))
        )

    def run_payload(self, payload: Callable[[], Awaitable]):
        future = asyncio.run_coroutine_threadsafe(
            ensure_coroutine(payload()), self.event_loop
        )
        return future.result()

    async def manage_payloads(self):
        # Remove tracked tasks and raise if tasks leak
        while self._tasks or self._running.is_set():
            # let asyncio efficiently wait for errors
            # we only force wake up via timeout every now and then to clean up
            done, pending = await asyncio.wait(
                self._tasks, timeout=60, return_when=asyncio.FIRST_EXCEPTION
            )
            self._tasks.difference_update(done)
            for task in done:
                # re-raise any exceptions
                task.result()

    async def aclose(self):
        self._running.clear()
        while self._tasks:
            for task in self._tasks.copy():
                if task.done():
                    self._tasks.remove(task)
                task.cancel()
            await asyncio.sleep(0.5)

    def stop(self):
        if not self._running.wait(0.2):
            return
        # the loop exists independently of this runner, we can use it to shut down
        closed = asyncio.run_coroutine_threadsafe(self.aclose(), self.event_loop)
        closed.result()
