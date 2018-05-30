import asyncio
import sys
import logging
import platform

from .logger import initialise_logging
from .config.yaml import load_configuration
from .cli import CLI
from .. import __about__
from ..utility import schedule_pipelines


def core(configuration: str, level: str, target: str, short_format: bool):
    initialise_logging(level=level, target=target, short_format=short_format)
    logger = logging.getLogger(__package__)
    logger.info('COBalD %s', __about__.__version__)
    logger.info(__about__.__url__)
    logger.info('%s %s (%s)', platform.python_implementation(), platform.python_version(), sys.executable)
    event_loop = asyncio.get_event_loop()
    pipeline = load_configuration(configuration)
    schedule_pipelines(event_loop, pipeline[-1])
    logger.info('Running main event loop...')
    event_loop.run_forever()


def main():
    options = CLI.parse_args()
    core(options.CONFIGURATION, options.log_level, options.log_target, options.log_journal)
