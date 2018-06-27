import json
import io
import logging
import threading
import itertools


from cobald.monitor.format_json import JsonFormatter, RECORD_ATTRIBUTES


class CapturingHandler(logging.StreamHandler):
    @property
    def content(self):
        return self.stream.getvalue()

    def __init__(self):
        super().__init__(stream=io.StringIO())


_test_index = 0
_index_lock = threading.Lock()


def make_test_logger(base_name: str = 'test_logger'):
    with _index_lock:
        global _test_index
        log_name = base_name + '.test%d' % _test_index
        _test_index += 1
    logger = logging.getLogger(log_name)
    handler = CapturingHandler()
    logger.handlers = [handler]
    return logger, handler


class TestFormatJson(object):
    def test_record_attributes(self):
        for attributes in itertools.product(RECORD_ATTRIBUTES, repeat=2):
            attributes = set(attributes)
            logger, handler = make_test_logger(__name__)
            handler.formatter = JsonFormatter(record_attributes=attributes)
            logger.critical('message')
            data = json.loads(handler.content)
            for attribute in attributes:
                assert attribute in data
            assert len(data) == len(attributes)

    def test_remap_attributes(self):
        for attributes in itertools.product(RECORD_ATTRIBUTES, repeat=2):
            attributes = {attr: key for attr, key in zip(attributes, 'abcdefg')}
            logger, handler = make_test_logger(__name__)
            handler.formatter = JsonFormatter(record_attributes=attributes)
            logger.critical('message')
            data = json.loads(handler.content)
            for attribute, key in attributes.items():
                assert key in data
                assert attribute not in data
            assert len(data) == len(attributes)
