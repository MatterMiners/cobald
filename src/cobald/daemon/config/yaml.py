from typing import Type, Tuple

from yaml import SafeLoader, BaseLoader, nodes

from .mapping import (
    load_configuration as load_mapping_configuration,
    ConfigurationError,
    SectionPlugin,
)


def load_configuration(
    path: str, loader: Type[BaseLoader] = SafeLoader, plugins: Tuple[SectionPlugin] = ()
):
    with open(path) as yaml_stream:
        loader_instance = loader(yaml_stream)
        try:
            config_data = loader_instance.get_single_data()
        finally:
            loader_instance.dispose()
    return load_mapping_configuration(config_data=config_data, plugins=plugins)


def yaml_constructor(factory):
    """
    Convert a factory function/class to a YAML constructor

    :param factory: the factory function/class
    :return: factory constructor

    Applying this helper to a factory allows it to be used as a YAML constructor,
    without it knowing about YAML itself.
    It properly constructs nodes and converts
    mapping nodes to ``factory(**node)``,
    sequence nodes to ``factory(*node)``, and
    scalar nodes to ``factory()``.

    For example, registering the constructor ``yaml_constructor(factory)`` as
    ``!factory`` means the following YAML is converted to ``factory(a=0.3, b=0.7)``:

    .. code::

        - !factory
          a: 0.3
          b: 0.7
    """

    def factory_constructor(loader: BaseLoader, node: nodes.Node):
        if isinstance(node, nodes.MappingNode):
            kwargs = loader.construct_mapping(node)
            return factory(**kwargs)
        elif isinstance(node, nodes.ScalarNode):
            return factory()
        elif isinstance(node, nodes.SequenceNode):
            args = loader.construct_sequence(node)
            return factory(*args)
        else:
            raise ConfigurationError(
                "YAML constructor %r on unsupported node type %s"
                % (node.tag, type(node).__name__)
            )

    return factory_constructor
