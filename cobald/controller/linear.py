import trio

from cobald.interfaces import Pool, Controller

from cobald.daemon import service


@service(flavour=trio)
class LinearController(Controller):
    """
    Controller that linearly increases or decreases demand

    :param target: the pool to manage
    :param low_utilisation: pool utilisation below which resources are decreased
    :param high_allocation: pool allocation above which resources are increased
    :param rate: maximum change of demand in resources per second
    """
    @property
    def rate(self):
        return 1 / self._interval

    @rate.setter
    def rate(self, value):
        self._interval = 1 / value

    def __init__(self, target: Pool, low_utilisation=0.5, high_allocation=0.5, rate=1):
        super().__init__(target=target)
        self._interval = None
        assert rate > 0
        self.rate = rate
        assert low_utilisation <= high_allocation
        self.low_utilisation = low_utilisation
        self.high_allocation = high_allocation

    async def run(self):
        while True:
            self.regulate_demand()
            await trio.sleep(self._interval)

    def regulate_demand(self):
        if self.target.utilisation < self.low_utilisation:
            self.target.demand -= 1
        elif self.target.allocation > self.high_allocation:
            self.target.demand += 1
