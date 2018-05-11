import abc

from .pool import Pool
from .controller import Controller


@Controller.register
@Pool.register
class ProxyPool(abc.ABC):
    """
    A pool that controls another pool to provide resources
    """
    @property
    def supply(self):
        """The volume of resources that is provided by this site"""
        return self.target.supply

    @property
    def demand(self):
        """The volume of resources to be provided by this site"""
        return self.target.demand

    @demand.setter
    def demand(self, value):
        self.target.demand = value

    @property
    def utilisation(self) -> float:
        """Fraction of the provided resources which is actively used"""
        return self.target.utilisation

    @property
    def consumption(self) -> float:
        """Fraction of the provided resources which is assigned for usage"""
        return self.target.consumption

    def __init__(self, target: Pool):
        self.target = target
