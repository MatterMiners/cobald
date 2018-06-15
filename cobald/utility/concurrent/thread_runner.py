import threading
import time


from ..debug import NameRepr
from .base_runner import SubroutineRunner


class OrphanedReturn(Exception):
    def __init__(self, who, value):
        super().__init__('no caller to receive %s from %s' % (value, who))
        self.who = who
        self.value = value


class CapturingThread(threading.Thread):
    """
    Daemonic threads that automatically capture any return value or exception from their ``target``
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
        except Exception as err:
            self._exception = err
        finally:
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            del self._target, self._args, self._kwargs


class ThreadRunner(SubroutineRunner):
    """Runner for subroutines with :py:mod:`threading`"""
    flavour = threading

    def __init__(self):
        super().__init__()
        self._threads = set()

    def run(self):
        with self._lock:
            self._running.set()
        try:
            while self._running.is_set():
                self._start_outstanding()
                for thread in self._threads.copy():
                    if thread.join(timeout=0):
                        self._threads.remove(thread)
                time.sleep(1)
        except KeyboardInterrupt:
            self._running.clear()
        except Exception:
            self._running.clear()
            raise

    def _start_outstanding(self):
        with self._lock:
            for subroutine in self._payloads:
                thread = CapturingThread(target=subroutine)
                thread.start()
                self._threads.add(thread)
            self._payloads.clear()
