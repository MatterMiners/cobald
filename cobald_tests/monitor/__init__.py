import threading
import logging
import io


class CapturingHandler(logging.StreamHandler):
    @property
    def content(self) -> str:
        return self.stream.getvalue()

    def __init__(self):
        super().__init__(stream=io.StringIO())

    def clear(self):
        self.stream.truncate(0)
        self.stream.seek(0)


_test_index = 0
_index_lock = threading.Lock()


class ExtraLogger(logging.Logger):
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
        """Replacement for Logger.makeRecord to overwrite fields via ``extra``"""
        try:
            created = extra and extra.pop('created')
        except KeyError:
            created = None
        rv = super().makeRecord(name, level, fn, lno, msg, args, exc_info, func, None, sinfo)
        if extra is not None:
            for key in extra:
                rv.__dict__[key] = extra[key]
        if created:
            rv.created = created
            rv.msecs = (created - int(created)) * 1000
            rv.relativeCreated = (created - logging._startTime) * 1000
        return rv


def make_test_logger(base_name: str = 'test_logger'):
    with _index_lock:
        global _test_index
        log_name = base_name + '.test%d' % _test_index
        _test_index += 1
    logger = logging.getLogger(log_name)
    logger.propagate = False
    logger.__class__ = ExtraLogger
    handler = CapturingHandler()
    logger.handlers = [handler]
    return logger, handler
