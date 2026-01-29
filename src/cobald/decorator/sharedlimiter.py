from cobald.interfaces import Pool, PoolDecorator

from ..utility import enforce

import sqlite3
import psycopg2

def _connect_to_db(mode, path):
    """Connect to SQL database of one of the supported types and return connection"""
    match mode:
        case "local":
            return sqlite3.connect(path)
        case "postgres":
            return psycopg2.connect(path)
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
        
        cur.execute(
            f"UPDATE {self.db_resource_id} "
            f"SET usage = {self.target.supply} "
            f"WHERE id = '{self.db_pool_id}'"
        )

        con.commit()
        
        cur.execute(
            f"SELECT upper_limit FROM limits "
            f"WHERE feature = '{self.db_resource_id}'"
        )
        limit = float(cur.fetchone()[0])

        cur.execute(
            f"SELECT SUM(weight*usage) FROM {self.db_resource_id}"
        )
        total_usage = float(cur.fetchone()[0] or 0.0)
        
        con.close()

        threshold = self.db_throttle_threshold

        #throttle down utilization if shared resource close to maximum
        load = min(total_usage/limit, 1.0)
        if load <= threshold:
            return self.target.utilisation
        else:
            sf = 1.0 - (load-threshold)**2 / (1-threshold)**2
        return self.target.utilisation * sf

    def __init__(
        self,
        target: Pool,
        mode: str,
        db_path: str,
        db_pool_id: str,
        db_resource_id: str,
        db_weight: float,
        db_global_max_default: float,
        db_throttle_threshold: float = 0.9,
    ):
        super().__init__(target)

        enforce(db_throttle_threshold >= 0 and db_throttle_threshold <= 1, ValueError(f"db_throttle_threshold must be between 0 and 1"))

        self.mode = mode
        self.db_path = db_path
        self.db_pool_id = db_pool_id
        self.db_resource_id = db_resource_id
        self.db_weight = db_weight
        self.db_global_max_default = db_global_max_default
        self.db_throttle_threshold = db_throttle_threshold
        # prepare DB

        self._prepare_db()
    
    def _prepare_db(self) -> None:
        """ 
        Prepare all the necessary tables in the DB.
        """

        con = _connect_to_db(self.mode, self.db_path)

        try:
            cur = con.cursor()

            # Create Limits table
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS limits (
                    feature TEXT PRIMARY KEY,
                    upper_limit REAL NOT NULL
                )
                """
            )

            # Crete feature table:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.db_resource_id} (
                    id TEXT PRIMARY KEY,
                    weight REAL NOT NULL,
                    usage REAL NOT NULL
                )
                """
            )

            # Add the limit
            cur.execute(
                f"SELECT upper_limit FROM limits WHERE feature = '{self.db_resource_id}'"
            )

            row = cur.fetchone()
            
            if row is None:
                cur.execute(
                    f"INSERT INTO limits(feature, upper_limit) VALUES ('{self.db_resource_id}', {self.db_global_max_default})"
                )
            
            cur.execute(
                f"SELECT id FROM {self.db_resource_id} WHERE id = '{self.db_pool_id}'"
            )

            
            row = cur.fetchone()
            
            if row is None:
                cur.execute(
                    f"INSERT INTO {self.db_resource_id}(id, weight, usage) VALUES ('{self.db_pool_id}', {self.db_weight}, {0.0})"
                )
            
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()