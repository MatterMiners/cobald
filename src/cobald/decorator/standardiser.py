from cobald.interfaces import Pool, PoolDecorator

from ..utility import enforce
from ..utility.primitives import infinity as inf


class Standardiser(PoolDecorator):
    """
    Limits for changes to the demand of a pool

    :param target: the pool on which changes are standardised
    :param minimum: minimum ``target.demand`` allowed
    :param maximum: maximum ``target.demand`` allowed
    :param granularity: granularity of ``target.demand``
    :param surplus: maximum by which ``target.supply`` may exceed ``target.demand``
    :param backlog: maximum by which ``target.demand`` may exceed ``target.supply``

    The default values apply no limits at all so that isolated limits may be used.
    When several limits are set, ``granularity`` has the weakest priority,
    both ``surplus`` and ``backlog`` may limit the result of ``granularity``,
    and ``minimum`` and ``maximum`` overrule all other limits.
    It is illegal to
    """

    @property
    def demand(self) -> float:
        if abs(self._demand - self.target.demand) >= self.granularity:
            self._demand = self.target.demand
        return self._demand

    @demand.setter
    def demand(self, value: float):
        minimum = max(self.minimum, self.target.supply - self.backlog)
        maximum = min(self.maximum, self.target.supply + self.surplus)
        self._demand = type(value)(min(maximum, max(minimum, value)))
        request = value // self.granularity * self.granularity
        self.target.demand = type(value)(min(maximum, max(minimum, request)))

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
