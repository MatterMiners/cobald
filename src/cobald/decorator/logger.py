from typing import NamedTuple, Any
import logging
import warnings

from cobald.interfaces import Pool, PoolDecorator


_DEFAULT_MESSAGE = (
    "demand = %(value)s "
    "[demand=%(demand)s, supply=%(supply)s, "
    "utilisation=%(utilisation).2f, allocation=%(allocation).2f]"
)


class _WarnValue(NamedTuple):
    value: Any
    warning: Warning


class _WarnMap(dict):
    r"""Map raising ``warnings`` for specific keys pointing to ``_WarnValue``\ s"""

    def __getitem__(self, item):
        value = super().__getitem__(item)
        if isinstance(value, _WarnValue):
            warnings.warn(value.warning, stacklevel=2)
            return value.value
        else:
            return value


_DEPRECATION_MAP = _WarnMap(
    value=10.0,
    demand=10.0,
    supply=10.0,
    utilisation=0.5,
    allocation=0.5,
    consumption=_WarnValue(0.5, FutureWarning("")),
    target=None,
)


class Logger(PoolDecorator):
    """
    Proxy which logs all changes of ``target.demand``

    :param name: name of the underlying :py:class:`logging.Logger`
    :param message: message to emit for every change
    :param level: numerical logging level

    The ``message`` parameter is used as a ``%``-style format string with named fields.
    Valid named fields are

    ``value``
        for the new demand to set,

    ``demand``, ``supply``, ``utilisation`` and ``allocation``
        for the current state of ``target``, and

    ``target``
        for the raw ``target`` pool.

    For historical reasons, ``consumption`` is available as an alias of ``allocation``.
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
            message % _DEPRECATION_MAP
        except KeyError as e:
            raise RuntimeError(f"invalid {type(self).__name__} message field: {e}")
        self._logger = None  # type: logging.Logger
        self.message = message
        self.name = name
        self.level = level
