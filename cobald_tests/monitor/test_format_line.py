import time
import ast

from cobald.monitor.format_line import LineProtocolFormatter

from . import make_test_logger


def parse_line_protocol(literal: str):
    name_tags, _, fields_stamp = literal.strip().partition(' ')
    fields, _, stamp = fields_stamp.partition(' ')
    fields = fields.split(',') if fields else []
    name, *tags = name_tags.split(',')
    return name, {
        key: value
        for key, value
        in (tag.split('=') for tag in tags)
    }, {
        key: ast.literal_eval(value)
        for key, value
        in (field.split('=') for field in fields)
    }, None if not stamp else int(stamp)


class TestFormatLine(object):
    def test_payload(self):
        for payload in (
                {'a': 'a'},
                {str(i): i for i in range(20)},
        ):
            logger, handler = make_test_logger(__name__)
            handler.formatter = LineProtocolFormatter()
            logger.critical('message', payload)
            name, tags, fields, timestamp = parse_line_protocol(handler.content)
            assert len(fields) == len(payload)
            assert fields == payload
            assert timestamp is None

    def test_timestamp_resolution(self):
        now = time.time()
        payload = {'a': 'a', '1': 1, '2.2': 2.2}
        for resolution in (100, 10, 1):
            logger, handler = make_test_logger(__name__)
            handler.formatter = LineProtocolFormatter(resolution=resolution)
            logger.critical('message', payload, extra={'created': now})
            name, tags, fields, timestamp = parse_line_protocol(handler.content)
            assert len(fields) == len(payload)
            assert timestamp == now // resolution * resolution * 1e9

    def test_payload_tag(self):
        for payload in (
                {'a': 'a'},
                {'a': 'a', 'b': 'b'},
                {str(i): i for i in range(20)},
        ):
            logger, handler = make_test_logger(__name__)
            handler.formatter = LineProtocolFormatter({'a'})
            logger.critical('message', payload)
            name, tags, fields, timestamp = parse_line_protocol(handler.content)
            assert timestamp is None
            if 'a' in payload:
                assert len(fields) == len(payload) - 1
                assert tags == {'a': 'a'}
                assert fields == {key: value for key, value in payload.items() if key != 'a'}
            else:
                assert len(fields) == len(payload)
                assert fields == payload

    def test_payload_empty(self):
        logger, handler = make_test_logger(__name__)
        handler.formatter = LineProtocolFormatter()
        logger.critical('message', {})
        name, tags, fields, timestamp = parse_line_protocol(handler.content)
        assert len(fields) == 0
        assert fields == {}
        assert len(tags) == 0
        assert tags == {}
        assert timestamp is None
