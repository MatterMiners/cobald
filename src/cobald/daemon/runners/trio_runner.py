import trio
from functools import partial


from .base_runner import BaseRunner
from .async_tools import raise_return, AsyncExecution


class TrioRunner(BaseRunner):
    """Runner for coroutines with :py:mod:`trio`"""

    flavour = trio

    def __init__(self):
        self._nursery = None
        super().__init__()

    def register_payload(self, payload):
        super().register_payload(partial(raise_return, payload))

    def run_payload(self, payload):
        execution = AsyncExecution(payload)
        super().register_payload(execution.coroutine)
        return execution.wait()

    def _run(self):
        return trio.run(self._await_all)

    async def _await_all(self):
        """Async component of _run"""
        delay = 0.0
        # we run a top-level nursery that automatically reaps/cancels for us
        async with trio.open_nursery() as nursery:
            while self.running.is_set():
                await self._start_payloads(nursery=nursery)
                await trio.sleep(delay)
                delay = min(delay + 0.1, 1.0)
            # cancel the scope to cancel all payloads
            nursery.cancel_scope.cancel()

    async def _start_payloads(self, nursery):
        """Start all queued payloads"""
        with self._lock:
            for coroutine in self._payloads:
                nursery.start_soon(coroutine)
            self._payloads.clear()
        await trio.sleep(0)
