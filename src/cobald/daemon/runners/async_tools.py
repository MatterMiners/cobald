from typing import Callable, Awaitable, Coroutine
import threading

from .base_runner import OrphanedReturn


async def raise_return(payload: Callable[[], Awaitable]) -> None:
    """Wrapper to raise exception on unhandled return values"""
    value = await payload()
    if value is not None:
        raise OrphanedReturn(payload, value)


def ensure_coroutine(awaitable: Awaitable) -> Coroutine:
    """Ensure that ``awaitable`` is a coroutine and wrap it otherwise"""
    if isinstance(awaitable, Coroutine):
        return awaitable

    async def wrapper():
        return await awaitable

    return wrapper()


class AsyncExecution(object):
    def __init__(self, payload):
        self.payload = payload
        self._result = None
        self._done = threading.Event()
        self._done.clear()

    # explicit coroutine for libraries that type check
    async def coroutine(self):
        await self

    def __await__(self):
        try:
            value = yield from self.payload().__await__()
        except Exception as err:
            self._result = None, err
        else:
            self._result = value, None
        self._done.set()

    def wait(self):
        self._done.wait()
        value, exception = self._result
        if exception is None:
            return value
        else:
            raise exception

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.payload)
