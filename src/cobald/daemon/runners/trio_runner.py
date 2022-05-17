from typing import Optional, Callable, Awaitable, Coroutine
import asyncio
from functools import partial

import trio

from .base_runner import BaseRunner, OrphanedReturn


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
        except (trio.RunFinishedError, trio.Cancelled):
            self._logger.warning(f"discarding payload {payload} during shutdown")
            return
        except RuntimeError:
            # trio raises a bare RuntimeError when we are already in the trio thread
            # just submit the task directly
            self._submit_tasks.send_nowait(payload)

    def run_payload(self, payload: Callable[[], Coroutine]):
        assert self._trio_token is not None and self._submit_tasks is not None
        return trio.from_thread.run(payload, trio_token=self._trio_token)

    async def ready(self):
        await self._ready.wait()

    async def manage_payloads(self):
        try:
            await self.asyncio_loop.run_in_executor(None, self._run_trio_blocking)
        except asyncio.CancelledError:
            await self.aclose()
            raise

    def _run_trio_blocking(self):
        return trio.run(self._manage_payloads_trio)

    async def _manage_payloads_trio(self):
        self._trio_token = trio.lowlevel.current_trio_token()
        # We receive tasks from a possibly blocking call in the same event loop
        # To avoid deadlocking the event loop, the task buffer must always have
        # sufficient capacity to accept new tasks.
        self._submit_tasks, receive_tasks = trio.open_memory_channel(
            max_buffer_size=float("inf")
        )
        self.asyncio_loop.call_soon_threadsafe(self._ready.set)
        async with trio.open_nursery() as nursery:
            async for task in receive_tasks:
                nursery.start_soon(self._monitor_payload, task)
            # shutting down: cancel the scope to cancel all payloads
            nursery.cancel_scope.cancel()

    async def _monitor_payload(self, payload: Callable[[], Awaitable]):
        """Wrapper for awaitables and to raise exception on unhandled return values"""
        value = await payload()
        if value is not None:
            raise OrphanedReturn(payload, value)

    async def _aclose_trio(self):
        # suppress trio cancellation to avoid raising an error in aclose
        try:
            await self._submit_tasks.aclose()
        except trio.Cancelled:
            pass

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
        except (trio.RunFinishedError, trio.Cancelled):
            # trio already finished in its own thread
            return
