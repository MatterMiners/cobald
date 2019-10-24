import threading
import time

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

    def __init__(self):
        super().__init__()
        self._threads = set()

    def run_payload(self, payload):
        # - run_payload has to block until payload is done
        # instead of running payload in a thread and blocking this one,
        # we just block this thread by running payload directly
        return payload()

    def _run(self):
        delay = 0.0
        while self.running.is_set():
            self._start_payloads()
            self._reap_payloads()
            time.sleep(delay)
            delay = min(delay + 0.1, 1.0)

    def _start_payloads(self):
        """Start all queued payloads"""
        with self._lock:
            payloads = self._payloads.copy()
            self._payloads.clear()
        for subroutine in payloads:
            thread = CapturingThread(target=subroutine)
            thread.start()
            self._threads.add(thread)
            self._logger.debug("booted thread %s", thread)
        time.sleep(0)

    def _reap_payloads(self):
        """Clean up all finished payloads"""
        for thread in self._threads.copy():
            # CapturingThread.join will throw
            if thread.join(timeout=0):
                self._threads.remove(thread)
                self._logger.debug("reaped thread %s", thread)
