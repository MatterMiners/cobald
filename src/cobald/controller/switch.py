from typing import Union

import trio

from ..interfaces import Pool, Controller
from ..utility import enforce, InvariantError, pairwise
from ..daemon import service


@service(flavour=trio)
class DemandSwitch(Controller):
    """
    Controller that dispatches to slaved controllers based on demand

    .. code:: python

        DemandSwitch(pool, linear_control, 10, supply_control)

    :param target: the pool on which to regulate demand
    :param default: controller to use by default
    :param slaves: pairs of minimum demand to switch and corresponding controller
    :param interval: interval between adjustments in seconds
    """

    def __init__(
        self,
        target: Pool,
        default: Controller,
        *slaves: Union[float, Controller],
        interval=1,
    ):
        super().__init__(target)
        enforce(
            len(slaves) % 2 == 0,
            InvariantError("slaves must be paired with required demands"),
        )
        self._default = default
        self._slaves = tuple(sorted(pairwise(slaves)))
        enforce(
            all(
                (isinstance(demand, (int, float)) and isinstance(slave, Controller))
                for demand, slave in self._slaves
            ),
            InvariantError("slaves must be paired with required demands (float, int)"),
        )
        enforce(
            default.target in (None, target)
            and all(slave.target in (None, target) for _, slave in self._slaves),
            InvariantError("slaves must have None or same target as switch target"),
        )
        default.target = target
        for _, slave in self._slaves:
            slave.target = target
        self.interval = interval

    async def run(self):
        while True:
            self.regulate_demand(self.interval)
            await trio.sleep(self.interval)

    def regulate(self, interval):
        chosen = self._default
        for demand, slave in self._slaves:
            if demand <= self.target.demand:
                chosen = slave
        chosen.regulate(interval)
