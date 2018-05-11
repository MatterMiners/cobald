import abc

from .pool import Pool


class Controller(abc.ABC):
    """
    Controller for the demand in a pool
    """
    def __init__(self, target: Pool):
        self.target = target
