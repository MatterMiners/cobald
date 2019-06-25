from collections.abc import Mapping
from logging import Formatter, LogRecord
from typing import Dict, Set, Union, Any

from .format_json import RECORD_ATTRIBUTES


def line_protocol(name, tags: dict = None, fields: dict = None, timestamp: float = None) -> str:
    """
    Format a report as per InfluxDB line protocol

    :param name: name of the report
    :param tags: tags identifying the specific report
    :param fields: measurements of the report
    :param timestamp: when the measurement was taken, in **seconds** since the epoch
    """
    output_str = name
    if tags:
        output_str += ','
        output_str += ','.join('%s=%s' % (key, value) for key, value in sorted(tags.items()))
    output_str += ' '
    output_str += ','.join(('%s=%r' % (key, value)).replace("'", '"') for key, value in sorted(fields.items()))
    if timestamp is not None:
        # line protocol requires nanosecond precision, python uses seconds
        output_str += ' %d' % (timestamp * 1E9)
    return output_str + '\n'


class LineProtocolFormatter(Formatter):
    """
    Formatter that emits data as InfluxDB Line Protocol

    :param tags: record data to use as tags
    :param resolution: resolution of timestamps in seconds

    The ``tags`` act as a whitelist for record keys if they are an iterable.
    When a dictionary is supplied, its values act as default values if the key is not in a record.
    """
    def __init__(self, tags: Union[Dict[str, Any], Set[str], None] = None, resolution: float = None):
        super().__init__()
        self._default_tags = tags if isinstance(tags, Mapping) else {}
        self._tags_whitelist = set(tags) if tags is not None else set()
        self._fields_blacklist = self._tags_whitelist | set(RECORD_ATTRIBUTES)
        self._resolution = resolution

    def format(self, record: LogRecord) -> str:
        args = record.args
        if args == ({},):  # logger.info('message', {}) -> record.args == ({},)
            args = {}
        assert isinstance(args, Mapping), 'monitor record argument must be a mapping, not %r' % type(args)
        record.asctime = self.formatTime(record, self.datefmt)
        record.message = record.getMessage() if args else record.msg
        tags = self._default_tags.copy()
        tags.update({key: value for key, value in args.items() if key in self._tags_whitelist})
        fields = {key: value for key, value in args.items() if key not in self._fields_blacklist}
        timestamp = record.created // self._resolution * self._resolution if self._resolution is not None else None
        return line_protocol(name=record.message, tags=tags, fields=fields, timestamp=timestamp)


if __name__ == '__main__':
    import logging
    logger = logging.getLogger()
    logger.handlers = [logging.StreamHandler()]
    logger.handlers[0].formatter = LineProtocolFormatter({'latitude': 49, 'longitude': 8})
    logger.warning('forecast', {'temperature': 298, 'humidity': 0.45})
