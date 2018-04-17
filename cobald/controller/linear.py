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
            await asyncio.sleep(self.interval)

    def control(self):
        if self.adapter.utilisation < self.low_utilisation:
            print('-', end='')
            self.adapter.decrease_resources()
        elif self.adapter.exhaustion > self.low_exhaustion:
            print('+', end='')
            self.adapter.increase_resources()
        else:
            print('=', end='')
