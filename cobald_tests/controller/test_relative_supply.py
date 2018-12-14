import pytest

from cobald.controller.relative_supply import RelativeSupplyController
from ..mock.pool import MockPool


class TestRelativeSupplyController(object):
    def test_low_scale(self):
        pool = MockPool()
        with pytest.raises(Exception):
            RelativeSupplyController(pool, low_scale=.9, high_scale=1.0)

    def test_high_scale(self):
        pool = MockPool()
        with pytest.raises(Exception):
            RelativeSupplyController(pool, low_scale=.5, high_scale=.9)

    def test_both_scales(self):
        pool = MockPool()
        with pytest.raises(Exception):
            RelativeSupplyController(pool, low_scale=1.1, high_scale=0.9)
