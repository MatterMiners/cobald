from ..interfaces import Pool, CompositePool


class WeightedComposite(CompositePool):
    """
    Weighted composition of several pools, with each pool weighted by its
    supply, utilisation or allocation.
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
            try:
                pool.demand = value * getattr(pool, self._weight) / self._total_weight
            except ZeroDivisionError:
                pool.demand = value / child_count

    @property
    def supply(self):
        return sum(child.supply for child in self.children)

    @property
    def utilisation(self):
        try:
            return (
                sum(
                    child.utilisation * getattr(child, self._weight)
                    for child in self.children
                )
                / self._total_weight
            )
        except ZeroDivisionError:
            return 1.0

    @property
    def allocation(self):
        try:
            return (
                sum(
                    child.allocation * getattr(child, self._weight)
                    for child in self.children
                )
                / self._total_weight
            )
        except ZeroDivisionError:
            return 1.0

    @property
    def _total_weight(self):
        return sum(getattr(child, self._weight) for child in self.children)

    def __init__(self, *children: Pool, weight="supply"):
        assert weight in (
            "supply",
            "utilisation",
            "allocation",
        ), "weight must be either supply, utilisation or allocation"
        self._weight = weight
        self._demand = sum(child.demand for child in children)
        self.children = list(children)
