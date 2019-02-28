from inspect import Signature, BoundArguments
from typing import Type, Generic, TypeVar, Tuple, Dict, TYPE_CHECKING, Union

from ._pool import Pool

if TYPE_CHECKING:
    from ._controller import Controller
    from ._proxy import PoolDecorator
    C_co = TypeVar('C_co', bound=Union[Controller, PoolDecorator])
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
        self._check_signature(args, kwargs)
        self.ctor = ctor
        self.args = args
        self.kwargs = kwargs

    def _check_signature(self, args: Tuple, kwargs: Dict):
        try:
            bound_args = Signature.from_callable(self.ctor).bind_partial(*args, **kwargs)  # type: BoundArguments
        except TypeError as err:
            message = err.args[0]
            raise TypeError('%s[%s] %s' % (self.__class__.__name__, self.ctor, message)) from err
        else:
            if bound_args.arguments.get('target', None) is not None:
                raise TypeError(
                    "%s[%s] cannot bind 'target' by calling. Use `this >> target` instead." % (
                        self.__class__.__name__, self.ctor
                    )
                )

    def __call__(self, *args, **kwargs) -> 'Partial[C_co]':
        return Partial(self.ctor, *self.args, *args, **self.kwargs, **kwargs)

    def __rshift__(self, other: Pool) -> C_co:
        return self.ctor(other, *self.args, **self.kwargs)
