from types import FunctionType

from cobald.controller.stepwise import Stepwise, UnboundStepwise, stepwise

from ..mock.pool import FullMockPool


class TestStepwise:
    def test_add(self):
        @stepwise
        def control(pool, interval):
            ...

        assert isinstance(control, UnboundStepwise)

        @control.add(supply=20)
        def rule(pool, interval):
            ...

        assert isinstance(control, UnboundStepwise)
        assert isinstance(rule, FunctionType)

    def test_instantiate(self):
        @stepwise
        def control(pool, interval):
            ...

        assert isinstance(control(FullMockPool()), Stepwise)
        assert isinstance(control.s() >> FullMockPool(), Stepwise)
        assert isinstance(control(FullMockPool(), interval=10), Stepwise)
        assert isinstance(control.s(interval=10) >> FullMockPool(), Stepwise)

        @control.add(supply=20)
        def rule(pool, interval):
            ...

        assert isinstance(control(FullMockPool()), Stepwise)
        assert isinstance(control.s() >> FullMockPool(), Stepwise)
        assert isinstance(control(FullMockPool(), interval=10), Stepwise)
        assert isinstance(control.s(interval=10) >> FullMockPool(), Stepwise)
