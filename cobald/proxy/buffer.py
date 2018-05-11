import asyncio

from cobald.interfaces.pool import Pool
from cobald.interfaces.proxy import ProxyPool
from cobald.interfaces.actor import Actor


class Buffer(ProxyPool, Actor):
    """
    A timed buffer for changes to a pool

    :param target: the pool to which changes are applied
    :param window: interval after which changes are applied

    Any changes made to :py:attr:`demand` are stored internally.
    Every ``window`` seconds, the final demand is applied to ``target``.
    """
    demand = 0.0

    def __init__(self, target: Pool, window: float = 10.):
        super().__init__(target=target)
        self.window = window
        self.demand = target.demand

    @asyncio.coroutine
    def run(self):
        while True:
            self.target.demand = self.demand
            self.demand = self.target.demand
            yield from asyncio.sleep(self.window)
