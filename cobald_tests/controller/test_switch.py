import pytest

from ..mock.pool import MockPool

from cobald.controller.linear import LinearController
from cobald.controller.switch import DemandSwitch


class TestSwitchController(object):
    def test_select(self):
        pool = MockPool()
        switch_controller = DemandSwitch(pool, LinearController(pool, rate=1), 5, LinearController(pool, rate=2))
        pool.utilisation = pool.allocation = 1.0
        expected_demand = 0
        for i in range(5):
            switch_controller.regulate(1)
            expected_demand += 1
            assert(pool.demand == expected_demand)
        for i in range(5):
            assert(pool.demand == expected_demand)
            switch_controller.regulate(1)
            expected_demand += 2
