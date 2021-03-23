import logging
import weakref
import trio
import gc
import functools
import threading

from types import ModuleType

from .meta_runner import MetaRunner
from .guard import exclusive
from ..debug import NameRepr


class ServiceUnit(object):
    """
    Definition for running a service

    :param service: the service to run
    :param flavour: runner flavour to use for running the service
    """

    __active_units__ = weakref.WeakSet()  # type: weakref.WeakSet[ServiceUnit]

    def __init__(self, service, flavour):
        assert hasattr(service, "run"), "service must implement a 'run' method"
        assert any(
            flavour == runner.flavour for runner in MetaRunner.runner_types
        ), "service flavour must be one of %s" % ",".join(
            repr(runner.flavour) for runner in MetaRunner.runner_types
        )
        self.service = weakref.ref(service)
        self.flavour = flavour
        self._started = False
        ServiceUnit.__active_units__.add(self)

    @classmethod
    def units(cls):
        """Sequence of all currently defined units"""
        return list(cls.__active_units__)

    @property
    def running(self):
        return self._started

    def start(self, runner: MetaRunner):
        service = self.service()
        if service is None:
            return
        else:
            self._started = True
            runner.register_payload(service.run, flavour=self.flavour)

    def __repr__(self):
        return "%s(%r, flavour=%r)" % (
            self.__class__.__name__,
            self.service() or "<defunct>",
            self.flavour,
        )


def service(flavour):
    r"""
    Mark a class as implementing a Service

    Each Service class must have a ``run`` method, which does not take any arguments.
    This method is :py:meth:`~.ServiceRunner.adopt`\ ed after the daemon starts, unless

    * the Service has been garbage collected, or
    * the ServiceUnit has been :py:meth:`~.ServiceUnit.cancel`\ ed.

    For each service instance, its :py:class:`~.ServiceUnit` is available at
    ``service_instance.__service_unit__``.
    """

    def service_unit_decorator(raw_cls):
        __new__ = raw_cls.__new__

        def __new_service__(cls, *args, **kwargs):
            if __new__ is object.__new__:
                self = __new__(cls)
            else:
                self = __new__(cls, *args, **kwargs)
            service_unit = ServiceUnit(self, flavour)
            self.__service_unit__ = service_unit
            return self

        raw_cls.__new__ = __new_service__
        if raw_cls.run.__doc__ is None:
            raw_cls.run.__doc__ = "Service entry point"
        return raw_cls

    return service_unit_decorator


class ServiceRunner(object):
    """
    Runner for coroutines, subroutines and services
    """

    def __init__(self, accept_delay: float = 1):
        self._logger = logging.getLogger("cobald.runtime.daemon.services")
        self._meta_runner = MetaRunner()
        self._must_shutdown = False
        self._is_shutdown = threading.Event()
        self.running = threading.Event()
        self.accept_delay = accept_delay

    def execute(self, payload, *args, flavour: ModuleType, **kwargs):
        """
        Synchronously run ``payload`` and provide its output

        If ``*args*`` and/or ``**kwargs`` are provided, pass them to ``payload``
        upon execution.
        """
        if args or kwargs:
            payload = functools.partial(payload, *args, **kwargs)
        return self._meta_runner.run_payload(payload, flavour=flavour)

    def adopt(self, payload, *args, flavour: ModuleType, **kwargs):
        """
        Concurrently run ``payload`` in the background

        If ``*args*`` and/or ``**kwargs`` are provided, pass them to ``payload``
        upon execution.
        """
        if args or kwargs:
            payload = functools.partial(payload, *args, **kwargs)
        self._meta_runner.register_payload(payload, flavour=flavour)

    @exclusive()
    def accept(self):
        """
        Start accepting synchronous, asynchronous and service payloads

        Since services are globally defined, only one :py:class:`ServiceRunner`
        may :py:meth:`accept` payloads at any time.
        """
        if self._meta_runner:
            raise RuntimeError("payloads scheduled for %s before being started" % self)
        self._must_shutdown = False
        self._logger.info("%s starting", self.__class__.__name__)
        # force collecting objects so that defunct,
        # migrated and overwritten services are destroyed now
        gc.collect()
        self._adopt_services()
        self.adopt(self._accept_services, flavour=trio)
        self._meta_runner.run()

    def shutdown(self):
        """Shutdown the accept loop and stop running payloads"""
        self._must_shutdown = True
        self._is_shutdown.wait()
        self._meta_runner.stop()

    async def _accept_services(self):
        delay, max_delay, increase = 0.0, self.accept_delay, self.accept_delay / 10
        self._is_shutdown.clear()
        self.running.set()
        try:
            self._logger.info("%s started", self.__class__.__name__)
            while not self._must_shutdown:
                self._adopt_services()
                await trio.sleep(delay)
                delay = min(delay + increase, max_delay)
        except Exception:
            self._logger.exception("%s aborted", self.__class__.__name__)
            raise
        else:
            self._logger.info("%s stopped", self.__class__.__name__)
        finally:
            self.running.clear()
            self._is_shutdown.set()

    def _adopt_services(self):
        for unit in ServiceUnit.units():  # type: ServiceUnit
            if unit.running:
                continue
            self._logger.info("%s adopts %s", self.__class__.__name__, NameRepr(unit))
            unit.start(self._meta_runner)
