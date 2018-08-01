import logging
import logging.config
import sys

_logger = logging.getLogger(__package__)


class ConfigurationError(Exception):
    pass


class FieldError(ConfigurationError, KeyError):
    """
    An expected field is missing from the configuration
    """
    def __init__(self, field: str, context: str):
        super().__init__('field %r missing at %s' % (field, context))
        self.field = field
        self.context = context


def configure_logging(logging_mapping):
    _logger.info('Configuring logging')
    logging.config.dictConfig(logging_mapping)


def create_pipeline(pipeline_elements):
    _logger.info('Configuring pipelines')
    pipeline = []
    previous_element = None
    for idx, element_data in enumerate(pipeline_elements):
        previous_element = _create_pipeline_element(
            element_data, context='pipeline element %d' % (idx + 1), target=previous_element
        )
        pipeline.append(previous_element)
    return pipeline


def _load_object(absolute_name: str):
    """Load an object based on an absolute, dotted name"""
    path = absolute_name.split('.')
    try:
        __import__(absolute_name)
    except ImportError:
        try:
            obj = sys.modules[path[0]]
        except KeyError:
            raise ModuleNotFoundError('No module named %r' % path[0])
        else:
            for component in path[1:]:
                try:
                    obj = getattr(obj, component)
                except AttributeError as err:
                    raise ConfigurationError('no such object %r: %s' % (absolute_name, err))
            return obj
    else:  # ImportError is not raised if ``absolute_name`` points to a valid module
        return sys.modules[absolute_name]


def _create_pipeline_element(element_mapping, context: str = 'pipeline element', target=None):
    try:
        factory_name = element_mapping.pop('type')
    except KeyError:
        raise FieldError('type', context)
    else:
        factory = _load_object(factory_name)
        if target is not None:
            return factory(target=target, **element_mapping)
        return factory(**element_mapping)


class Translator(object):
    def translate_hierarchy(self, structure, **construct_kwargs):
        if isinstance(structure, dict):
            structure = {key: self.translate_hierarchy(value) for key, value in structure.items()}
            if '__type__' in structure:
                return self.construct(structure, **construct_kwargs)
            return structure
        if isinstance(structure, list):
            prev_item, items = None, []
            for item in structure:
                if not isinstance(prev_item, (list, dict, str, int, float)):
                    prev_item = self.translate_hierarchy(item, target=prev_item)
                else:
                    prev_item = self.translate_hierarchy(item)
                items.append(prev_item)
            return items
        return structure

    @staticmethod
    def construct(mapping: dict, **kwargs):
        """
        Construct an object from a mapping

        :param mapping: the constructor definition, with ``__type__`` name and keyword arguments
        :param kwargs: additional keyword arguments to pass to the constructor
        """
        assert '__type__' not in kwargs and '__args__' not in kwargs
        mapping = {**mapping, **kwargs}
        factory_fqdn = mapping.pop('__type__')
        factory = _load_object(factory_fqdn)
        args = mapping.pop('__args__', [])
        return factory(*args, **mapping)
