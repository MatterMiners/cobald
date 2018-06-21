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
        with self._lock:
            assert not self._running.set(), 'cannot re-run: %s' % self
            self._running.set()
        self._logger.info('runner started: %s', self)
        try:
            self._run()
        except Exception:
            self._logger.error('runner aborted: %s', self)
            self._running.clear()
            raise
        else:
            self._logger.info('runner stopped: %s', self)
            self._running.clear()

    def _run(self):
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
