from cobald.interfaces import Pool, PoolDecorator

import sqlite3


def _connect_to_db(mode, path):
    """Connect to SQL database of one of the supported types and return connection"""
    match mode:
        case "local":
            return sqlite3.connect(path)
        case _:
            raise NotImplementedError


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
        #update CPU allocation and retrieve total load on shared resource
        con = _connect_to_db(self.mode, self.db_path)
        cur = con.cursor()
        cur.execute("UPDATE %s SET usage = ? WHERE id=?"%self.db_resource_id, [self.target.supply, self.db_pool_id])
        con.commit()
        limit = float(cur.execute("SELECT upper_limit FROM limits WHERE feature=?", [self.db_resource_id]).fetchone()[0])
        total_usage = float(cur.execute("SELECT SUM(weight*usage) FROM %s"%self.db_resource_id).fetchone()[0])
        con.close()

        #throttle down utilization if shared resource close to maximum
        load = min(total_usage/limit, 1.0)
        if load <= 0.9:
            return self.target.utilisation
        else:
            sf = 1.0-(load-0.9)**2*100.0
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
        self.mode = mode
        self.db_path = db_path
        self.db_pool_id = db_pool_id
        self.db_resource_id = db_resource_id
        self.db_weight = db_weight
        self.db_global_max_default = db_global_max_default
        # prepare DB
