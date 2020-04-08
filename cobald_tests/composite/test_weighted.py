import pytest

from ..mock.pool import FullMockPool

from cobald.composite.weighted import WeightedComposite


class TestWeightedComposite(object):
    def test_init(self):
        pool = FullMockPool()
        WeightedComposite(pool)

        with pytest.raises(AssertionError):
            WeightedComposite(pool, weight="ShouldFail")

        for weight in ("supply", "utilisation", "allocation"):
            WeightedComposite(pool, weight=weight)

    def test_demand(self):
        pools = [FullMockPool(), FullMockPool()]
        pools[0].demand = 123
        pools[1].demand = 456

        composite = WeightedComposite(*pools)
        assert composite.demand == 579

        # test demand setter weighted by supply (default)

        pools[0].supply = 100
        pools[1].supply = 200

        composite.demand = 300
        assert pools[0].demand == 100
        assert pools[1].demand == 200

        # test demand setter weighted by utilisation, allocation, supply

        for weight in ("utilisation", "allocation", "supply"):
            pools = [FullMockPool(), FullMockPool()]
            composite = WeightedComposite(*pools, weight=weight)
            setattr(pools[0], weight, 0.25)
            setattr(pools[1], weight, 0.75)

            composite.demand = 400
            assert pools[0].demand == 100
            assert pools[1].demand == 300

    def test_supply(self):
        pools = [FullMockPool(), FullMockPool()]
        composite = WeightedComposite(*pools)
        pools[0].supply = 100
        pools[1].supply = 200

        assert composite.supply == 300

    def test_utilisation(self):
        pools = [FullMockPool(), FullMockPool()]
        pools[0].supply = 0
        pools[1].supply = 0

        composite = WeightedComposite(*pools)

        assert composite.utilisation == 1.0

        pools[0].supply = 100
        pools[1].supply = 200
        pools[0].utilisation = 0.9
        pools[1].utilisation = 0.6

        assert composite.utilisation == 0.7

    def test_allocation(self):
        pools = [FullMockPool(), FullMockPool()]
        pools[0].supply = 0
        pools[1].supply = 0

        composite = WeightedComposite(*pools)

        assert composite.allocation == 1.0

        pools[0].supply = 100
        pools[1].supply = 200
        pools[0].allocation = 0.9
        pools[1].allocation = 0.6

        assert composite.allocation == 0.7

    @pytest.mark.parametrize('weight', ['supply', 'allocation', 'utilisation'])
    def test_fitness_fallback(self, weight):
        # empty composite should always assume perfect fitness
        composite = WeightedComposite(weight=weight)
        assert composite.supply == 0
        assert composite.allocation == 1
        assert composite.utilisation == 1
        children = [
            FullMockPool(demand=0, supply=0, allocation=0.0, utilisation=0.0)
            for _ in range(5)
        ]
        composite.children.extend(children)
        assert composite.supply == 0
        assert composite.allocation == 1
        assert composite.utilisation == 1
        # full composite fitness is correct
        for child in children:
            child.supply = 1
        assert composite.supply == len(children)
        assert composite.allocation == 0
        assert composite.utilisation == 0
