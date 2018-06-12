import threading
import time


from .base_runner import SubroutineRunner


class CapturingThread(threading.Thread):
    """
    Daemonic threads that automatically capture any return value or exception from their ``target``
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs, daemon=True)
        self._return_value = None
        self._exception = None

    def join(self, timeout=None):
        super().join(timeout=timeout)
        if self._started.is_set() and not self.is_alive():
            if self._exception is not None:
                raise self._exception
            return self._return_value

    def run(self):
        """Modified ``run`` that captures return value and exceptions from ``target``"""
        try:
            if self._target:
                self._return_value = self._target(*self._args, **self._kwargs)
        except Exception as err:
            self._exception = err
        finally:
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            del self._target, self._args, self._kwargs


class ThreadRunner(SubroutineRunner):
    flavour = threading

    def __init__(self):
        super().__init__()
        self._threads = []

    def run(self):
        with self._lock:
            self._running.set()
        try:
            while self._running.is_set():
                self._start_outstanding()
                for thread in self._threads:
                    thread.join(timeout=0)
                time.sleep(1)
        except Exception:
            self._running.clear()
            raise

    def _start_outstanding(self):
        with self._lock:
            for subroutine in self._payloads:
                thread = CapturingThread(target=subroutine)
                thread.start()
                self._threads.append(thread)
            self._payloads.clear()
