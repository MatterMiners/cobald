from inspect import Signature
from typing import Any, Generic, TypeVar, TYPE_CHECKING, overload

from . import _pool

if TYPE_CHECKING:
    from ._controller import Controller
    from ._pool import Pool

    Owner = Controller | Pool
    C_co = TypeVar("C_co", bound=Owner)
else:
    Owner = object
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

    def __init__(self, ctor: "type[C_co]", *args: Any, __leaf__: bool, **kwargs: Any):
        self.ctor = ctor
        self.args = args
        self.kwargs = kwargs
        # whether this constructs a leaf, i.e. a component not taking a target/child
        self.leaf = __leaf__
        self._check_signature()

    def _check_signature(self) -> None:
        """Check that the provided arguments are compatible with the `ctor` signature"""
        args, kwargs = self.args, self.kwargs
        if "target" in kwargs or (args and isinstance(args[0], _pool.Pool)):
            raise TypeError(
                "%s(%s, ...) cannot bind 'target' by calling. "
                "Use `this >> target` instead." % (self.__class__.__name__, self.ctor)
            )
        try:
            if not self.leaf:
                args = None, *args
            Signature.from_callable(self.ctor).bind_partial(*args, **kwargs)
        except TypeError as err:
            message = err.args[0]
            raise TypeError(
                "%s(%s, ...) %s" % (self.__class__.__name__, self.ctor, message)
            ) from err

    def __call__(self, *args: Any, **kwargs: Any) -> "Partial[C_co]":
        return Partial(
            self.ctor, *self.args, *args, __leaf__=self.leaf, **self.kwargs, **kwargs
        )

    def __construct__(self, *args: Any, **kwargs: Any) -> C_co:
        """Construct an instance stored and provided arguments"""
        return self.ctor(*args, *self.args, **kwargs, **self.kwargs)

    # TODO: Partial[Pool] fits this case, but it's not allowed by C_co ATM...
    @overload
    def __rshift__(self, other: "Pool | Owner") -> C_co: ...

    @overload
    def __rshift__(
        self, other: "Partial[Any] | PartialBind[Any]"
    ) -> "PartialBind[C_co]": ...

    def __rshift__(
        self, other: "Pool | Owner | Partial[Any] | PartialBind[Any]"
    ) -> "PartialBind[C_co] | C_co":
        if isinstance(other, PartialBind):
            return PartialBind(self, other.parent, *other.targets)
        elif isinstance(other, Partial):
            # other is as concrete as it gets and we cannot receive any more arguments
            # construct the pipeline now to resulve superfluous helpers
            if other.leaf:
                return self >> other.__construct__()
            return PartialBind(self, other)
        else:
            return self.__construct__(other)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(ctor={self.ctor.__name__}"
            + f", args={self.args}, kwargs={self.kwargs}"
            + f", leaf={self.leaf})"
        )


class PartialBind(Generic[C_co]):
    r"""
    Helper for recursively binding :py:class:`~.Controller`\ s
    and :py:class:`~.Decorator`\ s

    This helper is used to invert the operator precedence of ``>>``,
    allowing the last pair to be bound first.
    Until bound to a specific, concrete target it acts similar to a
    :py:class:`~.Partial` and can be bound to more targets to extend the chain.
    Binding creates a new instance, so any single instance can be
    bound as often as necessary.
    """

    __slots__ = ("parent", "targets")

    def __init__(
        self,
        parent: Partial[C_co],
        *targets: "Partial[Any] | PartialBind[Any]",
    ):
        self.parent = parent
        self.targets = targets

    @overload  # noqa: F811
    def __rshift__(self, other: Partial[Any]) -> "PartialBind[C_co]": ...

    @overload  # noqa: F811
    def __rshift__(self, other: "Pool") -> "C_co": ...

    def __rshift__(
        self, other: "Pool | Partial[Owner]"
    ) -> "PartialBind[C_co] | C_co":  # noqa: F811
        if isinstance(other, _pool.Pool):
            pool = self.targets[-1] >> other
            for owner in reversed(self.targets[:-1]):
                pool = owner >> pool
            return self.parent >> pool
        else:
            if other.leaf:
                return self >> other.__construct__()  # type: ignore
            else:
                return PartialBind(self.parent, *self.targets, other)
