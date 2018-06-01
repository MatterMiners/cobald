from cobald.interfaces.pool import Pool
from cobald.interfaces.proxy import PoolDecorator

from ..utility import infinity


class Limiter(PoolDecorator):
    """
    A passive buffer limiting changes to a pool

    :param target: the pool to which changes are applied
    :param minimum: minimum demand to provide
    :param maximum: maximum demand to provide
    :param backlog: limit for absolute difference between supply and demand
    """
    @property
    def demand(self):
        return self.target.demand

    @demand.setter
    def demand(self, value):
        self.target.demand = type(value)(min(self.maximum, max(self.minimum, value)))

    def __init__(self, target: Pool, minimum: float = 1.0, maximum: float = infinity):
        super().__init__(target=target)
        self.minimum = minimum
        self.maximum = maximum
