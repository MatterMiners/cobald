from collections.abc import Mapping
from logging import Formatter, LogRecord
import json


#: Attributes of a LogRecord.
# See <the docs `https://docs.python.org/3/library/logging.html#logrecord-attributes`>_.
RECORD_ATTRIBUTES = (
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "message",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
)


class JsonFormatter(Formatter):
    """
    Formatter that emits data as JSON

    :param fmt: default data for all records
    :param datefmt: format for timestamps

    The ``datefmt`` parameter has almost the same meaning as
    :py:class:`~.Formatter`.
    Setting it to ``None`` uses the default time format.
    However, setting it to any other value that is boolean
    false excludes the timestamp from reports.
    """

    def __init__(self, fmt: dict = None, datefmt: str = None):
        super().__init__(fmt=None, datefmt=datefmt, style="%")
        self._defaults = fmt or {}
        if not isinstance(self._defaults, Mapping):
            raise TypeError("`fmt` must be a Mapping or None")
        self._add_time = self.datefmt or self.datefmt is None

    def format(self, record: LogRecord):
        args = record.args
        if args == ({},):  # logger.info('message', {}) -> record.args == ({},)
            args = {}
        assert isinstance(
            args, Mapping
        ), "monitor record argument must be a mapping, not %r" % type(args)
        data = self._defaults.copy()
        if self._add_time:
            data["time"] = self.formatTime(record, self.datefmt)
        data["message"] = record.getMessage() if args else record.msg
        data.update(args)
        return json.dumps(data)


if __name__ == "__main__":
    import logging

    logger = logging.getLogger()
    logger.handlers = [logging.StreamHandler()]
    logger.handlers[0].formatter = JsonFormatter({"latitude": 49, "longitude": 8})
    logger.warning("forecast", {"temperature": 298, "humidity": 0.45})
