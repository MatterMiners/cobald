from cobald.interfaces import Pool


class MockPool(Pool):
    demand = 0

    def __init__(self):
        self._utilisation = 1.0
        self._allocation = 1.0

    @property
    def supply(self):
        return self.demand

    @property
    def allocation(self):
        return self._allocation

    @allocation.setter
    def allocation(self, value):
        if value < self._utilisation:
            self._utilisation = value
        self._allocation = value

    @property
    def utilisation(self):
        return self._utilisation

    @utilisation.setter
    def utilisation(self, value):
        if value > self._allocation:
            self._allocation = value
        self._utilisation = value
