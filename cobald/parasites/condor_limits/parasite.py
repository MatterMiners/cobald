from ...interfaces.pool import Pool

from .adapter import ConcurrencyConstraintView, ConcurrencyUsageView


@Pool.register
class ConcurrencyLimit(object):
    @property
    def supply(self):
        return self._constraints[self.resource]

    @property
    def utilisation(self):
        return self._usage[self.resource] / self._constraints[self.resource]

    consumption = utilisation

    @property
    def demand(self):
        return self._constraints[self.resource]

    @demand.setter
    def demand(self, value):
        self._constraints[self.resource] = value

    def __init__(self, resource: str, opponent: str, pool: str = None):
        self.resource = resource
        self.opponent = opponent
        self.pool = pool
        self._constraints = ConcurrencyConstraintView(pool=pool)
        self._usage = ConcurrencyUsageView(pool=pool)
