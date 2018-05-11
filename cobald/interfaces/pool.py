import abc


class Pool(metaclass=abc.ABCMeta):
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
