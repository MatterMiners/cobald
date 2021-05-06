import logging
import logging.config
import sys
from typing import Any, Dict, TypeVar, Callable, Tuple, Generic

from entrypoints import EntryPoint

from ..plugins import PluginRequirements

_logger = logging.getLogger(__package__)


T = TypeVar("T")
#: type of a mapping element, matching JSON/YAML
M = TypeVar("M", str, int, float, bool, dict, list)


class ConfigurationError(Exception):
    def __init__(self, what: Any, where: str = None):
        self.where = where
        self.what = what
        super().__init__("invalid configuration element '%s': %s" % (where, what))


def configure_logging(logging_mapping: dict):
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
        self, structure: M, *, where: str = "", **construct_kwargs
    ) -> M:
        try:
            if isinstance(structure, dict):
                structure = {
                    key: self.translate_hierarchy(value, where="%s.%s" % (where, key))
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
                            self.translate_hierarchy(
                                item, where="%s[%s]" % (where, index)
                            )
                            for index, item in reversed(list(enumerate(structure)))
                        ]
                    )
                )
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
        assert "__type__" not in kwargs and "__args__" not in kwargs
        mapping = {**mapping, **kwargs}
        factory_fqdn = mapping.pop("__type__")
        factory = self.load_name(factory_fqdn)
        args = mapping.pop("__args__", [])
        return factory(*args, **mapping)

    @staticmethod
    def load_name(absolute_name: str):
        """Load an object based on an absolute, dotted name"""
        path = absolute_name.split(".")
        try:
            __import__(absolute_name)
        except ImportError:
            try:
                obj = sys.modules[path[0]]
            except KeyError:
                raise ImportError("No module named %r" % path[0])
            else:
                for component in path[1:]:
                    try:
                        obj = getattr(obj, component)
                    except AttributeError as err:
                        raise ConfigurationError(
                            what="no such object %r: %s" % (absolute_name, err)
                        )
                return obj
        else:  # ImportError is not raised if ``absolute_name`` points to a valid module
            return sys.modules[absolute_name]


class SectionPlugin(Generic[M]):
    """
    Plugin to digest a top-level configuration section

    :param section: Name of the section to digest
    :param digest: callable that receives the section
    :param requirements: plugin requirements
    """

    __slots__ = "section", "digest", "requirements"

    @property
    def required(self):
        return self.requirements.required

    @property
    def before(self):
        return self.requirements.before

    @property
    def after(self):
        return self.requirements.after

    def __init__(
        self, section: str, digest: Callable[[M], Any], requirements: PluginRequirements
    ):
        self.section = section
        self.digest = digest
        self.requirements = requirements

    @classmethod
    def load(cls, entry_point: EntryPoint) -> "SectionPlugin":
        """
        Load a plugin from a pre-parsed entry point

        The entry point name is used as the configuration ``section`` to digest
        by the entry point target. Additional metadata may be provided by decorating
        the target implementation with :py:func:`cobald.daemon.plugins.constraints`.
        """
        digest = entry_point.load()
        requirements = getattr(digest, "__requirements__", PluginRequirements())
        if entry_point.extras:
            raise ValueError(
                f"SectionPlugin entry point '{entry_point.name}':"
                f" extras are no longer supported"
            )
        return cls(section=entry_point.name, digest=digest, requirements=requirements)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}"
            f"(section={self.section},"
            f" digest={self.digest},"
            f" requirements={self.requirements})"
        )


def load_configuration(
    config_data: Dict[str, Any], plugins: Tuple[SectionPlugin] = ()
) -> Dict[SectionPlugin, Any]:
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
    unmatched = config_data.keys() - {plugin.section for plugin in plugins}
    if unmatched:
        raise ConfigurationError(
            where="root", what="unknown config sections %s" % ", ".join(unmatched)
        )
    content = {}
    for plugin in plugins:
        try:
            section_data = config_data[plugin.section]
        except KeyError:
            if plugin.required:
                raise ConfigurationError(
                    where="root", what="missing section %r" % plugin.section
                )
        else:
            if plugin.requirements.schema is not None:
                section_data = plugin.requirements.schema(section_data)
            # invoke the plugin and store possible output
            # to avoid it being garbage collected
            plugin_content = plugin.digest(section_data)
            if plugin_content is not None:
                content[plugin] = plugin_content
    return content
