import os
from contextlib import contextmanager
from typing import Type

from yaml import SafeLoader, BaseLoader

from ..config.yaml import load_configuration as load_yaml_configuration,\
    yaml_constructor
from ..config.python import load_configuration as load_python_configuration
from ..config.mapping import Translator


class COBalDLoader(SafeLoader):
    """Loader with access to COBalD configuration constructors"""


def add_constructor_plugins(
        entry_point_group: str,
        loader: Type[BaseLoader]
) -> None:
    """
    Add PyYAML constructors from an entry point group to a loader

    :param loader: the PyYAML loader which uses the plugins
    :param entry_point_group: entry point group to search
    """
    from pkg_resources import iter_entry_points
    for entry in iter_entry_points(entry_point_group):
        if entry.name[0] == '!':
            raise RuntimeError(
                "plugin name %r in entry point group %r may not start with '!'" % (
                    entry.name, entry_point_group
                )
            )
        try:
            pipeline_factory = entry.load().s
        except AttributeError:
            pipeline_factory = entry.load()
        loader.add_constructor(
            tag='!' + entry.name,
            constructor=yaml_constructor(pipeline_factory),
        )


@contextmanager
def load(config_path: str):
    """
    Load a configuration and keep it alive for the given context

    :param config_path: path to a configuration file
    """
    # we bind the config to _ to keep it alive
    if os.path.splitext(config_path)[1] in ('.yaml', '.yml'):
        add_constructor_plugins(
            'cobald.config.yaml_constructors',
            COBalDLoader,  # type: ignore
        )
        _ = load_yaml_configuration(
            config_path,
            loader=COBalDLoader,  # type: ignore
            translator=PipelineTranslator()
        )
    elif os.path.splitext(config_path)[1] == '.py':
        _ = load_python_configuration(config_path)
    else:
        raise ValueError(
            'Unknown configuration extension: %r' % os.path.splitext(config_path)[1]
        )
    yield


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
    def translate_hierarchy(self, structure, *, where='', **construct_kwargs):
        try:
            pipeline = structure['pipeline']
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
                            item, where='%s[%s]' % (where, index), target=prev_item
                        )
                else:
                    prev_item = self.translate_hierarchy(
                        item, where='%s[%s]' % (where, index)
                    )
                items.append(prev_item)
            return list(reversed(items))
