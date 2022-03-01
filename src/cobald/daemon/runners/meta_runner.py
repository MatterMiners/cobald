import logging
import threading
import warnings

from types import ModuleType

from .base_runner import BaseRunner
from .trio_runner import TrioRunner
from .asyncio_runner import AsyncioRunner
from .thread_runner import ThreadRunner
from .asyncio_watcher import asyncio_main_run


from cobald.daemon.debug import NameRepr


class MetaRunner(object):
    """
    Unified interface to schedule subroutines and coroutines for concurrent execution
    """

    runner_types = (TrioRunner, AsyncioRunner, ThreadRunner)

    def __init__(self):
        self._logger = logging.getLogger("cobald.runtime.runner.meta")
        self._runners = {
            runner.flavour: runner() for runner in self.runner_types
        }  # type: dict[ModuleType, BaseRunner]
        self._lock = threading.Lock()
        self.running = threading.Event()
        self.running.clear()

    @property
    def runners(self):
        warnings.warn(DeprecationWarning(
            "Accessing 'MetaRunner.runners' directly is deprecated. "
            "Use register_payload or run_payload with the correct flavour instead."
        ))
        return self._runners

    def __bool__(self):
        return any(bool(runner) for runner in self._runners.values())

    def register_payload(self, *payloads, flavour: ModuleType):
        """Queue one or more payload for execution after its runner is started"""
        for payload in payloads:
            self._logger.debug(
                "registering payload %s (%s)", NameRepr(payload), NameRepr(flavour)
            )
            self._runners[flavour].register_payload(payload)

    def run_payload(self, payload, *, flavour: ModuleType):
        """Execute one payload after its runner is started and return its output"""
        return self._runners[flavour].run_payload(payload)

    def run(self):
        """Run all runners, blocking until completion or error"""
        self._logger.info("starting all runners")
        try:
            with self._lock:
                assert not self.running.set(), "cannot re-run: %s" % self
                self.running.set()
            thread_runner = self._runners[threading]
            for runner in self._runners.values():
                if runner is not thread_runner:
                    thread_runner.register_payload(runner.run)
            if threading.current_thread() == threading.main_thread():
                asyncio_main_run(root_runner=thread_runner)
            else:
                thread_runner.run()
        except KeyboardInterrupt:
            self._logger.info("runner interrupted")
        except Exception as err:
            self._logger.exception("runner terminated: %s", err)
            raise RuntimeError from err
        finally:
            self._stop_runners()
            self._logger.info("stopped all runners")
            self.running.clear()

    def stop(self):
        """Stop all runners"""
        self._stop_runners()

    def _stop_runners(self):
        for runner in self._runners.values():
            if runner.flavour == threading:
                continue
            runner.stop()
        self._runners[threading].stop()
