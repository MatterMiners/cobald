"""
Tools and helpers to declare plugins
"""

from typing import Callable, Iterable, TypeVar, NamedTuple, Hashable
from collections import defaultdict

P = TypeVar("P", bound=Hashable)
A = TypeVar("A")
K = TypeVar("K")


class PluginRequirements(NamedTuple):
    """Requirements of a :py:class:`~.SectionPlugin`"""

    required: bool = False
    before: frozenset[str] = frozenset()
    after: frozenset[str] = frozenset()


class YAMLTagSettings(NamedTuple):
    """Settings for interpreting a YAML tag"""

    eager: bool = False


_PLUGIN_REQUIREMENTS: "dict[Hashable, PluginRequirements]" = defaultdict(
    lambda m=PluginRequirements(): m
)
_YAML_SETTINGS: "dict[Hashable, YAMLTagSettings]" = defaultdict(
    lambda m=YAMLTagSettings(): m
)


def constraints(
    *, before: Iterable[str] = (), after: Iterable[str] = (), required: bool = False
) -> Callable[[P], P]:
    """
    Mark a callable as a plugin with constraints

    :param before: other plugins that must execute before this one
    :param after: other plugins that must execute after this one
    :param required: whether it is an error if the plugin does not apply

    .. note::

        This decorator only sets constraints of a plugin.
        A plugin must still be registered using ``entry_points``.
    """

    def section_wrapper(plugin: P) -> P:
        _PLUGIN_REQUIREMENTS[plugin] = PluginRequirements(
            required=required, before=frozenset(before), after=frozenset(after)
        )
        return plugin

    return section_wrapper


def yaml_tag(*, eager: bool = False) -> Callable[[P], P]:
    """
    Mark a callable as a YAML tag constructor with specific settings

    :param eager: whether the YAML content must be evaluated eagerly

    Since YAML can express recursive data, nested data structures are evaluated lazily
    by default. This means a constructor receives mutable nested data structures
    (e.g. a ``dict[..., list[...]]``) upfront but nested content is added later on.
    If a constructor requires the entire data at once, set ``eager=True`` to enforce
    eager evaluation before calling the constructor.

    .. note::

        This decorator only serves to apply non-default settings for a plugin.
        A plugin must still be registered using ``entry_points``.
    """

    def mark_settings(plugin: P) -> P:
        _YAML_SETTINGS[plugin] = YAMLTagSettings(eager=eager)
        return plugin

    return mark_settings


@yaml_tag(eager=True)
def __yaml_tag_test(*args: A, **kwargs: K) -> tuple[tuple[A, ...], dict[str, K]]:
    """YAML tag constructor for testing only"""
    import copy

    return copy.deepcopy(args), copy.deepcopy(kwargs)
