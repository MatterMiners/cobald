import pytest

from ..mock.pool import FullMockPool

from cobald.decorator.standardiser import Standardiser


class TestStandardiser(object):
    def test_init_enforcement(self):
        pool = FullMockPool()
        with pytest.raises(ValueError):
            Standardiser(pool, minimum=10, maximum=-10)
        with pytest.raises(ValueError):
            Standardiser(pool, surplus=-20)
        with pytest.raises(ValueError):
            Standardiser(pool, backlog=-20)
        with pytest.raises(ValueError):
            Standardiser(pool, granularity=-20)

    def test_granularity(self):
        pool = FullMockPool()
        for granularity in range(1, 5):
            standardiser = Standardiser(pool, granularity=granularity)
            standardiser.demand = 0
            for multiple in range(5):
                for offset in range(granularity):
                    value = granularity * multiple + offset
                    standardiser.demand = value
                    assert pool.demand % granularity == 0

    def test_granularity_incremental(self):
        """Standardiser: ``demand + n`` equals ``demand + 1 + 1 + 1 ... + 1``"""
        pool = FullMockPool()
        for granularity in (1, 3, 5, 7, 13, 16):
            # wrap first, then reset to test if Standardiser correctly picks this up
            standardiser = Standardiser(pool, granularity=granularity)
            pool.demand = 0
            for total in range(granularity * 5):
                standardiser.demand += 1
                assert pool.demand % granularity == 0
                assert standardiser.demand % granularity == (total + 1) % granularity
                assert standardiser.demand == total + 1

    def test_surplus_backlog(self):
        pool = FullMockPool()
        for base_supply in (10000, 500, 0):
            for surplus in (100, 10, 1):
                standardiser = Standardiser(pool, surplus=surplus)
                pool.supply = base_supply
                standardiser.demand = pool.supply + 2 * surplus
                assert pool.demand == base_supply + surplus
                standardiser.demand = pool.supply - 2 * surplus
                assert pool.demand == base_supply - 2 * surplus
            for backlog in (100, 10):
                standardiser = Standardiser(pool, backlog=backlog)
                pool.supply = base_supply
                standardiser.demand = pool.supply + 2 * backlog
                assert pool.demand == base_supply + 2 * backlog
                standardiser.demand = pool.supply - 2 * backlog
                assert pool.demand == base_supply - backlog

    def test_minimum_maximum(self):
        pool = FullMockPool()
        for minimum in (-100, -10, -1, 0, 10, 100):
            standardiser = Standardiser(pool, minimum=minimum)
            standardiser.demand = minimum - abs(minimum)
            assert pool.demand == minimum
            standardiser.demand = minimum + abs(minimum)
            assert pool.demand == minimum + abs(minimum)
        for maximum in (-100, -10, -1, 0, 10, 100):
            standardiser = Standardiser(pool, maximum=maximum)
            standardiser.demand = maximum + abs(maximum)
            assert pool.demand == maximum
            standardiser.demand = maximum - abs(maximum)
            assert pool.demand == maximum - abs(maximum)
