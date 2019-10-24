from inspect import Signature, BoundArguments
from typing import Type, Generic, TypeVar, TYPE_CHECKING, Union, overload

from . import _pool

if TYPE_CHECKING:
    from ._controller import Controller
    from ._proxy import PoolDecorator
    from ._pool import Pool

    Owner = Union[Controller, PoolDecorator]
    C_co = TypeVar("C_co", bound=Owner)
else:
    Owner = Union[object]
    C_co = TypeVar("C_co")


class Partial(Generic[C_co]):
    r"""
    Partial application and chaining of Pool :py:class:`~.Controller`\ s
    and :py:class:`~.Decorator`\ s

    This class acts similar to :py:class:`functools.partial`,
    but allows for repeated application (currying) and
    explicit binding via the ``>>`` operator.

    .. code:: python

        # incrementally prepare controller parameters
        control = Partial(Controller, rate=10, interval=10)
        control = control(low_utilisation=0.5, high_allocation=0.9)

        # apply target by chaining
        pipeline = control >> Decorator() >> Pool()

    :note: The keyword argument ``__leaf__`` is reserved for internal usage.

    :note: Binding :py:class:`~.Controller`\ s and :py:class:`~.Decorator`\ s
           creates a temporary :py:class:`~.PartialBind`. Only binding to a
           :py:class:`~.Pool` as the last element creates a concrete binding.
    """
    __slots__ = ("ctor", "args", "kwargs", "leaf")

    def __init__(self, ctor: Type[C_co], *args, __leaf__, **kwargs):
        self.ctor = ctor
        self.args = args
        self.kwargs = kwargs
        self.leaf = __leaf__
        self._check_signature()

    def _check_signature(self):
        args, kwargs = self.args, self.kwargs
        if "target" in kwargs or (args and isinstance(args[0], _pool.Pool)):
            raise TypeError(
                "%s[%s] cannot bind 'target' by calling. "
                "Use `this >> target` instead." % (self.__class__.__name__, self.ctor)
            )
        try:
            if not self.leaf:
                args = None, *args
            _ = Signature.from_callable(self.ctor).bind_partial(
                *args, **kwargs
            )  # type: BoundArguments
        except TypeError as err:
            message = err.args[0]
            raise TypeError(
                "%s[%s] %s" % (self.__class__.__name__, self.ctor, message)
            ) from err

    def __call__(self, *args, **kwargs) -> "Partial[C_co]":
        return Partial(
            self.ctor, *self.args, *args, __leaf__=self.leaf, **self.kwargs, **kwargs
        )

    def __construct__(self, *args, **kwargs):
        return self.ctor(*args, *self.args, **kwargs, **self.kwargs)

    @overload  # noqa: F811
    def __rshift__(self, other: "Union[Owner, Pool, PartialBind[Pool]]") -> "C_co":
        ...

    @overload  # noqa: F811
    def __rshift__(self, other: "Union[Partial, PartialBind]") -> "PartialBind[C_co]":
        ...

    def __rshift__(self, other):  # noqa: F811
        if isinstance(other, PartialBind):
            return PartialBind(self, other.parent, *other.targets)
        elif isinstance(other, Partial):
            if other.leaf:
                return self >> other.__construct__()
            return PartialBind(self, other)
        else:
            return self.__construct__(other)

    def __repr__(self):
        return (
            "{self.__class__.__name__}(ctor={self.ctor.__name__}".format(self=self)
            + ", args={self.args}, kwargs={self.kwargs}".format(self=self)
            + ", leaf={self.leaf})".format(self=self)
        )


class PartialBind(Generic[C_co]):
    r"""
    Helper for recursively binding :py:class:`~.Controller`\ s
    and :py:class:`~.Decorator`\ s

    This helper is used to invert the operator precedence of ``>>``,
    allowing the last pair to be bound first.
    """
    __slots__ = ("parent", "targets")

    def __init__(
        self,
        parent: Partial[C_co],
        *targets: "Union[Partial[Owner], PartialBind[Owner]]",
    ):
        self.parent = parent
        self.targets = targets

    @overload  # noqa: F811
    def __rshift__(self, other: Partial[Owner]) -> "PartialBind[C_co]":
        ...

    @overload  # noqa: F811
    def __rshift__(self, other: "Pool") -> "C_co":
        ...

    def __rshift__(self, other: "Union[Pool, Partial[Owner]]"):  # noqa: F811
        if isinstance(other, _pool.Pool):
            pool = self.targets[-1] >> other
            for owner in reversed(self.targets[:-1]):
                pool = owner >> pool
            return self.parent >> pool
        elif isinstance(other, Partial) and other.leaf:
            return self >> other.__construct__()
        else:
            return PartialBind(self.parent, *self.targets, other)
