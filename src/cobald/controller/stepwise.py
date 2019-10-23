from functools import partial
from itertools import chain
from typing import Callable, Tuple, Optional, TypeVar, List, Set, Dict, overload

import trio

from ..interfaces import Pool, Controller, Partial
from ..daemon import service

C = TypeVar("C", bound="Controller")

#: Individual control rule for a pool on a given interval
#:
#: When a rule for a :py:class:`Stepwise` is invoked, it receives
#: the ``pool`` to manage and the ``interval`` elapsed since the
#: last modification.
#: It should either *return* the new :py:attr:`~.Pool.demand`, or
#: :py:const:`None` to indicate no change; the latter can also
#: mean that the function does not hit a ``return`` statement.
#:
#: .. py:function:: \ rule(pool: Pool, interval: float) -> Optional[float]
#:
#: Note that a rule should *not* modify the ``pool`` directly.
ControlRule = Callable[[Pool, float], Optional[float]]


class RangeSelector(object):
    """
    Container that stores rules for the range of their supply bounds

    :param base: base rule that has no lower bound
    :param rules: lower bound and its control rule
    """

    def __init__(self, base: ControlRule, *rules: Tuple[float, ControlRule]):
        self._lookup = self._compile_lookup(base, rules)

    def get_rule(self, supply: float):
        for (low, high), rule in self._lookup.items():
            if low <= supply < high:
                return rule

    @staticmethod
    def _compile_lookup(base, rules) -> Dict[Tuple[float, float], ControlRule]:
        if not rules:
            return {(0, float("inf")): base}
        lookup = {}
        thresholds, _rules = zip(*sorted(rules))
        for low, high, rule in zip(
            chain([0], thresholds),
            chain(thresholds, [float("inf")]),
            chain([base], _rules),
        ):
            if low == high:
                raise ValueError("Duplicate entries for threshold %s" % low)
            lookup[low, high] = rule
        return lookup


@service(flavour=trio)
class Stepwise(Controller):
    """
    Controller that selects from several strategies based on supply

    :see: :py:class:`UnboundStepwise` allows creating :py:class:`Stepwise` instances
          via decorators.
    """

    def __init__(
        self,
        target: Pool,
        base: ControlRule,
        *rules: Tuple[float, ControlRule],
        interval: float = 1,
    ):
        super().__init__(target)
        self.interval = interval
        self._selector = RangeSelector(base, *rules)

    async def run(self):
        target, interval = self.target, self.interval
        while True:
            current_rule = self._selector.get_rule(target.supply)
            demand = current_rule(target, interval)
            if demand is not None:
                self.target.demand = demand
            await trio.sleep(interval)


class UnboundStepwise(object):
    """
    Decorator interface for constructing a :py:class:`Stepwise` controller

    Apply this as a decorator to a :py:data:`~.ControlRule` callable to create
    a basic controller skeleton.
    The initial callable forms the base rule.
    Additional rules can be added for specific :py:attr:`~.Pool.supply` thresholds
    using :py:meth:`~.UnboundStepwise.add`.

    The skeleton can be used like a regular :py:class:`~.Controller`:
    calling it with a :py:class:`~.Pool` and update ``interval`` creates
    a :py:class:`~.Controller` instance with the given rules for the
    :py:class:`~.Pool`.

    .. code:: python

        # initial controller skeleton from base case
        @stepwise
        def control(pool: Pool, interval):
            return 10

        # additional rules above specific supply thresholds
        @control.add(supply=10)
        def quantized(pool: Pool, interval):
            if pool.utilisation < 0.5:
                return pool.supply - 1
            elif pool.allocation > 0.5:
                return pool.supply + 1

        @control.add(supply=100)
        def continuous(pool: Pool, interval):
            if pool.utilisation < 0.5:
                return pool.supply * 1.1
            elif pool.allocation > 0.5:
                return pool.supply * 0.9

        # create controller from skeleton
        pipeline = control(pool, interval=10)
    """

    def __init__(self, base: ControlRule):
        self.base = base
        self.rules = []  # type: List[Tuple[float, ControlRule]]
        self._thresholds = set()  # type: Set[float]

    @overload  # noqa: F811
    def add(self, rule: ControlRule, *, supply: float) -> ControlRule:
        ...

    @overload  # noqa: F811
    def add(self, rule: None, *, supply: float) -> Callable[[ControlRule], ControlRule]:
        ...

    def add(self, rule: ControlRule = None, *, supply: float):  # noqa: F811
        """
        Register a new rule above a given ``supply`` threshold

        Registration supports a single-argument form for use as a decorator,
        as well as a two-argument form for direct application.
        Use the former for ``def`` or ``class`` definitions,
        and the later for ``lambda`` functions and existing callables.

        .. code:: python

            @control.add(supply=10)
            def linear(pool, interval):
                if pool.utilisation < 0.75:
                    return pool.supply - interval
                elif pool.allocation > 0.95:
                    return pool.supply + interval

            control.add(
                lambda pool, interval: pool.supply * (
                    1.2 if pool.allocation > 0.75 else 0.9
                ),
                supply=100
            )
        """
        if supply in self._thresholds:
            raise ValueError("rule for threshold %s re-defined" % supply)
        if rule is not None:
            self.rules.append((supply, rule))
            self._thresholds.add(supply)
            return rule
        else:
            return partial(self.add, supply=supply)

    def s(self, *args, **kwargs) -> Partial[Stepwise]:
        """
        Create an unbound prototype of this class, partially applying arguments

        .. code:: python

            @stepwise
            def control(pool: Pool, interval):
                return 10

            pipeline = control.s(interval=20) >> pool

        :note: The partial rules are sealed, and :py:meth:`~.UnboundStepwise.add`
               cannot be called on it.
        """
        return Partial(Stepwise, self.base, *self.rules, *args, __leaf__=True, **kwargs)

    def __call__(self, target: Pool, interval: float = None):
        if interval is None:
            return Stepwise(target, self.base, *self.rules)
        return Stepwise(target, self.base, *self.rules, interval=interval)


stepwise = UnboundStepwise
