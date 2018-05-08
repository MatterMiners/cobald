import asyncio

from cobald.interfaces.pool import Pool
from cobald.interfaces.actor import Actor


@Pool.register
@Actor.register
class BufferedController(object):
    def __init__(self, target: Pool, interval=10):
        self.interval = interval
        self.demand = target.demand

    async def run(self):
        while True:
            self.target.demand = self.demand
            await asyncio.sleep(self.interval)
