from cobald.interfaces import Pool, PoolDecorator


class SharedLimiter(PoolDecorator):
    """
    Limit on utilisation based on a resource shared between multiple pools

    :param target: the pool to which changes are applied
    :param mode: type of sql database, i.e. ``local`` or ``postgres``
    :param db_path: path or connection string to database
    :param db_pool_id: choose a unique id for this pool
    :param db_resource_id: name of the shared resource
    :param db_weight: weight to be appied to ``target.supply`` to calculate consumption of the shared resource
    :param db_global_max_default: default global maximum availability of shared resource if not already set in database

    The weighted ``supply`` determines how much of the shared resource this pool
    is currently consuming, which is written to the database.

    Once the total consumption of all involved pools together is approaching the
    global maximum value defined in the database, the pool ``utilisation`` is
    gradually throttled in order to prevent further resource allocation.
    """

    @property
    def utilisation(self):
        sf = 1.0
        return self.target.utilisation * sf

    def __init__(
        self,
        target: Pool,
        mode: string,
        db_path: str,
        db_pool_id: str,
        db_resource_id: str,
        db_weight: float,
        db_global_max_default: float,
    ):
        super().__init__(target)
        # prepare DB
