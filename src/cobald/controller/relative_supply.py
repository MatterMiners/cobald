import trio

from cobald.interfaces import Pool, Controller

from cobald.daemon import service


@service(flavour=trio)
class RelativeSupplyController(Controller):
    """
    Controller that adjusts demand relative to supply

    :param target: the pool to manage
    :param low_utilisation: pool utilisation below which resources are decreased
    :param high_allocation: pool allocation above which resources are increased
    :param low_scale: scale of ``target.supply`` when decreasing resources
    :param high_scale: scale of ``target.supply`` when increasing resources
    :param interval: interval between adjustments in seconds
    """

    def __init__(
        self,
        target: Pool,
        low_utilisation=0.5,
        high_allocation=0.5,
        low_scale=0.9,
        high_scale=1.1,
        interval=1,
    ):
        super().__init__(target=target)
        self.interval = interval
        assert low_utilisation <= high_allocation
        self.low_utilisation = low_utilisation
        self.high_allocation = high_allocation
        assert low_scale <= high_scale
        assert low_scale < 1
        assert high_scale > 1
        self.low_scale = low_scale
        self.high_scale = high_scale

    async def run(self):
        while True:
            self.regulate(self.interval)
            await trio.sleep(self.interval)

    def regulate(self, interval):
        if self.target.utilisation < self.low_utilisation:
            self.target.demand = self.target.supply * self.low_scale
        elif self.target.allocation > self.high_allocation:
            self.target.demand = self.target.supply * self.high_scale
        else:
            self.target.demand = self.target.supply
