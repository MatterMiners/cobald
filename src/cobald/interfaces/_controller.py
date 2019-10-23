import abc
from typing import TypeVar, Type

from ._pool import Pool
from ._partial import Partial


C = TypeVar("C", bound="Controller")


class Controller(metaclass=abc.ABCMeta):
    """
    Controller adjusting the demand in a :py:class:`~.Pool`

    :param target: the resource pool for which demand is adjusted
    """

    def __init__(self, target: Pool):
        self.target = target

    @classmethod
    def s(cls: Type[C], *args, **kwargs) -> Partial[C]:
        """
        Create an unbound prototype of this class, partially applying arguments

        .. code:: python

            controller = Controller.s(interval=20)

            pipeline = controller(rate=10) >> pool
        """
        return Partial(cls, *args, __leaf__=False, **kwargs)
