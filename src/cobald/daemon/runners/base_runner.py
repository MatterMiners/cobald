from typing import Any
from abc import abstractmethod, ABCMeta
import asyncio
import logging
import threading

from ..debug import NameRepr


class BaseRunner(metaclass=ABCMeta):
    """Concurrency backend on top of `asyncio`"""

    flavour = None  # type: Any

    def __init__(self, asyncio_loop: asyncio.AbstractEventLoop):
        self.asyncio_loop = asyncio_loop
        self._logger = logging.getLogger(
            "cobald.runtime.runner.%s" % NameRepr(self.flavour)
        )
        self._stopped = threading.Event()
        self._stopped.set()

    @abstractmethod
    def register_payload(self, payload):
        """
        Register ``payload`` for background execution in a threadsafe manner

        This runs ``payload`` as an orphaned background task as soon as possible.
        It is an error for ``payload`` to return or raise anything without handling it.
        """
        raise NotImplementedError

    @abstractmethod
    def run_payload(self, payload):
        """
        Execute ``payload`` and return its result in a threadsafe manner

        This runs ``payload`` as soon as possible, blocking until completion.
        Should ``payload`` return or raise anything, it is propagated to the caller.
        """
        raise NotImplementedError

    async def ready(self):
        """Wait until the runner is ready to accept payloads"""
        assert (
            not self._stopped.is_set()
        ), "runner must be .run before waiting until it is ready"
        # Most runners are ready when instantiated, simply queueing payloads
        # until they get a chance to run them. Only override this method when
        # the runner has to do some `async` setup before being ready.

    async def run(self):
        """
        Execute all current and future payloads in an `asyncio` coroutine

        This method will continuously execute payloads sent to the runner.
        It only returns when :py:meth:`stop` is called
        or if any orphaned payload returns or raises.
        In the latter case, :py:exc:`~.OrphanedReturn` or the raised exception
        is re-raised by this method.

        Implementations should override :py:meth:`~.manage_payloads`
        to customize their specific parts.
        """
        self._logger.info("runner started: %s", self)
        self._stopped.clear()
        try:
            await self.manage_payloads()
        except asyncio.CancelledError:
            self._logger.info("runner cancelled: %s", self)
            raise
        except BaseException:
            self._logger.exception("runner aborted: %s", self)
            raise
        else:
            self._logger.info("runner stopped: %s", self)
        finally:
            self._stopped.set()

    @abstractmethod
    async def manage_payloads(self):
        """
        Implementation of managing payloads when :py:meth:`~.run`

        This method must continuously execute payloads sent to the runner.
        It may only return when :py:meth:`stop` is called
        or if any orphaned payload return or raise.
        In the latter case, :py:exc:`~.OrphanedReturn` or the raised exception
        must re-raised by this method.
        """
        raise NotImplementedError

    @abstractmethod
    async def aclose(self):
        """Shut down this runner"""
        raise NotImplementedError

    def stop(self):
        """Stop execution of all current and future payloads and block until success"""
        if self._stopped.is_set():
            return
        # the loop exists independently of all runners, we can use it to shut down
        closed = asyncio.run_coroutine_threadsafe(self.aclose(), self.asyncio_loop)
        closed.result()


class OrphanedReturn(Exception):
    """A runnable returned a value without anyone to receive it"""

    def __init__(self, who, value):
        super().__init__("no caller to receive %s from %s" % (value, who))
        self.who = who
        self.value = value
