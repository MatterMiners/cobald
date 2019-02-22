import trio
from functools import partial


from .base_runner import BaseRunner
from .async_tools import raise_return, AsyncExecution


class TrioRunner(BaseRunner):
    """Runner for coroutines of :py:mod:`trio`"""
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
        return trio.run(self.await_all)

    async def await_all(self):
        delay = 0.0
        async with trio.open_nursery() as nursery:
            while self.running.is_set():
                await self._start_outstanding(nursery=nursery)
                await trio.sleep(delay)
                delay = min(delay + 0.1, 1.0)
            nursery.cancel_scope.cancel()

    async def _start_outstanding(self, nursery):
        with self._lock:
            for coroutine in self._payloads:
                nursery.start_soon(coroutine)
            self._payloads.clear()
        await trio.sleep(0)
