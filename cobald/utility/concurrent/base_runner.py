import logging
import threading

from ...utility.debug import NameRepr


class BaseRunner(object):
    flavour = None

    def __init__(self):
        self._logger = logging.getLogger('cobald.runtime.runner.%s' % NameRepr(self.flavour))
        self._payloads = []
        self._lock = threading.Lock()
        self.running = threading.Event()

    def register_payload(self, payload):
        self._payloads.append(payload)

    def run_payload(self, payload):
        raise NotImplementedError

    def run(self):
        self._logger.info('runner started: %s', self)
        try:
            with self._lock:
                assert not self.running.set(), 'cannot re-run: %s' % self
                self.running.set()
            self._run()
        except Exception:
            self._logger.error('runner aborted: %s', self)
            raise
        else:
            self._logger.info('runner stopped: %s', self)
        finally:
            self.running.clear()

    def _run(self):
        raise NotImplementedError

    def stop(self):
        self.running.clear()


class OrphanedReturn(Exception):
    """A runnable returned a value without anyone to receive it"""
    def __init__(self, who, value):
        super().__init__('no caller to receive %s from %s' % (value, who))
        self.who = who
        self.value = value
