import pytest

from cobald.interfaces import Controller, PoolDecorator, Partial

from ..mock.pool import FullMockPool


class MockController(Controller):
    def regulate(self, interval: float): ...


class MockDecorator(PoolDecorator): ...


class TestPartial(object):
    def test_bind(self):
        """Basic binding as ``controller >> pool``"""
        partial_control = MockController.s()
        assert isinstance(partial_control, Partial)
        pipeline = partial_control >> FullMockPool()
        assert isinstance(pipeline, MockController)

    def test_recursive_bind(self):
        """Recursive binding as ``controller >> deco >> deco >> pool``"""
        partial_control = MockController.s()
        assert isinstance(partial_control, Partial)
        partial_decorator = MockDecorator.s()
        assert isinstance(partial_decorator, Partial)
        pipeline = (
            partial_control >> partial_decorator >> partial_decorator >> FullMockPool()
        )
        assert isinstance(pipeline, MockController)
        assert isinstance(pipeline.target, MockDecorator)
        assert isinstance(pipeline.target.target, MockDecorator)
        assert isinstance(pipeline.target.target.target, FullMockPool)

    def test_recursive_curry(self):
        """Repeated partial application and variadic currying"""
        partial_control = MockController.s()
        assert isinstance(partial_control, Partial)
        for _ in range(3):
            partial_control = partial_control()
            assert isinstance(partial_control, Partial)
        pipeline = partial_control >> FullMockPool()
        assert isinstance(pipeline, MockController)

    def test_pool_curry_bind(self):
        """Curry and bind the last element of a pipeline"""
        partial_pool = FullMockPool.s()
        assert isinstance(partial_pool, Partial)
        partial_pool = partial_pool(demand=10)
        assert isinstance(partial_pool, Partial)
        partial_control = MockController.s()
        pipeline = partial_control >> partial_pool
        assert isinstance(pipeline, MockController)
        assert isinstance(pipeline.target, FullMockPool)
        assert pipeline.target.demand == 10

    def test_pool_recursive(self):
        """Curry and bind the last element of a long pipeline"""
        partial_pool = FullMockPool.s(demand=10)
        for _ in range(3):
            partial_pool = partial_pool()
            assert isinstance(partial_pool, Partial)
        pipeline = (
            MockController.s() >> MockDecorator.s() >> MockDecorator.s() >> partial_pool
        )
        assert isinstance(pipeline, MockController)
        assert isinstance(pipeline.target, MockDecorator)
        assert isinstance(pipeline.target.target, MockDecorator)
        assert isinstance(pipeline.target.target.target, FullMockPool)
        assert pipeline.target.target.target.demand == 10

    def test_signature_check(self):
        class ArgController(Controller):
            def __init__(self, target, a, b, c=3, *, kwa=2, kwb=3):
                super().__init__(target)
                self.data = a, b, c, kwa, kwb

        partial_control = ArgController.s()
        # incomplete arguments are okay
        assert isinstance(partial_control(1, kwa=3), Partial)
        # additional arguments are eagerly checked
        with pytest.raises(TypeError):
            partial_control(1, 2, 3, 4)  # too many *args
        with pytest.raises(TypeError):
            partial_control(d=4)  # wrong keyword
        with pytest.raises(TypeError):
            partial_control(1, a=2)  # duplicate positional/keyword
        # target cannot be curried
        with pytest.raises(TypeError):
            partial_control(target=2)
