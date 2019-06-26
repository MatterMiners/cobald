from ..interfaces import Pool, CompositePool


class WeightedComposite(CompositePool):
    """
    Weighted composition of several pools, with each pool weighted by its supply
    """
    children = []

    @property
    def demand(self):
        return self._demand

    @demand.setter
    def demand(self, value):
        self._demand = value
        total_supply = self.supply
        child_count = len(self.children)
        for pool in self.children:
            try:
                pool.demand = value * pool.supply / total_supply
            except ZeroDivisionError:
                pool.demand = value / child_count

    @property
    def supply(self):
        return sum(child.supply for child in self.children)

    @property
    def utilisation(self):
        try:
            return sum(
                child.utilisation * child.supply for child in self.children
            ) / self.supply
        except ZeroDivisionError:
            return 1.

    @property
    def allocation(self):
        try:
            return sum(
                child.allocation * child.supply for child in self.children
            ) / self.supply
        except ZeroDivisionError:
            return 1.

    def __init__(self, *children: Pool):
        self._demand = sum(child.demand for child in children)
        self.children = list(children)
