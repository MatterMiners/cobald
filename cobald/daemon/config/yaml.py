from yaml import load

from .mapping import configure_logging, create_pipeline, FieldError


def load_configuration(path):
    with open(path) as yaml_stream:
        config_data = load(yaml_stream)
    try:
        logging_mapping = config_data['logging']
    except KeyError:
        pass
    else:
        configure_logging(logging_mapping)
    try:
        pipeline_elements = config_data['pipeline']
    except KeyError:
        raise FieldError('pipeline', 'configuration root')
    else:
        return create_pipeline(pipeline_elements)
