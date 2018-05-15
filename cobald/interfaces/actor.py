import abc
import asyncio


class Actor(metaclass=abc.ABCMeta):
    """
    An active component that can be run by an event loop
    """
    def mount(self, event_loop: asyncio.AbstractEventLoop):
        """Mount the Actor in ``event_loop`` for execution"""
        event_loop.create_task(self.run())

    @asyncio.coroutine
    def run(self):
        return
