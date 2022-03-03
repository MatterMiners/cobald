from typing import Optional, Callable, Awaitable
import asyncio
from functools import partial

import trio

from .base_runner import BaseRunner, OrphanedReturn


async def raise_return(payload: Callable[[], Awaitable]) -> None:
    """Wrapper to raise exception on unhandled return values"""
    value = await payload()
    if value is not None:
        raise OrphanedReturn(payload, value)


class TrioRunner(BaseRunner):
    """
    Runner for coroutines with :py:mod:`trio`

    All active payloads are actively cancelled when the runner is closed.
    """

    flavour = trio

    # This runner uses a trio loop in a separate thread to run payloads.
    # Tracking payloads and errors is handled by a trio nursery. A queue ("channel")
    # is used to move payloads into the trio loop.
    # Since the trio loop runs in its own thread, all public methods have to move
    # payloads/tasks into that thread.
    def __init__(self, asyncio_loop: asyncio.AbstractEventLoop):
        super().__init__(asyncio_loop)
        self._ready = asyncio.Event()
        self._trio_token: Optional[trio.lowlevel.TrioToken] = None
        self._submit_tasks: Optional[trio.MemorySendChannel] = None

    def register_payload(self, payload: Callable[[], Awaitable]):
        assert self._trio_token is not None and self._submit_tasks is not None
        try:
            trio.from_thread.run(
                self._submit_tasks.send, payload, trio_token=self._trio_token
            )
        except trio.RunFinishedError:
            self._logger.warning(f"discarding payload {payload} during shutdown")
            return

    def run_payload(self, payload: Callable[[], Awaitable]):
        assert self._trio_token is not None and self._submit_tasks is not None
        return trio.from_thread.run(payload, trio_token=self._trio_token)

    async def ready(self):
        await self._ready.wait()

    async def manage_payloads(self):
        # this blocks one thread of the asyncio event loop
        await self.asyncio_loop.run_in_executor(None, self._run_trio_blocking)

    def _run_trio_blocking(self):
        return trio.run(self._manage_payloads_trio)

    async def _manage_payloads_trio(self):
        self._trio_token = trio.lowlevel.current_trio_token()
        # buffer of 256 is somewhat arbitrary but should be large enough to rarely stall
        # and small enough to smooth out explosive backlog.
        self._submit_tasks, receive_tasks = trio.open_memory_channel(256)
        self.asyncio_loop.call_soon_threadsafe(self._ready.set)
        async with trio.open_nursery() as nursery:
            async for task in receive_tasks:
                nursery.start_soon(raise_return, task)
            # shutting down: cancel the scope to cancel all payloads
            nursery.cancel_scope.cancel()

    async def _aclose_trio(self):
        await self._submit_tasks.aclose()

    async def aclose(self):
        if self._stopped.is_set():
            return
        # Trio only allows us an *synchronously blocking* call it from other threads.
        # Use an executor thread to make that *asynchronously* blocking for asyncio.
        try:
            await self.asyncio_loop.run_in_executor(
                None,
                partial(
                    trio.from_thread.run, self._aclose_trio, trio_token=self._trio_token
                ),
            )
        except trio.RunFinishedError:
            # trio already finished in its own thread
            return
