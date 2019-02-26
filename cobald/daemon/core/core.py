"""
Daemon core specific to cobald
"""
import sys
import logging
import platform

import cobald

from .logger import initialise_logging
from .cli import CLI
from .config import load
from .. import runtime


def core(configuration: str, level: str, target: str, short_format: bool):
    initialise_logging(level=level, target=target, short_format=short_format)
    logger = logging.getLogger(__package__)
    logger.info('COBalD %s', cobald.__about__.__version__)
    logger.info(cobald.__about__.__url__)
    logger.info('%s %s (%s)', platform.python_implementation(), platform.python_version(), sys.executable)
    logger.debug(cobald.__file__)
    logger.info('Using configuration', configuration)
    with load(configuration):
        logger.info('Starting daemon services...')
        runtime.accept()


def main():
    options = CLI.parse_args()
    core(options.CONFIGURATION, options.log_level, options.log_target, options.log_journal)
