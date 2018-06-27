from collections.abc import Mapping
from logging import Formatter, LogRecord
import json


#: Attributes of a LogRecord. See <the docs `https://docs.python.org/3/library/logging.html#logrecord-attributes`>_.
RECORD_ATTRIBUTES = (
    'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename', 'funcName',
    'levelname', 'levelno', 'lineno', 'message', 'module', 'msecs',
    'msg', 'name', 'pathname', 'process', 'processName', 'relativeCreated',
    'stack_info', 'thread', 'threadName',
)


class JsonFormatter(Formatter):
    """
    Formatter that emits data as JSON

    :param fmt: default data for all records
    :param datefmt: format for timestamps
    :param record_attributes: standard record attributes to include in output

    The ``datefmt`` parameter has the same meaning as for :py:class:`~.Formatter`.
    Note that if ``record_attributes`` does not whitelist ``"asctime"`` field,
    the result is not included in the log output.

    The ``record_attributes`` acts as a whitelist for the standard record attributes to include in the output.
    See :py:attr:`~.RECORD_ATTRIBUTES` for a list of available attributes.
    If ``record_attributes`` is a mapping, attributes are renamed according to it.
    For example, ``record_attributes = {'message': 'identifier', 'asctime': 'timestamp'}`` whitelists the fields
    ``'message'`` and ``asctime`` but renames them to ``'identifier'``  and ``'timestamp'``.
    """
    def __init__(self, fmt: dict = None, datefmt: str = None, record_attributes=('message',)):
        super().__init__(fmt=None, datefmt=datefmt, style='%')
        self._defaults = fmt or {}
        if not isinstance(self._defaults, Mapping):
            raise TypeError('`fmt` must be a Mapping or None')
        self._ignore_attributes = {name for name in RECORD_ATTRIBUTES if name not in record_attributes}
        try:
            self._remap_attributes = {**record_attributes}
        except TypeError:
            self._remap_attributes = {}

    def _as_dict(self, record):
        """Transform a populated ``record`` to a :py:class:`dict`"""
        data = {**self._defaults}
        self__remap_attributes = self._remap_attributes
        self__ignore_attributes = self._ignore_attributes
        data.update({
            self__remap_attributes.get(name, name): value
            for name, value in record.__dict__.items()
            if name not in self__ignore_attributes
        })
        return data

    def format(self, record: LogRecord):
        record.asctime = self.formatTime(record, self.datefmt)
        record.message = record.getMessage()
        data = self._as_dict(record)
        return json.dumps(data)


if __name__ == '__main__':
    import logging
    logger = logging.getLogger()
    logger.handlers = [logging.StreamHandler()]
    logger.handlers[0].formatter = JsonFormatter({'latitude': 49, 'longitude': 8})
    logger.warning('forecast', extra={'temperature': 298, 'humidity': 0.45})
