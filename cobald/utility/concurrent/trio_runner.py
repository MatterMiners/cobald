import trio


from .base_runner import CoroutineRunner


class TrioRunner(CoroutineRunner):
    """Runner for coroutines of :py:mod:`trio`"""
    flavour = trio

    def __init__(self):
        self._nursery = None
        super().__init__()

    def run(self):
        trio.run(self.await_all)

    async def await_all(self):
        self._running.set()
        async with trio.open_nursery() as nursery:
            while self._running.is_set():
                await self._start_outstanding(nursery=nursery)
                await trio.sleep(1)
        self._running.close()

    async def _start_outstanding(self, nursery):
        with self._lock:
            for coroutine in self._payloads:
                nursery.start_soon(coroutine)
            self._payloads.clear()
        await trio.sleep(0)
