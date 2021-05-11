import os
from contextlib import contextmanager
from typing import Type, Tuple, Dict, Set

from yaml import SafeLoader, BaseLoader
from entrypoints import get_group_all as get_entrypoints
from toposort import toposort_flatten

from ..plugins import constraints as plugin_constraints
from ..config.yaml import (
    load_configuration as load_yaml_configuration,
    yaml_constructor,
)
from ..config.python import load_configuration as load_python_configuration
from ..config.mapping import Translator, SectionPlugin
from ...interfaces._partial import Partial


class COBalDLoader(SafeLoader):
    """Loader with access to COBalD configuration constructors"""


def add_constructor_plugins(entry_point_group: str, loader: Type[BaseLoader]) -> None:
    """
    Add PyYAML constructors from an entry point group to a loader

    :param loader: the PyYAML loader which uses the plugins
    :param entry_point_group: entry point group to search

    .. note::

        This directly modifies the ``loader`` by
        calling :py:meth:`~.BaseLoader.add_constructor`.
    """
    for entry in get_entrypoints(entry_point_group):
        if entry.name[0] == "!":
            raise RuntimeError(
                "plugin name %r in entry point group %r may not start with '!'"
                % (entry.name, entry_point_group)
            )
        try:
            pipeline_factory = entry.load().s
        except AttributeError:
            pipeline_factory = entry.load()
        loader.add_constructor(
            tag="!" + entry.name, constructor=yaml_constructor(pipeline_factory)
        )


def load_section_plugins(entry_point_group: str) -> Tuple[SectionPlugin]:
    """
    Load configuration plugins from an entry point group

    :param entry_point_group: entry point group to search
    :return: all loaded plugins
    """
    plugins: Dict[str, SectionPlugin] = {
        plugin.section: plugin
        for plugin in map(SectionPlugin.load, get_entrypoints(entry_point_group))
    }
    dependencies: Dict[str, Set[str]] = {
        plugin.section: set(plugin.after) for plugin in plugins.values()
    }
    for plugin in plugins.values():
        for before in plugin.before:
            dependencies[before].add(plugin.section)
    return tuple(
        plugins[plugin_name]
        for plugin_name in toposort_flatten(dependencies, sort=False)
        if plugin_name in plugins
    )


@contextmanager
def load(config_path: str):
    """
    Load a configuration and keep it alive for the given context

    :param config_path: path to a configuration file
    """
    # we bind the config to c to keep it alive
    if os.path.splitext(config_path)[1] in (".yaml", ".yml"):
        add_constructor_plugins(
            "cobald.config.yaml_constructors", COBalDLoader  # type: ignore
        )
        config_plugins = load_section_plugins("cobald.config.sections")
        c = load_yaml_configuration(
            config_path,
            loader=COBalDLoader,  # type: ignore
            plugins=config_plugins,
        )
    elif os.path.splitext(config_path)[1] == ".py":
        c = load_python_configuration(config_path)
    else:
        raise ValueError(
            "Unknown configuration extension: %r" % os.path.splitext(config_path)[1]
        )
    # yielded value used in tests, runtime does not use configuration result
    yield c


@plugin_constraints(required=True)
def load_pipeline(content: list):
    """
    Load a cobald pipeline of Controller >> ... >> Pool from a configuration section

    :param content: content of the configuration section
    :return:
    """
    translator = PipelineTranslator()
    return translator.translate_hierarchy({"pipeline": content})


class PipelineTranslator(Translator):
    """
    Translator for :py:mod:`cobald` pipelines

    This allows for YAML configurations to have one or several ``pipeline`` elements.
    Each ``pipeline``  is translated as a series of nested elements, the way a
    :py:class:`~cobald.interfaces.Controller` receives a
    :py:class:`~cobald.interfaces.Pool`.

    .. code:: yaml

        pipeline:
            # same as ``package.module.callable(a, b, keyword1="one", keyword2="two")
            - __type__: package.module.Controller
              interval: 20
            - __type__: package.module.Pool
    """

    def translate_hierarchy(self, structure, *, where="", **construct_kwargs):
        try:
            pipeline = structure["pipeline"]
        except (KeyError, TypeError):
            return super().translate_hierarchy(
                structure, where=where, **construct_kwargs
            )
        else:
            prev_item, items = None, []
            for index, item in reversed(list(enumerate(pipeline))):
                if prev_item is not None:
                    if hasattr(item, "__rshift__"):
                        # fully constructed object from !constructor
                        prev_item = item >> prev_item
                    else:
                        # encoded object from __type__: constructor
                        prev_item = self.translate_hierarchy(
                            item, where="%s[%s]" % (where, index), target=prev_item
                        )
                else:
                    prev_item = self.translate_hierarchy(
                        item, where="%s[%s]" % (where, index)
                    )
                    if isinstance(prev_item, Partial):  # got form __type__
                        prev_item = prev_item.__construct__()
                assert not isinstance(prev_item, Partial)
                items.append(prev_item)
            return list(reversed(items))
