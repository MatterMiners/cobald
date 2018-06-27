from cobald.interfaces import Pool, PoolDecorator


class Coarser(PoolDecorator):
    """
    Proxy limiting changes in a pool to a certain granularity

    :param target: the pool to which changes are applied
    :param granularity: granularity of changes
    """
    @property
    def demand(self):
        return self._demand

    @demand.setter
    def demand(self, value):
        self._demand = value
        self.target.demand = value // self.granularity * self.granularity

    def __init__(self, target: Pool, granularity: int = 1):
        super().__init__(target=target)
        self._demand = 0
        self.granularity = granularity
