import asyncio

from cobald.interfaces.pool import Pool
from cobald.interfaces.controller import Controller
from cobald.interfaces.actor import Actor


class LinearController(Controller, Actor):
    """
    Controller that linearly increases or decreases demand

    :param target: the pool to manage
    :param low_utilisation: pool utilisation below which resources are decreased
    :param high_consumption: pool consumption above which resources are increased
    :param rate: maximum change of demand in resources per second
    """
    @property
    def rate(self):
        return 1 / self._interval

    @rate.setter
    def rate(self, value):
        self._interval = 1 / value

    def __init__(self, target: Pool, low_utilisation=0.5, high_consumption=0.5, rate=1):
        super().__init__(target=target)
        self._interval = None
        self.rate = rate
        self.low_utilisation = low_utilisation
        self.high_consumption = high_consumption

    @asyncio.coroutine
    def run(self):
        while True:
            if self.target.utilisation <= self.low_utilisation:
                self.target.demand -= 1
            elif self.target.consumption >= self.high_consumption:
                self.target.demand += 1
            yield from asyncio.sleep(self._interval)
