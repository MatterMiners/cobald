"""
Tools and helpers to declare plugins
"""
from typing import Iterable, FrozenSet, TypeVar, Optional, Type

from pydantic import BaseModel


T = TypeVar("T")


class PluginRequirements:
    """Requirements of a :py:class:`~.SectionPlugin`"""

    __slots__ = "required", "before", "after", "schema"

    def __init__(
        self,
        required: bool = False,
        before: FrozenSet[str] = frozenset(),
        after: FrozenSet[str] = frozenset(),
        schema: Optional[Type[BaseModel]] = None,
    ):
        self.required = required
        self.before = before
        self.after = after
        self.schema = schema

    def __repr__(self):
        return (
            f"{self.__class__.__name__}"
            f"(required={self.required},"
            f" before={self.before},"
            f" after={self.after}),"
            f" schema={self.schema})"
        )


def constraints(
    *,
    before: Iterable[str] = (),
    after: Iterable[str] = (),
    required: bool = False,
    schema: Optional[Type[BaseModel]] = None,
):
    """
    Mark a callable as a configuration section plugin with constraints

    :param before: other plugins that must execute before this one
    :param after: other plugins that must execute after this one
    :param required: whether it is an error if the plugin does not apply
    :param schema: schema for validation of the section

    .. note::

        This decorator only sets constraints of a plugin.
        A plugin must still be registered using ``entry_points``.
    """

    def section_wrapper(plugin: T) -> T:
        plugin.__requirements__ = PluginRequirements(
            required=required,
            before=frozenset(before),
            after=frozenset(after),
            schema=schema,
        )
        return plugin

    return section_wrapper
