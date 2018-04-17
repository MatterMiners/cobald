import asyncio

from ..resource.adapter import ResourceAdapter


class LinearController(object):
    def __init__(self, interval: float, low_utilisation: float, low_exhaustion: float, adapter: ResourceAdapter):
        self.interval = interval
        self.adapter = adapter
        self.low_utilisation = low_utilisation
        self.low_exhaustion = low_exhaustion

    async def coroutine(self):
        while True:
            self.control()
            await asyncio.sleep(1)

    def control(self):
        if self.adapter.utilisation < self.low_utilisation:
            self.adapter.decrease_resources()
        elif self.adapter.exhaustion > self.low_exhaustion:
            self.adapter.increase_resources()
