import asyncio
import random
from .adapter import ResourceAdapter


class RandomResource(ResourceAdapter):
    @property
    def utilisation(self):
        return min(1.0, self.demand / self._count)

    @property
    def exhaustion(self):
        return min(1.0, self.demand / self._count)

    def __init__(self, demand=4000, drift_rate=40):
        self.demand = demand
        self.drift_rate = drift_rate
        self._count = demand

    def increase_resources(self):
        self._count += 1

    def decrease_resources(self):
        self._count -= 1

    async def coroutine(self):
        while True:
            self._count += self.drift_rate * (-1 if random.random() > 0.5 else 1)
            print('target %d, current %d, util %.2f%% exh %.2f%%' % (
                self.demand, self._count, self.utilisation, self.exhaustion))
            await asyncio.sleep(1)


if __name__ == '__main__':
    from ..controller.linear import LinearController
    resource = RandomResource(drift_rate=40)
    controller = LinearController(0.1, 0.9, 0.9, resource)
    loop = asyncio.get_event_loop()
    loop.create_task(resource.coroutine())
    loop.create_task(controller.coroutine())
    loop.run_forever()
