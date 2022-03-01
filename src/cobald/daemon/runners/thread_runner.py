from typing import Optional
import threading
import asyncio

from ..debug import NameRepr
from .base_runner import BaseRunner, OrphanedReturn


class CapturingThread(threading.Thread):
    """
    Daemonic threads that capture any return value or exception from their ``target``
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs, daemon=True)
        self._exception = None
        self._name = str(NameRepr(self._target))

    def join(self, timeout=None):
        super().join(timeout=timeout)
        if self._started.is_set() and not self.is_alive():
            if self._exception is not None:
                raise self._exception
        return not self.is_alive()

    def run(self):
        """Modified ``run`` that captures return value and exceptions from ``target``"""
        try:
            if self._target:
                return_value = self._target(*self._args, **self._kwargs)
                if return_value is not None:
                    self._exception = OrphanedReturn(self, return_value)
        except BaseException as err:
            self._exception = err
        finally:
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            del self._target, self._args, self._kwargs


class ThreadRunner(BaseRunner):
    """Runner for subroutines with :py:mod:`threading`"""

    flavour = threading

    def __init__(self, asyncio_loop: asyncio.AbstractEventLoop):
        super().__init__(asyncio_loop)
        self._failure_queue: Optional[asyncio.Queue] = None

    def register_payload(self, payload):
        thread = threading.Thread(target=self.run_payload, args=(payload,), daemon=True)
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
        self._failure_queue = asyncio.Queue()
        failure = await self._failure_queue.get()
        if failure is not None:
            raise failure

    async def aclose(self):
        self._running.clear()
        await self._failure_queue.put(None)
