from typing import Callable
import weakref

import trio

from cobald.interfaces import Pool, CompositePool
from cobald.daemon import service


@service(flavour=trio)
class FactoryPool(CompositePool):
    """
    Composition that adds and removes pools to satisfy demand

    :param factory: a callable that produces a single new :py:class:`~.Pool` on each invocation
    :param interval: how often to adjust the number of children

    Adjustment uses two extensions that children must respond to adequately:

    * When spawned via ``factory()``, children shall already be set to their expected ``demand``.
    * When disabled via ``demand=0``, children shall shut down and free any resources and tasks.

    Once spawned, children are free to adjust their demand if required.
    The :py:class:`FactoryPool` re-inspects demand before spawning or disabling children.
    """
    @property
    def children(self):
        return [*self._hatchery, *self._mortuary]

    @property
    def demand(self):
        return self._demand

    @demand.setter
    def demand(self, value):
        # we may spend an arbitrary time spawning Drones, just acknowledge demand and defer any actions
        self._demand = value

    @property
    def supply(self):
        return sum(child.supply for child in self.children)

    @property
    def utilisation(self):
        try:
            return sum(child.utilisation for child in self._children) / len(self._children)
        except ZeroDivisionError:
            return 1.

    @property
    def allocation(self):
        try:
            return sum(child.allocation for child in self._children) / len(self._children)
        except ZeroDivisionError:
            return 1.

    def __init__(self, *children: Pool, factory: Callable[..., Pool], interval: float = 30):
        self._demand = sum(child.demand for child in children)
        #: children fulfilling our demand
        self._hatchery = set(children)
        #: children shutting down
        self._mortuary = weakref.WeakSet()
        self.factory = factory
        self.interval = interval

    async def run(self):
        while True:
            await trio.sleep_until(self.interval)
            # freeze target demand in case another thread updates us
            supply, demand = self.supply, self.demand
            if supply > demand:
                await self._shrink(target=demand)
            else:
                await self._grow(target=demand)

    async def _shrink(self, target: float):
        # we can only reap children that are not already shutting down
        # prefer reaping children that supply few used resources
        hit_list = sorted(self._hatchery, key=lambda child: child.supply * child.utilisation)
        excess_demand = sum(child.demand for child in hit_list) - target
        for child in hit_list:
            if excess_demand <= 0:
                break
            # reap child
            if child.demand <= excess_demand:
                excess_demand -= child.demand
                child.demand = 0
                self._hatchery.discard(child)
                self._mortuary.add(child)

    async def _grow(self, target: float):
        missing_demand = target - sum(child.demand for child in self.children)
        while missing_demand > 0:
            new_child = self.factory()
            self._hatchery.add(new_child)
            assert new_child.demand > 0, 'factory must produce children with initial demand'
            missing_demand -= new_child.demand
