import abc


class ResourceAdapter(abc.ABC):
    @property
    @abc.abstractmethod
    def utilisation(self):
        """Fraction of the owned resources which is in use"""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def exhaustion(self):
        """Fraction of the owned resources which is inaccessible"""
        raise NotImplementedError

    @abc.abstractmethod
    def increase_resources(self):
        """Increase the volume of owned resources"""
        pass

    @abc.abstractmethod
    def decrease_resources(self):
        """Decrease the volume of owned resources"""
        pass
