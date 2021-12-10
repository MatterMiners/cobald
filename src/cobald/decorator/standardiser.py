from cobald.interfaces import Pool, PoolDecorator

from ..utility import enforce
from ..utility.primitives import infinity as inf


def _clamp(low, value, high):
    """Clamp `value` to the range between `low` and `high`"""
    if value < low:
        return low
    elif value > high:
        return high
    else:
        return value


def _floor(n, base=1):
    """Floor `n` to a multiple of `base`"""
    return n // base * base


class Standardiser(PoolDecorator):
    """
    Limits for changes to the demand of a pool

    :param target: the pool on which changes are standardised
    :param minimum: minimum ``target.demand`` allowed
    :param maximum: maximum ``target.demand`` allowed
    :param granularity: granularity of ``target.demand``
    :param surplus: how much ``target.demand`` may be above ``target.supply``
    :param backlog: how much ``target.demand`` may be below ``target.supply``

    The ``supply`` and ``backlog`` clamp the ``demand`` such that
    ``supply - backlog <= demand <= supply + surplus`` holds.

    The default values apply no limits at all so that isolated limits may be used.
    When several limits are set, ``granularity`` has the weakest priority,
    both ``surplus`` and ``backlog`` may limit the result of ``granularity``,
    and ``minimum`` and ``maximum`` overrule all other limits.
    """

    @property
    def demand(self) -> float:
        if abs(self._demand - self.target.demand) >= self.granularity:
            self._demand = self.target.demand
        return self._demand

    @demand.setter
    def demand(self, value: float):
        # Record the clamped demand so that the controller sees the limits
        # but does not get into numerical problems from limited granularity
        self._demand = self._clamp_demand(value)
        if self.granularity != 1:
            self.target.demand = self._clamp_demand(_floor(value, self.granularity))
        else:
            self.target.demand = self._demand

    def _clamp_demand(self, value):
        """Clamp `value` between the min/max demand limits"""
        supply = self.target.supply
        by_supply = _clamp(supply - self.backlog, value, supply + self.surplus)
        by_limits = _clamp(self.minimum, by_supply, self.maximum)
        return type(value)(by_limits)

    def __init__(
        self,
        target: Pool,
        minimum: float = -inf,
        maximum: float = inf,
        granularity: int = 1,
        backlog: float = inf,
        surplus: float = inf,
    ):
        super().__init__(target)
        enforce(minimum <= maximum, ValueError("minimum must be smaller than maximum"))
        enforce(surplus > 0, ValueError("allowed surplus must be positive"))
        enforce(backlog > 0, ValueError("allowed backlog must be positive"))
        enforce(granularity > 0, ValueError("granularity must be positive"))
        # demand may be incrementally changed - store it internally to give
        # the impression of a smooth transition
        self._demand = target.demand
        self.minimum = minimum
        self.maximum = maximum
        self.granularity = granularity
        self.surplus = surplus
        self.backlog = backlog
