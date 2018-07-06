import trio


from .base_runner import CoroutineRunner, OrphanedReturn


async def return_trap(payload):
    """Wrapper to raise exception on unhandled return values"""
    value = await payload
    if value is not None:
        raise OrphanedReturn(payload, value)


class TrioRunner(CoroutineRunner):
    """Runner for coroutines of :py:mod:`trio`"""
    flavour = trio

    def __init__(self):
        self._nursery = None
        super().__init__()

    def _run(self):
        return trio.run(self.await_all)

    async def await_all(self):
        async with trio.open_nursery() as nursery:
            while self._running.is_set():
                await self._start_outstanding(nursery=nursery)
                await trio.sleep(1)

    async def _start_outstanding(self, nursery):
        with self._lock:
            for coroutine in self._payloads:
                nursery.start_soon(return_trap, coroutine())
            self._payloads.clear()
        await trio.sleep(0)
