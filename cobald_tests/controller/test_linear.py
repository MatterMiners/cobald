import pytest

from ..mock.pool import MockPool

from cobald.controller.linear import LinearController


class TestLinearController(object):
    def test_init(self):
        with pytest.raises(TypeError):
            LinearController()

    def test_init_with_pool(self):
        pool = MockPool()
        controller = LinearController(target=pool)
        pool.utilisation = 1.0

        expected_demand = 0
        for i in range(2):
            assert(pool.demand == expected_demand)
            controller.regulate_demand()
            expected_demand += 1

        pool.utilisation = 0.0
        for i in range(2):
            assert (pool.demand == expected_demand)
            controller.regulate_demand()
            expected_demand -= 1

    def test_utilisation(self):
        pool = MockPool()
        controller = LinearController(target=pool, low_utilisation=0.5)

        old_demand = pool.demand = 1
        pool.utilisation = pool.allocation = 1.0
        controller.regulate_demand()
        assert(pool.demand - old_demand == 1)

        old_demand = pool.demand = 1
        pool.utilisation = pool.allocation = 0.0
        controller.regulate_demand()
        assert(pool.demand - old_demand == -1)

        old_demand = pool.demand = 1
        pool.utilisation = pool.allocation = controller.low_utilisation
        controller.regulate_demand()
        assert(pool.demand - old_demand == 0)

        old_demand = pool.demand = 1
        pool.utilisation = pool.allocation = controller.low_utilisation - .01
        controller.regulate_demand()
        assert (pool.demand - old_demand == -1)

        old_demand = pool.demand = 1
        pool.utilisation = pool.allocation = controller.low_utilisation + .01
        controller.regulate_demand()
        assert(pool.demand - old_demand == 1)

    def test_allocation(self):
        pool = MockPool()
        controller = LinearController(target=pool, high_allocation=0.5)

        old_demand = pool.demand = 1
        pool.allocation = pool.utilisation = 1.0
        controller.regulate_demand()
        assert(pool.demand - old_demand == 1)

        old_demand = pool.demand = 1
        pool.allocation = pool.utilisation = 0.0
        controller.regulate_demand()
        assert(pool.demand - old_demand == -1)

        old_demand = pool.demand = 1
        pool.allocation = pool.utilisation = controller.high_allocation
        controller.regulate_demand()
        assert(pool.demand - old_demand == 0)

        old_demand = pool.demand = 1
        pool.allocation = pool.utilisation = controller.high_allocation + 0.01
        controller.regulate_demand()
        assert (pool.demand - old_demand == 1)

        old_demand = pool.demand = 1
        pool.allocation = pool.utilisation = controller.high_allocation - 0.01
        controller.regulate_demand()
        assert (pool.demand - old_demand == -1)

    def test_low_high(self):
        pool = MockPool()
        with pytest.raises(AssertionError):
            LinearController(target=pool, low_utilisation=1, high_allocation=0)
        assert(LinearController(target=pool, low_utilisation=.5, high_allocation=.5))
        assert(LinearController(target=pool, low_utilisation=.1, high_allocation=.9))

    def test_rate(self):
        pool = MockPool()
        with pytest.raises(AssertionError):
            LinearController(target=pool, rate=0)
        controller = LinearController(target=pool, rate=1)
        assert controller.rate == 1
        controller = LinearController(target=pool, rate=2)
        assert controller.rate == 2
        controller = LinearController(target=pool, rate=1/3)
        assert controller.rate == 1/3

