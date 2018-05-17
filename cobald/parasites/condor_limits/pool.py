from typing import Union

from ...interfaces.pool import Pool

from .adapter import ConcurrencyConstraintView, ConcurrencyUsageView, PoolResources, PoolResourceView


class ConcurrencyLimit(Pool):
    """
    Volume of ConcurrencyLimit in a pool

    :param resource: the name of the concurrency limit
    :param pool: the name of the HTCondor pool in which the limit is used
    """
    @property
    def supply(self):
        return self._constraints[self.resource]

    @property
    def utilisation(self):
        return self._usage[self.resource] / self._constraints[self.resource]

    allocation = utilisation

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
    """
    Volume of ConcurrencyLimit in a pool, managed by adjusting an opposing limit

    :param resource: the name of the concurrency limit
    :param opponent: the name of the concurrency limit opposing ``resource``
    :param total: the maximum sum of ``resource`` and ``opponent``
    :param pool: the name of the HTCondor pool in which the limit is used

    The parameter ``total`` can be either a fixed or query-able value.
    A fixed value is any :py:class:`float` or :py:class:`int` value.
    A query-able value is a string indicating which value to query from the pool;
    any of ``"cpus"``, ``"memory"``, ``"disk"`` or ``"machines"`` is understood.
    """
    @property
    def supply(self):
        return self.total - self._constraints[self.opponent]

    @property
    def utilisation(self):
        return self._usage[self.resource] / self.supply

    allocation = utilisation

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
            self.total = PoolResourceView(total, pool_resources)
        else:
            self.total = total
        self._constraints = ConcurrencyConstraintView(pool=pool)
        self._usage = ConcurrencyUsageView(pool=pool)


__all__ = [ConcurrencyLimit.__name__]
