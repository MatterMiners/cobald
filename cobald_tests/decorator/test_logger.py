import threading
import logging
import io
import warnings

import pytest

from ..mock.pool import FullMockPool

from cobald.decorator.logger import Logger


class CapturingHandler(logging.StreamHandler):
    @property
    def content(self) -> str:
        return self.stream.getvalue()

    def __init__(self):
        super().__init__(stream=io.StringIO())


_test_index = 0
_index_lock = threading.Lock()


def make_logger(base_name: str = "test_logger"):
    global _test_index
    with _index_lock:
        log_name = base_name + ".test%d" % _test_index
        _test_index += 1
    logger = logging.getLogger(log_name)
    logger.propagate = False
    handler = CapturingHandler()
    logger.handlers = [handler]
    return logger, handler


class TestLogger(object):
    def test_transparent_logging(self):
        pool = FullMockPool()
        logger, handler = make_logger()
        chain = Logger(target=pool, name=logger.name)
        chain.demand += 1
        assert handler.content
        assert chain.demand == pool.demand
        assert chain.utilisation == pool.utilisation
        assert chain.allocation == pool.allocation

    def test_name(self):
        pool = FullMockPool()
        chain = Logger(target=pool, name="default")
        assert chain.name == "default"
        chain.name = None
        assert chain.name == pool.__class__.__name__
        chain.name = "final"
        assert chain.name == "final"

    def test_verification(self):
        pool = FullMockPool()
        # ensure no warnings by default
        # see https://docs.pytest.org/en/8.0.x/how-to/capture-warnings.html#additional-use-cases-of-warnings-in-tests  # noqa
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            Logger(target=pool, name="test logger")

        pool = FullMockPool()
        with pytest.warns(FutureWarning):
            Logger(
                target=pool,
                name="test logger",
                message="logging deprecated %(consumption)s",
            )

        pool = FullMockPool()
        with pytest.raises(RuntimeError):
            Logger(
                target=pool,
                name="test logger",
                message="logging invalid %(dummy_field)s",
            )
