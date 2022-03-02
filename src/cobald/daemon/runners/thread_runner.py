from typing import Optional
import threading
import asyncio

from .base_runner import BaseRunner, OrphanedReturn


class ThreadRunner(BaseRunner):
    """
    Runner for subroutines with :py:mod:`threading`

    All active payloads are *not* cancelled when the runner is closed.
    Only program termination forcefully cancels leftover payloads.
    """

    flavour = threading

    def __init__(self, asyncio_loop: asyncio.AbstractEventLoop):
        super().__init__(asyncio_loop)
        self._failure_queue = asyncio.Queue()

    def register_payload(self, payload):
        thread = threading.Thread(
            target=self._monitor_payload, args=(payload,), daemon=True
        )
        thread.start()

    def run_payload(self, payload):
        # - run_payload has to block until payload is done
        # instead of running payload in a thread and blocking this one,
        # we just block this thread by running payload directly
        return payload()

    def _monitor_payload(self, payload):
        try:
            result = payload()
        except BaseException as e:
            failure = e
        else:
            if result is None:
                return
            failure = OrphanedReturn(payload, result)
        assert self._failure_queue is not None
        self.asyncio_loop.call_soon_threadsafe(self._failure_queue.put_nowait, failure)

    async def manage_payloads(self):
        failure = await self._failure_queue.get()
        if failure is not None:
            raise failure

    async def aclose(self):
        if self._stopped.is_set():
            return
        await self._failure_queue.put(None)
