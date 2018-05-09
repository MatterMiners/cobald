import abc
import asyncio


class Actor(abc.ABC):
    """
    An active component capable of concurrently performing work
    """
    def mount(self, event_loop: asyncio.AbstractEventLoop):
        event_loop.create_task(self.run())

    async def run(self):
        return
