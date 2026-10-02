from ._pool import Pool
from typing import Any, TypeVar, Type

from ._partial import Partial

C = TypeVar("C", bound="PoolDecorator")


class PoolDecorator(Pool):
    """
    Decorator modifying how a pool provides resources

    :param target: the resource pool for which demand is adjusted
    """

    def __init__(self, target: Pool):
        self.target = target

    @classmethod
    def s(cls: Type[C], *args: Any, **kwargs: Any) -> Partial[C]:
        """
        Create an unbound prototype of this class, partially applying arguments

        .. code:: python

            decorator = Buffer.s(window=20)

            pipeline = controller >> decorator >> pool
        """
        return Partial(cls, *args, __leaf__=False, **kwargs)

    @property
    def supply(self) -> float:
        """The volume of resources that is provided by this site"""
        return self.target.supply

    @property
    def demand(self) -> float:
        """The volume of resources to be provided by this site"""
        return self.target.demand

    @demand.setter
    def demand(self, value: float) -> None:
        self.target.demand = value

    @property
    def utilisation(self) -> float:
        """Fraction of the provided resources which is actively used"""
        return self.target.utilisation

    @property
    def allocation(self) -> float:
        """Fraction of the provided resources which is assigned for usage"""
        return self.target.allocation
