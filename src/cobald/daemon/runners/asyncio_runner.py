from typing import Callable, Awaitable, Coroutine
import asyncio

from .base_runner import BaseRunner, OrphanedReturn
from ._compat import asyncio_current_task


class AsyncioRunner(BaseRunner):
    """
    Runner for coroutines with :py:mod:`asyncio`

    All active payloads are actively cancelled when the runner is closed.
    """

    flavour = asyncio

    # This runner directly uses asyncio.Task to run payloads.
    # To detect errors, each payload is wrapped; errors and unexpected return values
    # are pushed to a queue from which the main task re-raises.
    # Tasks are registered in a container to allow cancelling them. The payload wrapper
    # takes care of adding/removing tasks.
    def __init__(self, asyncio_loop: asyncio.AbstractEventLoop):
        super().__init__(asyncio_loop)
        self._tasks = set()
        self._failure_queue = asyncio.Queue()

    def register_payload(self, payload: Callable[[], Awaitable]):
        self.asyncio_loop.call_soon_threadsafe(self._setup_payload, payload)

    def run_payload(self, payload: Callable[[], Coroutine]):
        future = asyncio.run_coroutine_threadsafe(payload(), self.asyncio_loop)
        return future.result()

    def _setup_payload(self, payload: Callable[[], Awaitable]):
        task = self.asyncio_loop.create_task(self._monitor_payload(payload))
        self._tasks.add(task)

    async def _monitor_payload(self, payload: Callable[[], Awaitable]):
        try:
            result = await payload()
        except asyncio.CancelledError:
            raise
        except BaseException as e:
            failure = e
        else:
            if result is None:
                return
            failure = OrphanedReturn(payload, result)
        finally:
            self._tasks.discard(asyncio_current_task())
        await self._failure_queue.put(failure)

    async def manage_payloads(self):
        failure = await self._failure_queue.get()
        if failure is not None:
            raise failure

    async def aclose(self):
        if self._stopped.is_set():
            return
        # let the manage task wake up and exit
        await self._failure_queue.put(None)
        while self._tasks:
            for task in self._tasks.copy():
                if task.done():
                    self._tasks.discard(task)
                else:
                    task.cancel()
            await asyncio.sleep(0.1)
