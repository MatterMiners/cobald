import asyncio

from .base_runner import CoroutineRunner


class AsyncioRunner(CoroutineRunner):
    flavour = asyncio

    def run(self):
        event_loop = asyncio.get_event_loop()
        asyncio.wait(*self._payloads, loop=event_loop, return_when=asyncio.FIRST_EXCEPTION)
