import pytest

from cobald.controller.relative_supply import RelativeSupplyController
from ..mock.pool import MockPool


class TestRelativeSupplyController(object):
    def test_low_scale(self):
        pool = MockPool()
        with pytest.raises(Exception):
            RelativeSupplyController(pool, low_scale=0.9, high_scale=1.0)

    def test_high_scale(self):
        pool = MockPool()
        with pytest.raises(Exception):
            RelativeSupplyController(pool, low_scale=0.5, high_scale=0.9)

    def test_both_scales(self):
        pool = MockPool()
        with pytest.raises(Exception):
            RelativeSupplyController(pool, low_scale=1.1, high_scale=0.9)

    def test_adjustment(self):
        pool = MockPool()
        relative_supply_controller = RelativeSupplyController(pool)
        pool.utilisation = pool.allocation = 1.0
        expected_demand = 0
        for _ in range(5):
            relative_supply_controller.regulate(1)
            assert pool.demand == expected_demand
        pool.demand = 1
        for _ in range(5):
            expected_demand = pool.supply * relative_supply_controller.high_scale
            relative_supply_controller.regulate(1)
            assert pool.demand == expected_demand
        pool.utilisation = pool.allocation = 0.1
        for _ in range(5):
            expected_demand = pool.supply * relative_supply_controller.low_scale
            relative_supply_controller.regulate(1)
            assert pool.demand == expected_demand
        pool.utilisation = pool.allocation = 0.5
        expected_demand = pool.supply
        for _ in range(5):
            relative_supply_controller.regulate(1)
            assert pool.demand == expected_demand
