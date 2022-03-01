import logging
import threading
from typing import Any

from cobald.daemon.debug import NameRepr


class BaseRunner(object):
    flavour = None  # type: Any

    def __init__(self):
        self._logger = logging.getLogger(
            "cobald.runtime.runner.%s" % NameRepr(self.flavour)
        )
        self._running = threading.Event()
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
        self._running.set()
        try:
            await self.manage_payloads()
        except Exception:
            self._logger.exception("runner aborted: %s", self)
            raise
        else:
            self._logger.info("runner stopped: %s", self)
        finally:
            self._running.clear()
            self._stopped.set()

    async def manage_payloads(self):
        raise NotImplementedError

    async def aclose(self):
        """Shut down this runner"""

    def stop(self):
        """
        Stop execution of all current and future payloads and wait for success
        """
        self._stopped.wait()


class OrphanedReturn(Exception):
    """A runnable returned a value without anyone to receive it"""

    def __init__(self, who, value):
        super().__init__("no caller to receive %s from %s" % (value, who))
        self.who = who
        self.value = value
