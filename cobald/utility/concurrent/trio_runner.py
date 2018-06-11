import trio


from .base_runner import CoroutineRunner


class TrioRunner(CoroutineRunner):
    flavour = trio

    def __init__(self):
        self._nursery = None
        super().__init__()

    def run(self):
        trio.run(self.await_all)

    async def await_all(self):
        with trio.open_nursery() as nursery:
            for coroutine in self._coroutines:
                nursery.start_soon(coroutine)
