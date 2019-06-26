import logging
import logging.config
import sys

from typing import Any

_logger = logging.getLogger(__package__)


class ConfigurationError(Exception):
    def __init__(self, what: Any, where: str = None):
        self.where = where
        self.what = what
        super().__init__("invalid configuration element '%s': %s" % (where, what))


def configure_logging(logging_mapping):
    _logger.info('Configuring logging')
    # > takes a default parameter, disable_existing_loggers, which defaults to True
    # > for reasons of backward compatibility. This may or may not be what you want
    # Note: this is *not* what we want, since we create several loggers in advance
    logging_mapping['disable_existing_loggers'] = logging_mapping.get(
        'disable_existing_loggers', False
    )
    logging.config.dictConfig(logging_mapping)


class Translator(object):
    """
    Translator from a mapping to an initialised object hierarchy
    """
    def translate_hierarchy(self, structure, *, where='', **construct_kwargs):
        try:
            if isinstance(structure, dict):
                structure = {
                    key: self.translate_hierarchy(value, where='%s.%s' % (where, key))
                    for key, value in structure.items()
                }
                if '__type__' in structure:
                    return self.construct(structure, **construct_kwargs)
                return structure
            elif isinstance(structure, list):
                # translate bottom up - need those lists to materialize
                # reversed and enumerate iterables
                return list(reversed([
                    self.translate_hierarchy(item, where='%s[%s]' % (where, index))
                    for index, item in reversed(list(enumerate(structure)))
                ]))
            else:
                return structure
        except ConfigurationError as err:
            if err.where is None:
                raise ConfigurationError(what=err.what, where=where)
            raise
        except Exception as err:
            raise ConfigurationError(where=where, what=err)

    def construct(self, mapping: dict, **kwargs):
        """
        Construct an object from a mapping

        :param mapping: constructor definition, with ``__type__`` and keyword arguments
        :param kwargs: additional keyword arguments to pass to the constructor
        """
        assert '__type__' not in kwargs and '__args__' not in kwargs
        mapping = {**mapping, **kwargs}
        factory_fqdn = mapping.pop('__type__')
        factory = self.load_name(factory_fqdn)
        args = mapping.pop('__args__', [])
        return factory(*args, **mapping)

    @staticmethod
    def load_name(absolute_name: str):
        """Load an object based on an absolute, dotted name"""
        path = absolute_name.split('.')
        try:
            __import__(absolute_name)
        except ImportError:
            try:
                obj = sys.modules[path[0]]
            except KeyError:
                raise ImportError('No module named %r' % path[0])
            else:
                for component in path[1:]:
                    try:
                        obj = getattr(obj, component)
                    except AttributeError as err:
                        raise ConfigurationError(
                            what='no such object %r: %s' % (absolute_name, err)
                        )
                return obj
        else:  # ImportError is not raised if ``absolute_name`` points to a valid module
            return sys.modules[absolute_name]
