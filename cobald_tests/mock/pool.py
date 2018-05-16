from cobald.interfaces.pool import Pool


class MockPool(Pool):
    demand = 0
    utilisation = 1.0

    @property
    def supply(self):
        return self.demand

    @property
    def consumption(self) -> float:
        return self.utilisation
