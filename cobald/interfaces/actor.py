import abc
import asyncio


class Actor(metaclass=abc.ABCMeta):
    """
    An active component capable of concurrently performing work
    """
    def mount(self, event_loop: asyncio.AbstractEventLoop):
        event_loop.create_task(self.run())

    @asyncio.coroutine
    def run(self):
        return
