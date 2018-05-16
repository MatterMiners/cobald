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
