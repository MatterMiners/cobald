from types import FunctionType

from cobald.controller.stepwise import Stepwise, UnboundStepwise, stepwise


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
