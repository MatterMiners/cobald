from typing import Type, Generic, TypeVar, Tuple, Dict, TYPE_CHECKING

from ._pool import Pool

if TYPE_CHECKING:
    from ._controller import Controller
    from ._proxy import PoolDecorator
    C_co = TypeVar('C_co', Controller, PoolDecorator, covariant=True)
else:
    C_co = TypeVar('C_co')


class Partial(Generic[C_co]):
    """
    Partial application and chaining of Pool :py:class:`~.Controllers` and :py:class:`~.Decorators`

    This class acts similar to :py:class:`functools.partial`,
    but allows for repeated application (currying) and
    explicit binding via the ``>>`` operator.

    .. code:: python

        # incrementally prepare controller parameters
        control = Partial(Controller, rate=10, interval=10)
        control = control(low_utilisation=0.5, high_allocation=0.9)

        # apply target by chaining
        pipeline = control >> Decorator() >> Pool()
    """
    __slots__ = ('ctor', 'args', 'kwargs')

    def __init__(self, ctor: Type[C_co], *args, **kwargs):
        self._assert_unbound(args, kwargs)
        self.ctor = ctor
        self.args = args
        self.kwargs = kwargs

    @staticmethod
    def _assert_unbound(args: Tuple, kwargs: Dict):
        if (args and isinstance(args[0], Pool)) or kwargs.get('target') is not None:
            raise ValueError(
                'Cannot bind target by calling `this(target, ...)`. '
                'Use `this.bind(target)` or `this >> target` instead.'
            )

    def __call__(self, *args, **kwargs) -> 'Partial[C_co]':
        self._assert_unbound(args, kwargs)
        return Partial(self.ctor, *self.args, *args, **self.kwargs, **kwargs)

    def __rshift__(self, other: Pool) -> C_co:
        return self.ctor(other, *self.args, **self.kwargs)
