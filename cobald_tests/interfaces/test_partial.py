from cobald.interfaces import Controller, PoolDecorator, Partial

from ..mock.pool import FullMockPool


class MockController(Controller):
    def regulate(self, interval: float):
        ...


class MockDecorator(PoolDecorator):
    ...


class TestPartial(object):
    def test_bind(self):
        partial_control = MockController.s()
        assert isinstance(partial_control, Partial)
        pipeline = partial_control >> FullMockPool()
        assert isinstance(pipeline, MockController)

    def test_recursive_bind(self):
        partial_control = MockController.s()
        assert isinstance(partial_control, Partial)
        partial_decorator = MockDecorator.s()
        assert isinstance(partial_decorator, Partial)
        pipeline = partial_control >> partial_decorator >> partial_decorator >> FullMockPool()
        assert isinstance(pipeline, MockController)
        assert isinstance(pipeline.target, MockDecorator)
        assert isinstance(pipeline.target.target, MockDecorator)
        assert isinstance(pipeline.target.target.target, FullMockPool)

    def test_recursive_curry(self):
        partial_control = MockController.s()
        assert isinstance(partial_control, Partial)
        for _ in range(3):
            partial_control = partial_control()
            assert isinstance(partial_control, Partial)
        pipeline = partial_control >> FullMockPool()
        assert isinstance(pipeline, MockController)
