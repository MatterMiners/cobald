from typing import Any, Coroutine, Callable, NamedTuple, TypeVar, Protocol, NoReturn
import asyncio
import logging
import warnings
import weakref
import functools
import threading
import trio
import contextlib

from types import ModuleType

from .meta_runner import MetaRunner
from ..debug import NameRepr

T = TypeVar("T")


def _weakdict_values(wd: "weakref.WeakKeyDictionary[Any, T]") -> set[T]:
    """Thread-safely copy all values from a weakset to a set"""
    # The WeakXYZ methods are not thread-safe because they miss locking until py3.14.
    # See https://github.com/python/cpython/issues/123089 and related.
    # Directly copy the underlying data-dict as this is GIL-atomic.
    items: "set[tuple[weakref.ReferenceType[Any], T]]" = set(wd.data.copy().items())
    return {value for kref, value in items if kref() is not None}


class Service(Protocol):
    """
    Protocol for classes that provide a service to run in the background
    """

    def run(self) -> None | Coroutine[Any, Any, None]: ...


S = TypeVar("S", bound=Service)


class ServiceUnit:
    """
    Definition for running a service

    :param service: the service to run
    :param flavour: runner flavour to use for running the service
    """

    __defined_units__: "weakref.WeakKeyDictionary[Service, ServiceUnit]" = (
        weakref.WeakKeyDictionary()
    )

    def __init__(self, service: Service, flavour: ModuleType):
        assert hasattr(service, "run"), "service must implement a 'run' method"
        self.service = weakref.ref(service)
        self.flavour = flavour
        #: whether the unit was ever started
        self.started = False

    @classmethod
    def units(cls) -> "set[ServiceUnit]":
        """Container of all currently defined units"""
        return _weakdict_values(cls.__defined_units__)

    @property
    def running(self) -> bool:
        """Whether this specific service is running"""
        warnings.warn(
            DeprecationWarning(
                "'ServiceUnit.running' is deprecated and misleading, use '.started'"
            ),
            stacklevel=2,
        )
        return self.started

    def __repr__(self):
        service = self.service() or "<defunct>"
        return f"{self.__class__.__name__}({service}, flavour={self.flavour!r})"


def service(flavour: ModuleType) -> Callable[[type[S]], type[S]]:
    r"""
    Mark a class as implementing a Service

    Each Service class must have a ``run`` method taking no arguments.
    The :py:class:`~.ServiceRunner` automatically executes this when active.
    """

    def service_unit_decorator(raw_cls: type[S]) -> type[S]:
        __new__ = raw_cls.__new__

        def __new_service__(cls: type[S], *args: Any, **kwargs: Any) -> S:
            if __new__ is object.__new__:
                self = __new__(cls)
            else:
                self = __new__(cls, *args, **kwargs)
            # make the unit visible to the service runner(s)
            ServiceUnit.__defined_units__[self] = unit = ServiceUnit(self, flavour)
            ServiceRunner.notify(unit)
            return self

        raw_cls.__new__ = __new_service__
        if raw_cls.run.__doc__ is None:
            raw_cls.run.__doc__ = "Service entry point"
        return raw_cls

    return service_unit_decorator


class RunningState(NamedTuple):
    """State of an active :py:class:`~.ServiceRunner`"""

    #: the loop in which the runner is active
    loop: asyncio.AbstractEventLoop
    #: service tasks spawned by the runner
    tasks: asyncio.TaskGroup
    #: queue for new services or exceptions to handle
    interrupts: asyncio.Queue[tuple[ServiceUnit, None] | tuple[None, BaseException]]

    @classmethod
    @contextlib.asynccontextmanager
    async def new(cls):
        loop = asyncio.get_running_loop()
        self = cls(loop, asyncio.TaskGroup(), asyncio.Queue())
        async with self.tasks:
            yield self

    def put_threadsafe(
        self, message: tuple[ServiceUnit, None] | tuple[None, BaseException]
    ) -> None:
        self.loop.call_soon_threadsafe(self.interrupts.put_nowait, message)


