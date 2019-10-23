from collections.abc import Mapping
from logging import Formatter, LogRecord
from typing import Dict, Set, Union, Any, TypeVar

from .format_json import RECORD_ATTRIBUTES


T = TypeVar("T")


def escape_key(key: str) -> str:
    assert isinstance(key, str)
    return key.replace(r",", r"\,").replace(r"=", r"\=").replace(r" ", r"\ ")


def escape_field(field: T) -> T:
    if isinstance(field, str):
        return '"' + field.replace("\\", r"\\").replace('"', r"\"") + '"'
    return field


def line_protocol(
    name, tags: dict = None, fields: dict = None, timestamp: float = None
) -> str:
    """
    Format a report as per InfluxDB line protocol

    :param name: name of the report
    :param tags: tags identifying the specific report
    :param fields: measurements of the report
    :param timestamp: when the measurement was taken, in **seconds** since the epoch
    """
    _escape_key = escape_key
    _escape_field = escape_field
    output_str = name.replace(r",", r"\,").replace(r" ", r"\ ")
    if tags:
        output_str += ","
        output_str += ",".join(
            "%s=%s" % (_escape_key(key), _escape_key(value))
            for key, value in sorted(tags.items())
        )
    output_str += " "
    output_str += ",".join(
        ("%s=%s" % (_escape_key(key), _escape_field(value))).replace("'", '"')
        for key, value in sorted(fields.items())
    )
    if timestamp is not None:
        # line protocol requires nanosecond precision, python uses seconds
        output_str += " %d" % (timestamp * 1e9)
    return output_str + "\n"


class LineProtocolFormatter(Formatter):
    """
    Formatter that emits data as InfluxDB Line Protocol

    :param tags: record data to use as tags
    :param resolution: resolution of timestamps in seconds

    The ``tags`` act as a whitelist for record keys if they are an iterable.
    When a dictionary is supplied, its values act as default values if the
    key is not in a record.

    The ``resolution`` allows summarising data by downsampling the timestamps
    to the given resolution, e.g. for a ``resolution`` of ``10`` you can expect
    timestamps 10, 20, 30, ...
    If ``resolution`` is ``None`` the timestamp is omitted from the Line Protocol
    and Telegraf will take care on setting the current timestamp.
    """

    def __init__(
        self,
        tags: Union[Dict[str, Any], Set[str], None] = None,
        resolution: float = None,
    ):
        super().__init__()
        self._default_tags = tags if isinstance(tags, Mapping) else {}
        self._tags_whitelist = set(tags) if tags is not None else set()
        self._fields_blacklist = self._tags_whitelist | set(RECORD_ATTRIBUTES)
        self._resolution = resolution

    def format(self, record: LogRecord) -> str:
        args = record.args
        if args == ({},):  # logger.info('message', {}) -> record.args == ({},)
            args = {}
        assert isinstance(
            args, Mapping
        ), "monitor record argument must be a mapping, not %r" % type(args)
        assert all(
            elem is not None for elem in args.values()
        ), "line protocol values must not be None"
        record.asctime = self.formatTime(record, self.datefmt)
        record.message = record.getMessage() if args else record.msg
        tags = self._default_tags.copy()
        tags.update(
            {key: value for key, value in args.items() if key in self._tags_whitelist}
        )
        fields = {
            key: value
            for key, value in args.items()
            if key not in self._fields_blacklist
        }
        timestamp = (
            record.created // self._resolution * self._resolution
            if self._resolution is not None
            else None
        )
        return line_protocol(
            name=record.message, tags=tags, fields=fields, timestamp=timestamp
        )


if __name__ == "__main__":
    import logging

    logger = logging.getLogger()
    logger.handlers = [logging.StreamHandler()]
    logger.handlers[0].formatter = LineProtocolFormatter(
        {"latitude": 49, "longitude": 8}
    )
    logger.warning("forecast", {"temperature": 298, "humidity": 0.45})
