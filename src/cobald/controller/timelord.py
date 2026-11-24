from datatime import datetime

import trio

from cobald.interfaces import Pool, Controller

from cobald.daemon import service


@service(flavour=trio)
class TimelordController(Controller):
    """
    Time based Controller to test further demand in intervals. Between the intervals the demand set to zero.

    :param target: the pool to manage
    :param low_utilisation: pool utilisation below which resources are decreased
    :param high_allocation: pool allocation above which resources are increased
    :param rate: maximum change of demand in resources per second
    :param interval: interval between adjustments in seconds
    :param test_interval: test interval in seconds
    :param test_intermission: interval between test interval in seconds
    """

    def __init__(
        self, target: Pool, low_utilisation=0.5, high_allocation=0.5, rate=1, interval=1, test_interval=600,
            test_intermission=3000,
    ):
        super().__init__(target=target)
        assert rate > 0
        self.rate = rate
        self.interval = interval
        assert low_utilisation <= high_allocation
        self.low_utilisation = low_utilisation
        self.high_allocation = high_allocation
        assert test_intermission > 0
        self.test_intermission = test_intermission
        self.next_test_start_date = datatime.datetime.now()
        assert test_interval > 0
        self.test_interval = test_interval
        self.update_test_date = False

    async def run(self):
        while True:
            self.regulate(self.interval)
            await trio.sleep(self.interval)

    def regulate(self, interval):
        if (self.next_test_start_date + self.test_interval) < datatime.datetime.now() and\
                self.next_test_start_date > datetime.datetime.now():
            self.update_test_date = True
            if self.target.utilisation < self.low_utilisation:
                self.target.demand -= interval * self.rate
            elif self.target.allocation > self.high_allocation:
                self.target.demand += interval * self.rate
        else:
            if self.update_test_date:
                self.next_test_start_date += self.test_interval + self.test_intermission
                self.update_test_date = False
            self.target.demand = 0
