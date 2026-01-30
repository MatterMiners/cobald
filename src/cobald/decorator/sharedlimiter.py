from cobald.interfaces import Pool, PoolDecorator

from ..utility import enforce

import logging
logger = logging.getLogger(__name__)

import sqlite3

try:
    import psycopg2
    _HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None
    _HAS_PSYCOPG2 = False


def _connect_to_db(mode, path):
    """Connect to SQL database of one of the supported types and return connection"""
    match mode:
        case "local":
            return sqlite3.connect(path)
        case "postgres":
            if not _HAS_PSYCOPG2:
                raise ModuleNotFoundError(
                    "Postgres mode requires 'psycopg2' package"
            )
            return psycopg2.connect(path)
        case _:
            raise NotImplementedError


def model_nominal(x):
    return 1.0-x**2


def model_plus(x):
    return 1.0-x


def model_minus(x):
    return 1.0-x**4


def _scale_factor(x, delta):
    enforce(x >= 0 and x <= 1, ValueError(f"x for scale factor must be between 0 and 1"))
    if delta:
        if delta >= 0:
            return (1.0-delta)*model_nominal(x)+delta*model_plus(x)
        else:
            return (1.0+delta)*model_nominal(x)-delta*model_minus(x)
    else:
        return model_nominal(x)


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
    :param threshold: optional parameter from 0 to 1 to define the threshold relative resource usage for the limiter
    :param share: nominal resource share of this pool to be pursued by the limiter (optional)

    The weighted ``supply`` determines how much of the shared resource this pool
    is currently consuming, which is written to the database.

    Once the total consumption of all involved pools together exceeds
    ``threshold`` and is approaching the global maximum value defined in the
    database, the pool ``utilisation`` is gradually throttled in order to prevent
    further resource allocation.
    """

    @property
    def utilisation(self):
        #update CPU allocation and retrieve total load on shared resource
        con = _connect_to_db(self.mode, self.db_path)
        try:
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
            row = cur.fetchone()
            limit = float(row[0] if row and row[0] is not None else 0.0)

            if limit <= 0:
                logger.warning(
                    "SharedLimiter: upper_limit <= 0, forcing utilisation=0",
                    {
                        "resource": self.db_resource_id,
                        "pool_id": self.db_pool_id,
                        "upper_limit": limit,
                        "mode": self.mode,
                        "db_path": self.db_path,
                        "supply": float(self.target.supply),
                    },
                )
                return 0

            cur.execute(
                f"SELECT SUM(weight*usage) FROM {self.db_resource_id}"
            )
            row = cur.fetchone()
            total_usage = float(row[0] if row and row[0] is not None else 0.0)

            cur.execute(
                f"SELECT weight*usage FROM {self.db_resource_id} WHERE id = '{self.db_pool_id}'"
            )
            row = cur.fetchone()
            my_usage = float(row[0] if row and row[0] is not None else 0.0)
        finally:
            con.close()

        threshold = self.threshold

        #throttle down utilization if shared resource close to maximum
        load = min(total_usage/limit, 1.0)
        if load <= threshold:
            return self.target.utilisation
        
        x = (load-threshold) / (1-threshold)
        delta_share = None
        if self.share:
            delta_share = my_usage/total_usage - self.share #does not get here if total_usage==0
            delta_share = 20.0 * max(min(delta_share, 0.05), -0.05) #crop to +-5% and normalise
        return self.target.utilisation * _scale_factor(x, delta_share)

    def __init__(
        self,
        target: Pool,
        mode: str,
        db_path: str,
        db_pool_id: str,
        db_resource_id: str,
        db_weight: float,
        db_global_max_default: float,
        threshold: float = 0.9,
        share: float = None,
    ):
        super().__init__(target)

        enforce(threshold >= 0 and threshold < 1, ValueError(f"threshold must be between 0 and 1"))
        if share:
            enforce(share >= 0 and share <= 1, ValueError(f"threshold must be between 0 and 1"))

        self.mode = mode
        self.db_path = db_path
        self.db_pool_id = db_pool_id
        self.db_resource_id = db_resource_id
        self.db_weight = db_weight
        self.db_global_max_default = db_global_max_default
        self.threshold = threshold
        self.share = share
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
