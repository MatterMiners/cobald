from yaml import load

from .mapping import configure_logging, Translator, FieldError


def load_configuration(path, translator=Translator()):
    with open(path) as yaml_stream:
        config_data = load(yaml_stream)
    try:
        logging_mapping = config_data['logging']
    except KeyError:
        pass
    else:
        configure_logging(logging_mapping)
    try:
        root_pipeline = config_data['pipeline']
    except KeyError:
        raise FieldError('pipeline', 'configuration root')
    else:
        return translator.translate_hierarchy({'pipeline': root_pipeline})
