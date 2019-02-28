from cobald.interfaces import Controller, Partial

from ..mock.pool import FullMockPool


class MockController(Controller):
    def regulate(self, interval: float):
        ...


class TestPartial(object):
    def test_bind(self):
        partial_control = MockController.s()
        assert isinstance(partial_control, Partial)
        pipeline = partial_control >> FullMockPool()
        assert isinstance(pipeline, MockController)
