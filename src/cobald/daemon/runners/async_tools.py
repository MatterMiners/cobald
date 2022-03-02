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
