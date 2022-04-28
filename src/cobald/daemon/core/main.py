"""
Daemon core specific to cobald
"""
import asyncio
import sys
import logging
import platform

import cobald.__about__

from .logger import initialise_logging
from .cli import CLI
from .config import load
from .. import runtime


def run(configuration: str, level: str, target: str, short_format: bool):
    """Run the daemon and all its services"""
    initialise_logging(level=level, target=target, short_format=short_format)
    logger = logging.getLogger(__package__)
    logger.info("COBalD %s", cobald.__about__.__version__)
    logger.info(cobald.__about__.__url__)
    logger.info(
        "%s %s (%s)",
        platform.python_implementation(),
        platform.python_version(),
        sys.executable,
    )
    logger.debug(cobald.__about__.__file__)
    logger.info("Using configuration %s", configuration)
    logger.info("Starting daemon services...")
    runtime.adopt(_load_services, configuration, flavour=asyncio)
    runtime.accept()


async def _load_services(path: str):
    """
    Helper to load configured tasks once the runtime is ready and to hold objects alive
    """
    with load(path):
        # sleep indefinitely to wait until the runtime is aborted
        await asyncio.sleep(float("inf"))


def cli_run():
    """Run the daemon from a command line interface"""
    options = CLI.parse_args()
    run(
        configuration=options.CONFIGURATION,
        level=options.log_level,
        target=options.log_target,
        short_format=options.log_journal,
    )
