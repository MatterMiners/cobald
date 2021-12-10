from typing import NamedTuple, Any
import logging
import warnings

from cobald.interfaces import Pool, PoolDecorator


_DEFAULT_MESSAGE = (
    "demand = %(value)s "
    "[demand=%(demand)s, supply=%(supply)s, "
    "utilisation=%(utilisation).2f, allocation=%(allocation).2f]"
)


# The %-style formatting corresponds to key lookups in a mapping
# To warn about deprecated keys, we use a specialised mapping class
# that warns when a marked item is looked up.
class _WarnValue(NamedTuple):
    """Entry in a `_WarnMap` that raises a `warning` when its `value` is fetched"""

    value: Any
    warning: Warning


class _WarnMap(dict):
    r"""Map that raises a warnings if keys pointing to ``_WarnValue``\ s are accessed"""

    def __getitem__(self, item):
        value = super().__getitem__(item)
        if isinstance(value, _WarnValue):
            warnings.warn(value.warning, stacklevel=2)
            return value.value
        else:
            return value


# Mapping providing test values for all fields of a :py:class:`~.Logger` message
# - Valid fields must have an arbitrary value of correct type to test their formatting.
# - Deprecated fields must use `_WarnValue` to trigger a deprecation warning as well.
_LOGGER_TEST_FIELDS = _WarnMap(
    value=10.0,
    demand=10.0,
    supply=10.0,
    utilisation=0.5,
    allocation=0.5,
    consumption=_WarnValue(
        0.5,
        FutureWarning(
            "The Logger message field 'consumption' is deprecated;"
            " use 'allocation' instead"
        ),
    ),
    target=None,
)


class Logger(PoolDecorator):
    """
    Log a message on every change of ``demand``

    :param name: name of the :py:class:`logging.Logger` to log to
    :param message: format for message to emit on every change
    :param level: numerical logging level

    The ``message`` parameter is used as a ``%``-style format string with named fields.
    Valid named format fields are

    ``value``
        for the new demand being set,

    ``demand``, ``supply``, ``utilisation`` and ``allocation``
        for the current state of ``target``, and

    ``target``
        for the ``target`` pool itself.

    For example, a ``message`` of ``"adjust demand from %(demand)s to %(value)s"``
    will log the old and new demand value.

    .. deprecated:: 0.12.2
        The ``consumption`` format field. Use ``allocation`` instead.
    """

    @property
    def demand(self):
        return self.target.demand

    @demand.setter
    def demand(self, value):
        self._logger.log(
            self.level,
            self.message,
            {
                "value": value,
                "demand": self.target.demand,
                "supply": self.target.supply,
                "utilisation": self.target.utilisation,
                "allocation": self.target.allocation,
                "consumption": self.target.allocation,
                "target": self.target,
            },
        )
        self.target.demand = value

    @property
    def name(self) -> str:
        return self._logger.name

    @name.setter
    def name(self, value: str):
        if value is None:
            value = self.target.__class__.__qualname__
        self._logger = logging.getLogger(value)

    def __init__(
        self,
        target: Pool,
        name: str = None,
        message: str = _DEFAULT_MESSAGE,
        level: int = logging.INFO,
    ):
        super().__init__(target=target)
        # try formatting message to warn about invalid/deprecated fields
        try:
            message % _LOGGER_TEST_FIELDS
        except KeyError as e:
            raise RuntimeError(
                f"invalid {type(self).__name__} message field: {e}"
            ) from None
        self._logger = None  # type: logging.Logger
        self.message = message
        self.name = name
        self.level = level
