import logging
import weakref
import trio
import gc
import functools

from types import ModuleType

from ..utility.concurrent.meta_runner import MetaRunner


class ServiceUnit(object):
    __active_units__ = weakref.WeakSet()

    def __init__(self, service, flavour):
        assert hasattr(service, 'run'), "service must implement a 'run' method"
        self.service = weakref.ref(service)
        self.flavour = flavour
        self._cancel = False
        self._started = False
        ServiceUnit.__active_units__.add(self)

    @classmethod
    def units(cls):
        """Sequence of all currently defined units"""
        return list(cls.__active_units__)

    @property
    def running(self):
        return self._started

    def cancel(self):
        if self._started:
            raise RuntimeError('attempt to cancel %r after starting it' % self)
        self._cancel = True

    def start(self, runner: MetaRunner):
        service = self.service()
        if service is None or self._cancel or self._started:
            return
        else:
            self._started = True
            runner.register_payload(service.run, flavour=self.flavour)

    def __repr__(self):
        return '%s(%r, flavour=%r)' % (self.__class__.__name__, self.service() or '<defunct>', self.flavour)


def __new_service__(cls, *args, flavour, **kwargs):
    self = super(cls, cls).__new__(cls)
    service_unit = ServiceUnit(self, flavour)
    self.__service_unit__ = service_unit
    return self


def service(flavour):
    """
    Mark a class as implementing a Service

    Each Service class must have a ``run`` method.
    This method is :py:meth:`~ServiceRunner.adopt`\ ed after the daemon starts, unless

    * the Service has been garbage collected, or
    * the ServiceUnit has been :py:meth:`~ServiceUnit.cancel`\ ed.

    For each service instance, its :py:class:`ServiceUnit` is available at ``service_instance.__service_unit__``.
    """
    def service_unit_decorator(cls):
        cls.__new__ = functools.partialmethod(__new_service__, flavour=flavour)
        try:
            run = cls.run
        except AttributeError:
            pass
        else:
            if run.__doc__ is None:
                run.__doc__ = "Service entry point"
        return cls
    return service_unit_decorator


@service(flavour=trio)
class ServiceRunner(object):
    """
    Runner for coroutines, subroutines and services
    """
    def __init__(self, accept_delay : float = 1):
        self._logger = logging.getLogger('cobald.runtime.daemon.services')
        self._meta_runner = MetaRunner()
        self.accept_delay = accept_delay

    def execute(self, payload, flavour: ModuleType):
        """Synchronously run ``payload`` and provide its output"""
        self._meta_runner.run_payload(payload, flavour=flavour)

    def adopt(self, payload, flavour: ModuleType):
        """Concurrently run ``payload`` in the background"""
        self._meta_runner.register_payload(payload, flavour=flavour)

    def accept(self):
        """Start accepting synchronous, asynchronous and service payloads"""
        assert not self._meta_runner, 'payloads scheduled for %s before being started' % self
        self._logger.info('ServiceRunner starting')
        # force collecting objects so that defunct, migrated and overwritten services are destroyed now
        gc.collect()
        self._adopt_services()
        self._meta_runner.run()

    async def run(self):
        while True:
            await trio.sleep(self.accept_delay)
            self._accept_services()

    def _adopt_services(self):
        for unit in ServiceUnit.units():  # type: ServiceUnit
            if unit.running:
                continue
            unit.start(self._meta_runner)
