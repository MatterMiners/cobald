import asyncio

from cobald.interfaces.pool import ProxyPool, Pool
from cobald.interfaces.actor import Actor


@Actor.register
class BufferedController(ProxyPool):
    demand = 0.0

    def __init__(self, target: Pool, window=10):
        super().__init__(target=target)
        self.window = window
        self.demand = target.demand

    async def run(self):
        while True:
            self.target.demand = self.demand
            await asyncio.sleep(self.window)
