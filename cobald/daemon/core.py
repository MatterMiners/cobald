"""
Daemon core specific to cobald
"""
import os
import sys
import logging
import platform

import cobald

from .logger import initialise_logging
from .config.mapping import Translator
from .config.yaml import load_configuration as load_yaml_configuration
from .config.python import load_configuration as load_python_configuration
from .cli import CLI
from . import runtime
from .. import __about__


class PipelineTranslator(Translator):
    def translate_hierarchy(self, structure, *, where='', **construct_kwargs):
        try:
            pipeline = structure['pipeline']
        except (KeyError, TypeError):
            return super().translate_hierarchy(structure, where=where, **construct_kwargs)
        else:
            prev_item, items = None, []
            for index, item in reversed(list(enumerate(pipeline))):
                if prev_item is not None:
                    prev_item = self.translate_hierarchy(item, where='%s[%s]' % (where, index), target=prev_item)
                else:
                    prev_item = self.translate_hierarchy(item)
                items.append(prev_item)
            return list(reversed(items))


def core(configuration: str, level: str, target: str, short_format: bool):
    initialise_logging(level=level, target=target, short_format=short_format)
    logger = logging.getLogger(__package__)
    logger.info('COBalD %s', __about__.__version__)
    logger.info(__about__.__url__)
    logger.info('%s %s (%s)', platform.python_implementation(), platform.python_version(), sys.executable)
    logger.debug(cobald.__file__)
    if os.path.splitext(configuration)[1] == '.yaml':
        handle = load_yaml_configuration(configuration, translator=PipelineTranslator())
    elif os.path.splitext(configuration)[1] == '.py':
        handle = load_python_configuration(configuration)
    else:
        raise ValueError('Unknown configuration extension: %r' % os.path.splitext(configuration)[1])
    logger.info('Running main event loop...')
    runtime.accept()
    del handle


def main():
    options = CLI.parse_args()
    core(options.CONFIGURATION, options.log_level, options.log_target, options.log_journal)
