import abc
import asyncio
import warnings


class Actor(metaclass=abc.ABCMeta):
    """
    An active component that can be run by an event loop
    """
    def __new__(cls, *args, **kwargs):
        warnings.warn(FutureWarning(
            'Actor will be removed in the future. '
            '%s Instances should autonomously register themselves with `deamon.runner`.' % cls.__name__
        ))
        return super().__new__(cls)

    def mount(self, event_loop: asyncio.AbstractEventLoop):
        """Mount the Actor in ``event_loop`` for execution"""
        event_loop.create_task(self.run())

    @asyncio.coroutine
    def run(self):
        return
