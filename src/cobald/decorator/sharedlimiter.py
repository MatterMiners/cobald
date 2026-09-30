from cobald.interfaces import Pool, PoolDecorator
from typing import Any

import logging
logger = logging.getLogger(__name__)

_DEFAULT_MAX_SHARE_DEVIATION = 0.05


def _connect_to_db(backend: str, path: str) -> Any:
    """Connect to SQL database of one of the supported types and return connection"""
    match backend:
        case "sqlite":
            import sqlite3

            return sqlite3.connect(path)
        case "postgresql":
            import psycopg2

            return psycopg2.connect(path)
        case _:
            raise NotImplementedError


def _model_nominal(normalized_load: float) -> float:
    """The default quadratic throttling curve for the normalized load."""
    return 1.0 - normalized_load**2


def _model_plus(normalized_load: float) -> float:
    """The linear curve that throttles more strongly than the default."""
    return 1.0 - normalized_load


def _model_minus(normalized_load: float) -> float:
    """The quartic curve that throttles more gently than the default."""
    return 1.0 - normalized_load**4


def _scale_factor(
    normalized_load: float,
    share_deviation: float,
    max_share_deviation: float,
) -> float:
    """Blend throttling curves according to deviation from 
    the desired share and output scale factor for utilisation value.

    share_deviation is mapped to a curve blend between -1 and 1. Zero uses
    only the nominal curve. Positive values blend toward stronger throttling,
    while negative values blend toward gentler throttling. Deviations at or
    beyond ``max_share_deviation`` use the respective curve fully.
    """
    assert 0 <= normalized_load <= 1
    assert 0 < max_share_deviation <= 1

    # Convert the raw share difference to the [-1, 1] range used for blending.
    # For example, with max_share_deviation=0.05, share_deviation=0.01 gives a
    # curve_blend of 0.2: 80% nominal curve and 20% stronger curve.
    bounded_deviation = max(
        min(share_deviation, max_share_deviation),
        -max_share_deviation,
    )
    curve_blend = bounded_deviation / max_share_deviation

    if curve_blend > 0:
        return (
            (1.0 - curve_blend) * _model_nominal(normalized_load)
            + curve_blend * _model_plus(normalized_load)
        )
    elif curve_blend < 0:
        return (
            (1.0 + curve_blend) * _model_nominal(normalized_load)
            - curve_blend * _model_minus(normalized_load)
        )
    return _model_nominal(normalized_load)


class SharedLimiter(PoolDecorator):
    """
    Limit on utilisation based on a resource shared between multiple pools

    :param target: the pool to which changes are applied
    :param backend: type of SQL database, i.e. ``sqlite`` or ``postgresql``
    :param db_path: path or connection string to database
    :param db_pool_id: choose a unique id for this pool
    :param db_resource_id: name of the shared resource
    :param db_weight: weight to be appied to ``target.supply`` to calculate consumption of the shared resource
    :param db_global_max_default: default global maximum availability of shared resource if not already set in database
    :param threshold: optional parameter from 0 to 1 to define the threshold relative resource usage for the limiter
    :param share: nominal resource share of this pool to be pursued by the limiter (optional)
    :param max_share_deviation: share difference at which the stronger or gentler throttling curve is applied fully

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
        con = _connect_to_db(self.backend, self.db_path)
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
                        "backend": self.backend,
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
            # A total usage of zero produces zero load and returns here, which
            # also prevents division by zero in the share calculation below.
            return self.target.utilisation

        normalized_load = (load - threshold) / (1 - threshold)
        share_deviation = 0.0
        if self.share is not None:
            # Compare this pool's actual share of the total usage with its
            # desired share and calculate the deviation.
            share_deviation = my_usage / total_usage - self.share

        # The selected curve produces a value between zero and one. Multiplying
        # by it reduces the utilisation by the chosen throttling strength.
        return self.target.utilisation * _scale_factor(
            normalized_load,
            share_deviation,
            self.max_share_deviation,
        )

    def __init__(
        self,
        target: Pool,
        backend: str,
        db_path: str,
        db_pool_id: str,
        db_resource_id: str,
        db_weight: float,
        db_global_max_default: float,
        threshold: float = 0.9,
        share: float = None,
        max_share_deviation: float = _DEFAULT_MAX_SHARE_DEVIATION,
    ):
        super().__init__(target)

        assert threshold >= 0 and threshold < 1
        if share is not None:
            assert share >= 0 and share <= 1
        assert max_share_deviation > 0 and max_share_deviation <= 1

        self.backend = backend
        self.db_path = db_path
        self.db_pool_id = db_pool_id
        self.db_resource_id = db_resource_id
        self.db_weight = db_weight
        self.db_global_max_default = db_global_max_default
        self.threshold = threshold
        self.share = share
        self.max_share_deviation = max_share_deviation

        self._prepare_db()
    
    def _prepare_db(self) -> None:
        """ 
        Prepare all the necessary tables in the DB.
        """

        con = _connect_to_db(self.backend, self.db_path)

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
