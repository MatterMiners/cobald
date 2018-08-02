from yaml import load

from .mapping import configure_logging, Translator, ConfigurationError


def load_configuration(path, translator=Translator()):
    with open(path) as yaml_stream:
        config_data = load(yaml_stream)
    try:
        logging_mapping = config_data.pop('logging')
    except KeyError:
        pass
    else:
        configure_logging(logging_mapping)
    try:
        root_pipeline = config_data.pop('pipeline')
    except KeyError as err:
        raise ConfigurationError(where='root', what=err)
    else:
        if config_data:
            raise ConfigurationError(where='root', what='dangling configuration keys (%s)' % ', '.join(config_data))
        return translator.translate_hierarchy({'pipeline': root_pipeline})
