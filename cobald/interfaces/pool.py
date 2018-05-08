import abc


class Pool(abc.ABC):
    """
    Individual provider for a number of indistinguishable resources
    """
    @property
    @abc.abstractmethod
    def supply(self):
        """The volume of resources that is provided by this site"""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def demand(self):
        """The volume of resources to be provided by this site"""
        raise NotImplementedError

    @demand.setter
    @abc.abstractmethod
    def demand(self, value):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def utilisation(self) -> float:
        """Fraction of the provided resources which is actively used"""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def consumption(self) -> float:
        """Fraction of the provided resources which is assigned for usage"""
        raise NotImplementedError


@Pool.register
class ProxyPool(abc.ABC):
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
