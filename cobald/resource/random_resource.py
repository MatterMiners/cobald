import asyncio
import random
from .adapter import ResourceAdapter


class RandomResource(ResourceAdapter):
    @property
    def utilisation(self):
        return min(self.demand / resource for resource in self._resources)

    @property
    def exhaustion(self):
        return max(self.demand / resource for resource in self._resources)

    def __init__(self, demand=4000, dimensions=2, drift_rate=40):
        self.demand = demand
        self.drift_rate = drift_rate
        self._resources = [demand for _ in range(dimensions)]

    def increase_resources(self):
        self._resources = [value + 1 for value in self._resources]

    def decrease_resources(self):
        self._resources = [value + -1 for value in self._resources]

    async def coroutine(self):
        while True:
            self._resources = [
                value - (0 if random.randint(0, 1) else int(4 * self.drift_rate * random.random()))
                for value in self._resources
            ]
            print('\ttarget %d, low %d, high %d, avg %d, util %.2f exh %.2f' % (
                self.demand, min(self._resources), max(self._resources), sum(self._resources) / len(self._resources),
                self.utilisation, self.exhaustion))
            await asyncio.sleep(1)


if __name__ == '__main__':
    from ..controller.linear import LinearController
    resource = RandomResource(drift_rate=10)
    controller = LinearController(0.05, 0.95, 0.975, resource)
    loop = asyncio.get_event_loop()
    loop.create_task(resource.coroutine())
    loop.create_task(controller.coroutine())
    loop.run_forever()
