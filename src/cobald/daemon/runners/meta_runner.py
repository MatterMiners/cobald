import logging
import threading
import warnings
import asyncio

from types import ModuleType

from .base_runner import BaseRunner
from .trio_runner import TrioRunner
from .asyncio_runner import AsyncioRunner
from .thread_runner import ThreadRunner
from ._compat import asyncio_run


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

    @property
    def runners(self):
        warnings.warn(
            DeprecationWarning(
                "Accessing 'MetaRunner.runners' directly is deprecated. "
                "Use register_payload or run_payload with the correct flavour instead."
            )
        )
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

    async def _launch_runners(self):
        """Launch all runners inside an `asyncio` event loop and wait for them"""
        asyncio_loop = asyncio.get_event_loop()
        # we are already running asyncio – just wrap it as a runner
        runners = {asyncio: AsyncioRunner(asyncio_loop)}
        # launch other runners in asyncio's thread pool
        # this blocks some threads of the pool, but we have only very few runners
        runner_tasks = []
        for runner_type in self.runner_types:
            if runner_type.flavour in runners:
                continue
            runner = runners[runner_type.flavour] = runner_type()
            runner_tasks.append(asyncio_loop.run_in_executor(None, runner.run))
        await asyncio.gather(*runner_tasks)

    def run(self):
        """Run all runners, blocking until completion or error"""
        self._logger.info("starting all runners")
        self._lock.acquire()
        try:
            asyncio_run(self._launch_runners())
        except KeyboardInterrupt:
            self._logger.info("runner interrupted")
        except Exception as err:
            self._logger.exception("runner terminated: %s", err)
            raise RuntimeError from err
        finally:
            self._stop_runners()
            self._logger.info("stopped all runners")
            self._lock.release()

    def stop(self):
        """Stop all runners"""
        self._stop_runners()

    def _stop_runners(self):
        for runner in self._runners.values():
            if runner.flavour == threading:
                continue
            runner.stop()
        self._runners[threading].stop()
