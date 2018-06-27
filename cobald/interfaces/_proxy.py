from ._pool import Pool


class PoolDecorator(Pool):
    """
    Decorator modifying how a pool provides resources
    """
    def __init__(self, target: Pool):
        self.target = target

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
    def allocation(self) -> float:
        """Fraction of the provided resources which is assigned for usage"""
        return self.target.allocation
