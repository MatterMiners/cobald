import abc
from typing import TypeVar, Type, TYPE_CHECKING

from ._partial import Partial

if TYPE_CHECKING:
    from ._controller import Controller


C = TypeVar("C", bound="Controller")


class Pool(metaclass=abc.ABCMeta):
    """
    Individual provider for a number of indistinguishable resources
    """

    @property
    @abc.abstractmethod
    def supply(self) -> float:
        """The volume of resources that is provided by this pool"""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def demand(self) -> float:
        """The volume of resources to be provided by this pool"""
        raise NotImplementedError

    @demand.setter
    @abc.abstractmethod
    def demand(self, value: float):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def utilisation(self) -> float:
        """Fraction of the provided resources which are actively used"""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def allocation(self) -> float:
        """Fraction of the provided resources which are assigned for usage"""
        raise NotImplementedError

    @classmethod
    def s(cls: Type[C], *args, **kwargs) -> Partial[C]:
        """
        Create an unbound prototype of this class, partially applying arguments

        .. code:: python

            pool = RemotePool.s(port=1337)

            pipeline = controller >> pool(host='localhost')
        """
        return Partial(cls, *args, __leaf__=True, **kwargs)
