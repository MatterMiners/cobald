import json
import logging
import time

from cobald.monitor.format_json import JsonFormatter

from . import make_test_logger


class TestFormatJson(object):
    def test_payload(self):
        for payload in (
                {'a': 'a'},
                {str(i): i for i in range(20)},
        ):
            logger, handler = make_test_logger(__name__)
            handler.formatter = JsonFormatter()
            logger.critical('message', payload)
            data = json.loads(handler.content)
            assert len(data) == len(payload) + 2
            assert data.pop('message') == 'message'
            assert data.pop('time')
            assert data == payload

    def test_default_timestamp(self):
        now = time.time()
        payload = {'a': 'a', '1': 1, '2.2': 2.2}
        logger, handler = make_test_logger(__name__)
        handler.formatter = JsonFormatter()
        logger.critical('message', payload, extra={'created': now})
        data = json.loads(handler.content)
        assert len(data) == len(payload) + 2
        # from Formatter and LogRecord
        ct = time.localtime(now)
        msecs = (now - int(now)) * 1000
        default_time_string = logging.Formatter.default_msec_format % (
            time.strftime(logging.Formatter.default_time_format, ct),
            msecs
        )
        assert data.pop('time') == default_time_string

    def test_explicit_timestamp(self):
        now = time.time()
        payload = {'a': 'a', '1': 1, '2.2': 2.2}
        logger, handler = make_test_logger(__name__)
        handler.formatter = JsonFormatter(datefmt='%Y')
        logger.critical('message', payload, extra={'created': now})
        data = json.loads(handler.content)
        assert len(data) == len(payload) + 2
        # from Formatter and LogRecord
        ct = time.localtime(now)
        default_time_string = time.strftime('%Y', ct)
        assert data.pop('time') == default_time_string

    def test_disabled_timestamp(self):
        now = time.time()
        payload = {'a': 'a', '1': 1, '2.2': 2.2}
        logger, handler = make_test_logger(__name__)
        handler.formatter = JsonFormatter(datefmt='')
        logger.critical('message', payload, extra={'created': now})
        data = json.loads(handler.content)
        assert len(data) == len(payload) + 1
        assert 'time' not in data

    def test_payload_empty(self):
        logger, handler = make_test_logger(__name__)
        handler.formatter = JsonFormatter()
        logger.critical('message', {})
        data = json.loads(handler.content)
        assert len(data) == 2

    def test_default(self):
        logger, handler = make_test_logger(__name__)
        handler.formatter = JsonFormatter(fmt={"test": 1})
        logger.critical('message', {'drones': 1})
        data = json.loads(handler.content)
        assert data.pop("test") == 1
        handler.clear()
        logger.critical('message', {'test': 2})
        data = json.loads(handler.content)
        assert data.pop("test") == 2
        assert len(data) == 2
        handler.clear()
        logger.critical('message', {})
        data = json.loads(handler.content)
        assert data.pop("test") == 1
        assert len(data) == 2
