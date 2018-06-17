import logging
import threading

from ...utility.debug import NameRepr


class BaseRunner(object):
    flavour = None

    def __init__(self):
        self._logger = logging.getLogger('cobald.runtime.runner.%s' % NameRepr(self.flavour))
        self._payloads = []
        self._lock = threading.Lock()
        self._running = threading.Event()

    def run(self):
        raise NotImplementedError

    def stop(self):
        self._running.clear()


class CoroutineRunner(BaseRunner):
    """
    Base Runner to concurrently execute coroutines
    """
    def register_coroutine(self, coroutine):
        self._payloads.append(coroutine)


class SubroutineRunner(BaseRunner):
    """
    Base Runner to concurrently execute subroutines
    """
    def register_subroutine(self, subroutine):
        self._payloads.append(subroutine)
