from cobald.interfaces import Pool, PoolDecorator, PropertyError


class Default(PoolDecorator):
    """
    Defaults for :py:attr:`~.Pool.utilisation` or :py:attr:`~.Pool.allocation` raising :py:exc:`~.PropertyError`

    :param target: the pool to which defaults are applied
    :param utilisation: default utilisation in case of a :py:exc:`~.PropertyError`
    :param allocation: default allocation in case of a :py:exc:`~.PropertyError`
    """
    def __init__(self, target: Pool, utilisation: float, allocation: float):
        super().__init__(target=target)
        self._utilisation = utilisation
        self._allocation = allocation

    @property
    def utilisation(self) -> float:
        """Fraction of the provided resources which is actively used"""
        try:
            return self.target.utilisation
        except PropertyError:
            return self._utilisation

    @property
    def allocation(self) -> float:
        """Fraction of the provided resources which is assigned for usage"""
        try:
            return self.target.allocation
        except PropertyError:
            return self._allocation
