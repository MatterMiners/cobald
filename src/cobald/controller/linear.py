import asyncio

from cobald.interfaces import Pool, Controller

from cobald.daemon import service


@service(flavour=asyncio)
class LinearController(Controller):
    """
    Controller that linearly increases or decreases demand

    :param target: the pool to manage
    :param low_utilisation: pool utilisation below which resources are decreased
    :param high_allocation: pool allocation above which resources are increased
    :param rate: maximum change of demand in resources per second
    :param interval: interval between adjustments in seconds
    """

    def __init__(
        self,
        target: Pool,
        low_utilisation: float = 0.5,
        high_allocation: float = 0.5,
        rate: float = 1,
        interval: float = 1,
    ):
        super().__init__(target=target)
        assert rate > 0
        self.rate = rate
        self.interval = interval
        assert low_utilisation <= high_allocation
        self.low_utilisation = low_utilisation
        self.high_allocation = high_allocation

    async def run(self):
        while True:
            self.regulate(self.interval)
            await asyncio.sleep(self.interval)

    def regulate(self, interval: float):
        if self.target.utilisation < self.low_utilisation:
            self.target.demand -= interval * self.rate
        elif self.target.allocation > self.high_allocation:
            self.target.demand += interval * self.rate
