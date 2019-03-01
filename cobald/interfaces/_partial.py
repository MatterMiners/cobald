from inspect import Signature, BoundArguments
from typing import Type, Generic, TypeVar, Tuple, Dict, TYPE_CHECKING, Union, overload

from ._pool import Pool

if TYPE_CHECKING:
    from ._controller import Controller
    from ._proxy import PoolDecorator
    Owner = Union[Controller, PoolDecorator]
    C_co = TypeVar('C_co', bound=Owner)
else:
    Owner = Union[object]
    C_co = TypeVar('C_co')


class Partial(Generic[C_co]):
    r"""
    Partial application and chaining of Pool :py:class:`~.Controller`\ s and :py:class:`~.Decorator` \s

    This class acts similar to :py:class:`functools.partial`,
    but allows for repeated application (currying) and
    explicit binding via the ``>>`` operator.

    .. code:: python

        # incrementally prepare controller parameters
        control = Partial(Controller, rate=10, interval=10)
        control = control(low_utilisation=0.5, high_allocation=0.9)

        # apply target by chaining
        pipeline = control >> Decorator() >> Pool()

    :note: Binding :py:class:`~.Controller`\ s and :py:class:`~.Decorator` \s creates a temporary
           :py:class:`~.PartialBind`. Only binding to a :py:class:`~.Pool` as the last element
           creates a concrete binding.
    """
    __slots__ = ('ctor', 'args', 'kwargs')

    def __init__(self, ctor: Type[C_co], *args, **kwargs):
        self.ctor = ctor
        self.args = args
        self.kwargs = kwargs
        self._check_signature(args, kwargs)

    def _check_signature(self, args: Tuple, kwargs: Dict):
        if 'target' in kwargs or (args and isinstance(args[0], Pool)):
            raise TypeError(
                "%s[%s] cannot bind 'target' by calling. Use `this >> target` instead." % (
                    self.__class__.__name__, self.ctor
                )
            )
        try:
            bound_args = Signature.from_callable(self.ctor).bind_partial(None, *args, **kwargs)  # type: BoundArguments
        except TypeError as err:
            message = err.args[0]
            raise TypeError('%s[%s] %s' % (self.__class__.__name__, self.ctor, message)) from err

    def __call__(self, *args, **kwargs) -> 'Partial[C_co]':
        return Partial(self.ctor, *self.args, *args, **self.kwargs, **kwargs)

    @overload
    def __rshift__(self, other: 'Union[Partial, PartialBind]') -> 'PartialBind[C_co]':
        ...

    @overload
    def __rshift__(self, other: 'Union[Owner, Pool]') -> 'C_co':
        ...

    def __rshift__(self, other):
        if isinstance(other, (Partial, PartialBind)):
            return PartialBind(self, other)
        else:
            return self.ctor(other, *self.args, **self.kwargs)


class PartialBind(Generic[C_co]):
    r"""
    Helper for recursively binding :py:class:`~.Controller`\ s and :py:class:`~.Decorator` \s

    This helper is used to invert the operator precedence of ``>>``,
    allowing the last pair to be bound first.
    """
    __slots__ = ('parent', 'targets')

    def __init__(self, parent: Partial[C_co], *targets: Partial[Owner]):
        self.parent = parent
        self.targets = targets

    @overload
    def __rshift__(self, other: Partial[Owner]) -> 'PartialBind[C_co]':
        ...

    @overload
    def __rshift__(self, other: Pool) -> 'C_co':
        ...

    def __rshift__(self, other: Union[Pool, Partial[Owner]]):
        if isinstance(other, Pool):
            pool = self.targets[-1] >> other
            for owner in reversed(self.targets[:-1]):
                pool = owner >> pool
            return self.parent >> pool
        else:
            return PartialBind(self.parent, *self.targets, other)
