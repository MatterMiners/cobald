from cobald.interfaces import Pool, PoolDecorator


def _clamp(low: float, value: float, high: float):
    """Clamp `value` to the range between `low` and `high`"""
    if value < low:
        return low
    elif value > high:
        return high
    else:
        return value


def _floor(n: float, base: float = 1):
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
        if self._target_demand != self.target.demand:
            return self.target.demand
        return self._parent_demand

    @demand.setter
    def demand(self, value: float) -> None:
        # Record the clamped demand so that the controller sees the limits
        # but does not get into numerical problems from limited granularity
        self._parent_demand = self._clamp_demand(value)
        if self.granularity is not None:
            self._target_demand = self._clamp_demand(_floor(value, self.granularity))
        else:
            self._target_demand = self._parent_demand
        self.target.demand = self._target_demand

    def _clamp_demand(self, value: float) -> float:
        """Clamp demand `value` between the min/max demand limits"""
        supply = self.target.supply
        by_supply = _clamp(supply - self.backlog, value, supply + self.surplus)
        by_limits = _clamp(self.minimum, by_supply, self.maximum)
        return type(value)(by_limits)

    def __init__(
        self,
        target: Pool,
        minimum: float = -float("inf"),
        maximum: float = float("inf"),
        granularity: float | None = 1,
        backlog: float = float("inf"),
        surplus: float = float("inf"),
    ) -> None:
        super().__init__(target)
        assert minimum <= maximum, "minimum must be smaller than maximum"
        assert surplus > 0, "allowed surplus must be positive"
        assert backlog > 0, "allowed backlog must be positive"
        assert (
            granularity is None or granularity > 0
        ), "granularity must be positive or None"
        # demand may incrementally change by parent and independently by child
        # track both ends to reflect full granularity and changes
        self._parent_demand = target.demand
        self._target_demand = target.demand
        self.minimum = minimum
        self.maximum = maximum
        self.granularity = granularity
        self.surplus = surplus
        self.backlog = backlog
