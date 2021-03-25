"""
The configuration machinery to load and apply the configuration based on plugins

Configuration is geared towards digesting structured mappings/YAML,
with plugins for digesting either entire sections or individual nodes.

* *Constructor Plugins* are callables that receive part of a YAML during loading.
* *Section Plugins* are callables that receive a top-level section of the
  configuration after loading.

The plugins are loaded from Python
`entry points <https://packaging.python.org/specifications/entry-points/>`_
which point at callables inside normal Python packages
(the section ``"logging"`` being the only exception).
The machinery is implemented by :py:func:`~.load`,
which in turn uses helpers to load plugins of each type.

The core part of cobald's functionality, a controller >> pool pipeline,
is itself a section plugin as :py:func:`~.load_pipeline`.
"""
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


class COBalDLoader(SafeLoader):
    """YAML loader with access to COBalD configuration constructors"""


# Loading of plugins from entry_points
def add_constructor_plugins(entry_point_group: str, loader: Type[BaseLoader]) -> None:
    """
    Add PyYAML constructors from an entry point group to a loader

    :param loader: the PyYAML loader which uses the plugins
    :param entry_point_group: name of entry point group to search

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
    Load configuration section plugins from an entry point group

    :param entry_point_group: name of entry point group to search
    :return: all loaded plugins sorted by before/after dependencies
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


# The high-level config machinery implementation itself
@contextmanager
def load(config_path: str):
    """
    Load a configuration and keep it alive for the given context

    :param config_path: path to a configuration file
    """
    # we bind the config to _ to keep it alive
    if os.path.splitext(config_path)[1] in (".yaml", ".yml"):
        add_constructor_plugins(
            "cobald.config.yaml_constructors", COBalDLoader  # type: ignore
        )
        config_plugins = load_section_plugins("cobald.config.sections")
        _ = load_yaml_configuration(
            config_path,
            loader=COBalDLoader,  # type: ignore
            plugins=config_plugins,
        )
    elif os.path.splitext(config_path)[1] == ".py":
        _ = load_python_configuration(config_path)
    else:
        raise ValueError(
            "Unknown configuration extension: %r" % os.path.splitext(config_path)[1]
        )
    yield


# The plugin for loading a cobald pipeline
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
                    try:
                        # fully constructed object from !constructor
                        prev_item = item >> prev_item
                    except TypeError:
                        # encoded object from __type__: constructor
                        prev_item = self.translate_hierarchy(
                            item, where="%s[%s]" % (where, index), target=prev_item
                        )
                else:
                    prev_item = self.translate_hierarchy(
                        item, where="%s[%s]" % (where, index)
                    )
                items.append(prev_item)
            return list(reversed(items))
