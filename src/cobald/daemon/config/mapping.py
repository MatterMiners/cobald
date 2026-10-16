"""
Load a configuration from a mapping-like data format matching JSON and YAML
"""

from typing import Any, Callable, NamedTuple, TypeAlias
import logging
import logging.config
import sys

from entrypoints import EntryPoint

from ..plugins import PluginRequirements, _PLUGIN_REQUIREMENTS

_logger = logging.getLogger(__package__)

#: type of a mapping element, matching JSON/YAML
Node: TypeAlias = "str | int | float | dict[str, Node] | list[Node]"


class ConfigurationError(Exception):
    def __init__(self, what: Any, where: "str | None" = None):
        super().__init__(what, where)
        self.what = what
        self.where = where

    def __str__(self) -> str:
        where = f" {self.where!r}" if self.where is not None else ""
        return f"invalid configuration element{where}: {self.what}"


def configure_logging(logging_mapping: "dict[str, Any]"):
    _logger.info("Configuring logging")
    # > takes a default parameter, disable_existing_loggers, which defaults to True
    # > for reasons of backward compatibility. This may or may not be what you want
    # Note: this is *not* what we want, since we create several loggers in advance
    logging_mapping["disable_existing_loggers"] = logging_mapping.get(
        "disable_existing_loggers", False
    )
    logging.config.dictConfig(logging_mapping)


class Translator(object):
    """
    Translator from a mapping to an initialised object hierarchy
    """

    def translate_hierarchy(
        self, structure: Node, *, where: str = "", **construct_kwargs: Any
    ) -> Node:
        try:
            if isinstance(structure, dict):
                structure = {
                    key: self.translate_hierarchy(value, where=f"{where}.{key}")
                    for key, value in structure.items()
                }
                if "__type__" in structure:
                    return self.construct(structure, **construct_kwargs)
                return structure
            elif isinstance(structure, list):
                # translate bottom up - need those lists to materialize
                # reversed and enumerate iterables
                return list(
                    reversed(
                        [
                            self.translate_hierarchy(item, where=f"{where}[{index}]")
                            for index, item in reversed(list(enumerate(structure)))
                        ]
                    )
                )
            else:
                return structure
        except ConfigurationError as err:
            if err.where is None:
                raise ConfigurationError(what=err.what, where=where) from err
            raise
        except Exception as err:
            raise ConfigurationError(where=where, what=err) from err

    def construct(self, mapping: dict[str, Any], **kwargs: Any) -> Any:
        """
        Construct an object from a mapping

        :param mapping: definition with ``__type__`` and optional ``__args__``
        :param kwargs: additional keyword arguments to pass to the constructor
        """
        assert "__type__" not in kwargs and "__args__" not in kwargs
        mapping = {**mapping, **kwargs}
        factory_fqdn = mapping.pop("__type__")
        factory = self.load_name(factory_fqdn)
        args = mapping.pop("__args__", [])
        return factory(*args, **mapping)

    @staticmethod
    def load_name(absolute_name: str) -> Any:
        """Load an object based on an absolute, dotted name"""
        # __import__ loads everything, but does not fetch the element
        try:
            __import__(absolute_name)
        except ImportError:
            path = absolute_name.split(".")
            try:
                obj = sys.modules[path[0]]
            except KeyError:
                raise ImportError(f"No module named {path[0]!r}") from None
            else:
                for component in path[1:]:
                    try:
                        obj = getattr(obj, component)
                    except AttributeError as err:
                        raise ConfigurationError(
                            what=f"no such object {absolute_name!r}"
                        ) from err
                return obj
        else:  # ImportError is not raised if ``absolute_name`` points to a valid module
            return sys.modules[absolute_name]


class SectionPlugin(NamedTuple):
    """
    Plugin to digest a top-level configuration section

    :param section: Name of the section to digest
    :param digest: callable that receives the section
    :param requirements: plugin requirements
    """

    section: str
    digest: Callable[[Node], Any]
    requirements: PluginRequirements

    @classmethod
    def load(cls, entry_point: EntryPoint) -> "SectionPlugin":
        """Load a plugin from a pre-parsed entry point"""
        digest = entry_point.load()
        requirements = _PLUGIN_REQUIREMENTS[digest]
        assert not entry_point.extras, "SectionPlugin entry point extras not supported"
        return cls(section=entry_point.name, digest=digest, requirements=requirements)


def load_configuration(
    config_data: dict[str, Any], plugins: tuple[SectionPlugin, ...] = ()
) -> dict[SectionPlugin, Any]:
    """
    Load the configuration from a mapping, applying plugins to sections

    :param config_data: the raw configuration without any plugins applied
    :param plugins: all plugins that *might* apply, in order
    :return: the output of all applied plugins
    """
    try:
        logging_mapping = config_data.pop("logging")
    except KeyError:
        pass
    else:
        configure_logging(logging_mapping)
    # see if there is any unexpected config content
    if unmatched := config_data.keys() - {plugin.section for plugin in plugins}:
        raise ConfigurationError(
            where="root", what=f"unknown config sections {', '.join(unmatched)}"
        )
    content: dict[SectionPlugin, Any] = {}
    for plugin in plugins:
        try:
            section_data = config_data[plugin.section]
        except KeyError:
            if plugin.requirements.required:
                raise ConfigurationError(
                    where="root", what="missing section {plugin.section!r}"
                ) from None
        else:
            # invoke the plugin and store possible output
            # to avoid it being garbage collected
            plugin_content = plugin.digest(section_data)
            if plugin_content is not None:
                content[plugin] = plugin_content
    return content
