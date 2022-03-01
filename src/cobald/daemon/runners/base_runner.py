import asyncio
import logging
import threading
from typing import Any

from cobald.daemon.debug import NameRepr


class BaseRunner(object):
    """Concurrency backend on top of `asyncio`"""

    flavour = None  # type: Any

    def __init__(self, asyncio_loop: asyncio.AbstractEventLoop):
        self.asyncio_loop = asyncio_loop
        self._logger = logging.getLogger(
            "cobald.runtime.runner.%s" % NameRepr(self.flavour)
        )
        self._stopped = threading.Event()
        self._stopped.set()

    def register_payload(self, payload):
        """
        Register ``payload`` for background execution in a threadsafe manner

        This runs ``payload`` as an orphaned background task as soon as possible.
        It is an error for ``payload`` to return or raise anything without handling it.
        """
        raise NotImplementedError

    def run_payload(self, payload):
        """
        Register ``payload`` for direct execution in a threadsafe manner

        This runs ``payload`` as soon as possible, blocking until completion.
        Should ``payload`` return or raise anything, it is propagated to the caller.
        """
        raise NotImplementedError

    async def ready(self):
        """Wait until the runner is ready to accept payloads"""
        assert (
            not self._stopped.is_set()
        ), "runner must be .run before waiting until it is ready"

    async def run(self):
        """
        Execute all current and future payloads in an `asyncio` task

        Blocks and executes payloads until :py:meth:`stop` is called.
        It is an error for any orphaned payload to return or raise.

        Implementations should override :py:meth:`~.manage_payloads`
        to customize their specific parts.
        """
        self._logger.info("runner started: %s", self)
        self._stopped.clear()
        try:
            await self.manage_payloads()
        except Exception:
            self._logger.exception("runner aborted: %s", self)
            raise
        else:
            self._logger.info("runner stopped: %s", self)
        finally:
            self._stopped.set()

    async def manage_payloads(self):
        raise NotImplementedError

    async def aclose(self):
        """Shut down this runner"""

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
