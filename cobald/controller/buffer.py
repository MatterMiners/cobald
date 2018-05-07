import asyncio

from cobald.interfaces.parasite import ParaSite
from cobald.interfaces.actor import Actor


@ParaSite.register
@Actor.register
class BufferedController(object):
    def __init__(self, target: ParaSite, interval=10):
        self.interval = interval
        self.demand = target.demand

    async def run(self):
        while True:
            self.target.demand = self.demand
            await asyncio.sleep(self.interval)
