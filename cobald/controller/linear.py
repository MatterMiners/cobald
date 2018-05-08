import asyncio

from cobald.interfaces.pool import Pool
from cobald.interfaces.actor import Actor


class LinearController(Actor):
    @property
    def rate(self):
        return 1 / self._interval

    @rate.setter
    def rate(self, value):
        self._interval = 1 / value

    def __init__(self, target: Pool, low_utilisation=0.5, high_consumption=0.5, rate=1):
        self._interval = None
        self.rate = rate
        self.target = target
        self.low_utilisation = low_utilisation
        self.high_consumption = high_consumption

    async def run(self):
        while True:
            if self.target.utilisation <= self.low_utilisation:
                self.target.demand -= 1
            elif self.target.consumption >= self.high_consumption:
                self.target.demand += 1
            await asyncio.sleep(self._interval)
