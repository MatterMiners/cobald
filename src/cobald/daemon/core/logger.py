import sys
import logging
import logging.handlers


def create_handler(target: str):
    """Create a handler for logging to ``target``"""
    if target == "stderr":
        return logging.StreamHandler(sys.stderr)
    elif target == "stdout":
        return logging.StreamHandler(sys.stdout)
    else:
        return logging.handlers.WatchedFileHandler(filename=target)


def initialise_logging(level: str, target: str, short_format: bool):
    """Initialise basic logging facilities"""
    try:
        log_level = getattr(logging, level)
    except AttributeError:
        raise SystemExit(
            "invalid log level %r, expected any of 'DEBUG',"
            "'INFO', 'WARNING', 'ERROR' or 'CRITICAL'" % level
        ) from None
    handler = create_handler(target=target)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)-15s (%(process)d) %(message)s"
        if not short_format
        else "%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[handler],
    )
