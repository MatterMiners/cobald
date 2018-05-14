from typing import Union

from ...interfaces.pool import Pool

from .adapter import ConcurrencyConstraintView, ConcurrencyUsageView, PoolResources


class ConcurrencyLimit(Pool):
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

    def __init__(self, resource: str, pool: str = None):
        self.resource = resource
        self.pool = pool
        self._constraints = ConcurrencyConstraintView(pool=pool)
        self._usage = ConcurrencyUsageView(pool=pool)


class ConcurrencyAntiLimit(Pool):
    @property
    def supply(self):
        return self.total - self._constraints[self.opponent]

    @property
    def utilisation(self):
        return self._usage[self.resource] / self.supply

    consumption = utilisation

    @property
    def demand(self):
        return self.total - self._constraints[self.opponent]

    @demand.setter
    def demand(self, value):
        self._constraints[self.opponent] = self.total - value

    def __init__(self, resource: str, opponent: str, total: Union[str, float], pool: str = None):
        self.resource = resource
        self.opponent = opponent
        self.pool = pool
        if isinstance(total, str):
            pool_resources = PoolResources(pool=pool)
            self.total = pool_resources[total]
        else:
            self.total = total
        self._constraints = ConcurrencyConstraintView(pool=pool)
        self._usage = ConcurrencyUsageView(pool=pool)


__all__ = [ConcurrencyLimit.__name__]
