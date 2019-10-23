from ..interfaces import Pool, CompositePool


class UniformComposite(CompositePool):
    """
    Uniform composition of several pools, with each pool weighted the same
    """

    children = []

    @property
    def demand(self):
        return self._demand

    @demand.setter
    def demand(self, value):
        self._demand = value
        child_count = len(self.children)
        for pool in self.children:
            pool.demand = value / child_count

    @property
    def supply(self):
        return sum(child.supply for child in self.children)

    @property
    def utilisation(self):
        try:
            return sum(child.utilisation for child in self.children) / len(
                self.children
            )
        except ZeroDivisionError:
            return 1.0

    @property
    def allocation(self):
        try:
            return sum(child.allocation for child in self.children) / len(self.children)
        except ZeroDivisionError:
            return 1.0

    def __init__(self, *children: Pool):
        self._demand = sum(child.demand for child in children)
        self.children = list(children)
