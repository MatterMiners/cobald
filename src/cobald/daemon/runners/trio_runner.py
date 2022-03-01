from typing import Optional, Callable, Awaitable
import asyncio
from functools import partial
import trio

from .base_runner import BaseRunner
from .async_tools import raise_return


class TrioRunner(BaseRunner):
    """
    Runner for coroutines with :py:mod:`trio`

    All active payloads are actively cancelled when the runner is closed.
    """

    flavour = trio

    def __init__(self, asyncio_loop: asyncio.AbstractEventLoop):
        super().__init__(asyncio_loop)
        self._trio_token: Optional[trio.lowlevel.TrioToken] = None
        self._submit_tasks: Optional[trio.MemorySendChannel] = None

    def register_payload(self, payload: Callable[[], Awaitable]):
        assert self._trio_token is not None and self._submit_tasks is not None
        trio.from_thread.run(
            self._submit_tasks.send, payload, trio_token=self._trio_token
        )

    def run_payload(self, payload: Callable[[], Awaitable]):
        assert self._trio_token is not None and self._submit_tasks is not None
        trio.from_thread.run(
            payload, trio_token=self._trio_token
        )

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
        async with trio.open_nursery() as nursery:
            async for task in receive_tasks:
                nursery.start_soon(raise_return, task)
            # shutting down: cancel the scope to cancel all payloads
            nursery.cancel_scope.cancel()

    async def _aclose_trio(self):
        self._running.clear()
        await self._submit_tasks.aclose()

    async def aclose(self):
        await self.asyncio_loop.run_in_executor(
            None, partial(
                trio.from_thread.run, self._aclose_trio, trio_token=self._trio_token
            )
        )
