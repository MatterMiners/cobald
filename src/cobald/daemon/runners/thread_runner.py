import threading
import asyncio

from .base_runner import BaseRunner, OrphanedReturn


class ThreadRunner(BaseRunner):
    """
    Runner for subroutines with :py:mod:`threading`

    Active payloads are *not* cancelled when the runner is closed.
    Only program termination forcefully cancels leftover payloads.
    """

    flavour = threading

    # This runner directly uses threading.Thread to run payloads.
    # To detect errors, each payload is wrapped; errors and unexpected return values
    # are pushed to a queue from which the main task re-raises.
    def __init__(self, asyncio_loop: asyncio.AbstractEventLoop):
        super().__init__(asyncio_loop)
        self._payload_failure = asyncio_loop.create_future()

    def register_payload(self, payload):
        thread = threading.Thread(
            target=self._monitor_payload, args=(payload,), daemon=True
        )
        thread.start()

    def run_payload(self, payload):
        # The method has to block until payload is done.
        # Instead of running payload in a thread and blocking this one,
        # this thread is blocked by running the payload directly.
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
        self.asyncio_loop.call_soon_threadsafe(self._set_failure, failure)

    def _set_failure(self, failure: BaseException):
        if not self._payload_failure.done():
            self._payload_failure.set_exception(failure)

    async def manage_payloads(self):
        await self._payload_failure

    async def aclose(self):
        if self._stopped.is_set():
            return
        if not self._payload_failure.done():
            self._payload_failure.set_result(None)