class ServiceRunner:
    """
    Runner for services

    The service runner runs services and tracks their concurrent tasks
    to provide safe background concurrency.
    If any task fails with an exception or provides unexpected output values,
    this is registered as an error and all tasks are gracefully shut down.
    """

    _exclusive_run = threading.Lock()
    _running_instance: "ServiceRunner | None" = None

    def __init__(self, accept_delay: float = 1):
        if accept_delay != 1:
            warnings.warn(
                DeprecationWarning("'accept_delay' is deprecated and no longer used"),
                stacklevel=2,
            )
        self._logger = logging.getLogger("cobald.runtime.daemon.services")
        self._state: RunningState | None = None
        self._meta_runner: MetaRunner | None = None

    # MetaRunner legacy support
    # Only spawn the runner if needed, which is hopefully never
    def _get_runner(self) -> MetaRunner:
        if self._meta_runner is None:
            self._meta_runner = MetaRunner()
            thread = threading.Thread(
                target=self._monitor_run, args=(self._meta_runner.run,), daemon=True
            )
            thread.start()
            self._meta_runner.running.wait()
        return self._meta_runner

    def execute(
        self, payload: Callable[..., T], *args: Any, flavour: ModuleType, **kwargs: Any
    ) -> T:
        """
        Synchronously run ``payload`` and provide its output

        If ``*args*`` and/or ``**kwargs`` are provided, pass them to ``payload``
        upon execution.
        """
        warnings.warn(
            DeprecationWarning(
                f"'runtime.execute' is deprecated, directly use {flavour.__name__!r}"
            ),
            stacklevel=2,
        )
        if args or kwargs:
            payload = functools.partial(payload, *args, **kwargs)
        return self._get_runner().run_payload(payload, flavour=flavour)

    def adopt(
        self, payload: Callable[..., T], *args: Any, flavour: ModuleType, **kwargs: Any
    ) -> None:
        """
        Concurrently run ``payload`` in the background

        If ``*args*`` and/or ``**kwargs`` are provided, pass them to ``payload``
        upon execution.
        """
        warnings.warn(
            DeprecationWarning(
                f"'runtime.execute' is deprecated, directly use {flavour.__name__!r}"
            ),
            stacklevel=2,
        )
        if args or kwargs:
            payload = functools.partial(payload, *args, **kwargs)
        self._get_runner().register_payload(payload, flavour=flavour)

    # asyncio based service facilities
    @classmethod
    def notify(cls, of: ServiceUnit) -> None:
        """Notify the running instance (if any) of a new service"""
        try:
            put = cls._running_instance._state.put_threadsafe
        except AttributeError:
            return
        else:
            put((of, None))

    async def run_services(self) -> NoReturn:
        """
        Continuously run services

        Since services are globally defined, only one :py:class:`ServiceRunner`
        may :py:meth:`~.run_services` at any time.
        """
        if self._exclusive_run.acquire(blocking=False):
            ServiceRunner._running_instance = self
            try:
                return await self._run_services()
            finally:
                ServiceRunner._running_instance = None
                self._state = None
                if self._meta_runner is not None:
                    self._meta_runner.stop()
                    self._meta_runner = None
                self._exclusive_run.release()
        else:
            raise RuntimeError("only one 'run_services' allowed at once")

    async def _run_services(self) -> NoReturn:
        self._logger.info("%s starting", self.__class__.__name__)
        async with RunningState.new() as state:
            assert self._state is None
            self._state = state
            # spawn existing units
            for unit in ServiceUnit.units():
                self._spawn_service(unit)
            # wait for new units or errors
            while True:
                unit, exc = await state.interrupts.get()
                if exc is not None:
                    raise exc
                elif unit is not None:
                    self._spawn_service(unit)

    def _spawn_service(self, unit: ServiceUnit) -> None:
        assert self._state is not None, "cannot spawn outside of run context"
        asyncio_tg = self._state.tasks
        if unit.started or (service := unit.service()) is None:
            return
        unit.started = True
        self._logger.info("%s adopts %s", self.__class__.__name__, NameRepr(unit))
        if unit.flavour is asyncio:
            # the task group keeps tasks alive, we can forget about them
            asyncio_tg.create_task(service.run(), name=str(service))
        elif unit.flavour is threading:
            thread = threading.Thread(
                target=self._monitor_run, args=(service.run,), daemon=True
            )
            thread.run()
        elif unit.flavour is trio:
            warnings.warn(
                DeprecationWarning(
                    f"'trio' services are deprecated, please use 'asyncio' for {unit}"
                ),
                stacklevel=2,
            )
            self._get_runner().register_payload(service.run, flavour=trio)
        else:
            raise NotImplementedError(f"service flavour {unit.flavour} for {service}")

    def _monitor_run(self, payload: Callable[[], None]) -> None:
        """Run `payload` synchronously and report any failures"""
        try:
            result = payload()
        except BaseException as e:  # noqa: B036
            failure = e
        else:
            if result is None:
                return
            failure = RuntimeError(f"payload {payload} returned unexpected {result}")
        if (state := self._state) is not None:
            state.put_threadsafe((None, failure))
