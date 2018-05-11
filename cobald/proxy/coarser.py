from cobald.interfaces.pool import Pool
from cobald.interfaces.proxy import ProxyPool


class Coarser(ProxyPool):
    """
    Proxy limiting changes in a pool to a certain granularity

    :param target: the pool to which changes are applied
    :param granularity: granularity of changes
    """
    @ProxyPool.demand.setter
    def demand(self, value):
        self.target.demand = value // self.granularity * self.granularity

    def __init__(self, target: Pool, granularity: int = 1):
        super().__init__(target=target)
        self.granularity = granularity
