from typing import Dict, List, Any
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

from ..debug import NameRepr


class MetaRunner(object):
    """
    Unified interface to schedule subroutines and coroutines for concurrent execution
    """

    runner_types = (TrioRunner, AsyncioRunner, ThreadRunner)

    def __init__(self):
        self._logger = logging.getLogger("cobald.runtime.runner.meta")
        self._runners: Dict[ModuleType, BaseRunner] = {}
        # queue to store payloads submitted before the runner is started
        self._runner_queues: Dict[ModuleType, Any] = {}
        self.running = threading.Event()

    @property
    def runners(self):
        warnings.warn(
            DeprecationWarning(
                "Accessing 'MetaRunner.runners' directly is deprecated. "
                "Use register_payload or run_payload with the correct flavour instead."
            )
        )
        return self._runners

    def register_payload(self, *payloads, flavour: ModuleType):
        """Queue one or more payloads for execution after its runner is started"""
        try:
            runner = self._runners[flavour]
        except KeyError:
            if self.running.is_set():
                raise RuntimeError(f"unknown runner {NameRepr(flavour)}") from None
            self._runner_queues.setdefault(flavour, []).extend(payloads)
        else:
            for payload in payloads:
                self._logger.debug(
                    "registering payload %s (%s)", NameRepr(payload), NameRepr(flavour)
                )
                runner.register_payload(payload)

    def run_payload(self, payload, *, flavour: ModuleType):
        """
        Execute one payload and return its output

        This method will block until the payload is completed.
        It is an error to call it during initialisation before the runners are started.
        """
        return self._runners[flavour].run_payload(payload)

    def run(self):
        """Run all runners, blocking until completion or error"""
        self._logger.info("starting all runners")
        try:
            asyncio_run(self._manage_runners())
        except KeyboardInterrupt:
            self._logger.info("runner interrupted")
        except Exception as err:
            self._logger.exception("runner terminated: %s", err)
            raise RuntimeError("background task failed") from err
        finally:
            self._logger.info("stopped all runners")

    def stop(self):
        """Stop all runners"""
        self._logger.debug("stop all runners")
        for runner in self._runners.values():
            runner.stop()

    async def _manage_runners(self):
        """Manage all runners inside the current `asyncio` event loop"""
        runner_tasks = await self._launch_runners()
        self.running.set()
        try:
            # wait for all runners to either stop gracefully or propagate errors
            # we only unqueue payloads *while* watching runners as payloads could
            # cause the runners to fail – we need to stop unqueueing them as well.
            await asyncio.gather(*runner_tasks, self._unqueue_payloads())
        except KeyboardInterrupt:
            # KeyboardInterrupt in a runner task immediately kills the event loop.
            # When we get resurrected, the exception has already been handled!
            # Just clean up...
            await asyncio.shield(self._aclose_runners(runner_tasks))
        except BaseException:
            await asyncio.shield(self._aclose_runners(runner_tasks))
            raise
        finally:
            self.running.clear()

    async def _launch_runners(self) -> List[asyncio.Task]:
        """Launch all runners inside the current `asyncio` event loop"""
        asyncio_loop = asyncio.get_event_loop()
        self._runners = {}
        runner_tasks = []
        for runner_type in self.runner_types:
            runner = self._runners[runner_type.flavour] = runner_type(asyncio_loop)
            runner_tasks.append(asyncio_loop.create_task(runner.run()))
        for runner in self._runners.values():
            await runner.ready()
        return runner_tasks

    async def _unqueue_payloads(self) -> None:
        """Register payloads once runners are started"""
        # Unqueue when we are running so that payloads do not get requeued.
        # This also provides checking that the queued flavours correspond to a runner.
        assert self.running.is_set(), "runners must be launched before unqueueing"
        # runners are started, so re-registering payloads does not queue them again
        for flavour, queue in self._runner_queues.items():
            self.register_payload(*queue, flavour=flavour)
            queue.clear()
        self._runner_queues.clear()

    async def _aclose_runners(self, runner_tasks):
        for runner in self._runners.values():
            await runner.aclose()
        # wait until runners are closed
        await asyncio.gather(*runner_tasks, return_exceptions=True)
        self._runners.clear()
