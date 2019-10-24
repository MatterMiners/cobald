import logging

from cobald.interfaces import Pool, PoolDecorator


_DEFAULT_MESSAGE = (
    "demand = %(value)s "
    "[demand=%(demand)s, supply=%(supply)s, "
    "utilisation=%(utilisation).2f, consumption=%(consumption).2f]"
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

    ``demand``, ``supply``, ``utilisation`` and ``consumption``
        for the current state of ``target``, and

    ``target``
        for the raw ``target`` pool.
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
        self._logger = None  # type: logging.Logger
        self.message = message
        self.name = name
        self.level = level
