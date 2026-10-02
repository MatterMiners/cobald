import asyncio
import logging

from cobald.interfaces import Pool, PoolDecorator
from cobald.daemon import service
from typing import Any

_DEFAULT_MAX_SHARE_DEVIATION = 0.05
logger = logging.getLogger(__name__)


def _connect_to_db(backend: tuple[Any, ...]) -> Any:
    """Connect to SQL database of one of the supported types and return connection"""
    match backend:
        case ("sqlite", *connection_args):
            import sqlite3

            return sqlite3.connect(*connection_args)
        case ("postgresql", *connection_args):
            import psycopg2

            return psycopg2.connect(*connection_args)
        case _:
            raise NotImplementedError


def _parameter_marker(backend: tuple[Any, ...]) -> str:
    """Return the parameter marker used by the selected DB-API driver."""
    if backend[0] == "sqlite":
        return "?"
    if backend[0] == "postgresql":
        return "%s"
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


@service(flavour=asyncio)
class SharedLimiter(PoolDecorator):
    """
    Limit on utilisation based on a resource shared between multiple pools

    :param target: the pool to which changes are applied
    :param backend: open tuple with backend database type name followed by the connection arguments, for example ``("sqlite", path)``
    :param pool_id: identifier for this pool, (e.g. it's name)
    :param resource_id: identifier for the shared resource (e.g. it's name)
    :param weight: weight to be appied to ``target.supply`` to calculate consumption of the shared resource
    :param default_limit: resource limit to store if ``resource_id`` is not yet present in the database
    :param threshold: relative total resource load at or below which no throttling is applied
    :param share: desired fraction of the total weighted supply attributed to this pool
    :param max_share_deviation: share difference at which the stronger or gentler throttling curve is applied fully
    :param interval: seconds between updates of the shared resource state

    The weighted ``supply`` determines how much of the shared resource this pool
    is currently consuming, which is written to the database.

    Once the total consumption of all involved pools together exceeds
    ``threshold`` and is approaching the global maximum value defined in the
    database, the pool ``utilisation`` is gradually throttled in order to prevent
    further resource allocation.
    """

    @property
    def utilisation(self) -> float:
        return self.target.utilisation * self._utilisation_scale

    async def run(self) -> None:
        """Periodically refresh the cached utilisation scale."""
        while True:
            await asyncio.to_thread(self._update)
            await asyncio.sleep(self.interval)

    def _update(self) -> None:
        """Synchronize supply through the database and update the cached scale."""
        supply = float(self.target.supply)

        con = _connect_to_db(self.backend)
        parameter = _parameter_marker(self.backend)

        try:
            cur = con.cursor()

            cur.execute(
                f"UPDATE pool_supply SET supply = {parameter} "
                f"WHERE resource_id = {parameter} AND pool_id = {parameter}",
                (supply, self.resource_id, self.pool_id),
            )

            con.commit()

            cur.execute(
                f"SELECT upper_limit FROM resources "
                f"WHERE resource_id = {parameter}",
                (self.resource_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(
                    f"shared resource {self.resource_id!r} is missing from the database"
                )
            limit = float(row[0])

            if limit <= 0:
                raise RuntimeError(
                    "invalid resource limit read from database: "
                    f"resource_id={self.resource_id!r}, "
                    f"pool_id={self.pool_id!r}, "
                    f"backend={self.backend[0]!r}, "
                    f"row={row!r}, "
                    f"supply={supply!r}; "
                    "expected upper_limit to be greater than zero"
                )

            cur.execute(
                f"SELECT COALESCE(SUM(weight * supply), 0) FROM pool_supply "
                f"WHERE resource_id = {parameter}",
                (self.resource_id,),
            )
            row = cur.fetchone()

            total_usage = float(row[0])
            my_usage = self.weight * supply
        finally:
            con.close()

        threshold = self.threshold

        # Throttle utilisation if the shared resource exceeds its threshold.
        load = min(total_usage / limit, 1.0)
        share_deviation = 0.0
        if load <= threshold:
            # A total usage of zero produces zero load and returns here, which
            # also prevents division by zero in the share calculation below.
            self._utilisation_scale = 1.0
        else:
            normalized_load = (load - threshold) / (1 - threshold)
            if self.share is not None:
                # Compare this pool's actual share of the total usage with its
                # desired share and calculate the deviation.
                share_deviation = my_usage / total_usage - self.share

            self._utilisation_scale = _scale_factor(
                normalized_load,
                share_deviation,
                self.max_share_deviation,
            )

        logger.debug(
            "updated shared limit: resource=%r pool=%r supply=%s "
            "weighted_total=%s limit=%s load=%s share_deviation=%s "
            "scale=%s utilisation=%s",
            self.resource_id,
            self.pool_id,
            supply,
            total_usage,
            limit,
            load,
            share_deviation,
            self._utilisation_scale,
            self.utilisation,
        )

    def __init__(
        self,
        target: Pool,
        backend: tuple[Any, ...],
        pool_id: str,
        resource_id: str,
        weight: float,
        default_limit: float,
        threshold: float = 0.9,
        share: "float | None" = None,
        max_share_deviation: float = _DEFAULT_MAX_SHARE_DEVIATION,
        interval: float = 1.0,
    ):
        super().__init__(target)

        assert threshold >= 0 and threshold < 1
        if share is not None:
            assert share >= 0 and share <= 1
        assert max_share_deviation > 0 and max_share_deviation <= 1
        assert default_limit > 0
        assert interval > 0

        self.backend = backend
        self.pool_id = pool_id
        self.resource_id = resource_id
        self.weight = weight
        self.default_limit = default_limit
        self.threshold = threshold
        self.share = share
        self.max_share_deviation = max_share_deviation
        self.interval = interval
        self._utilisation_scale = 1.0

        self._prepare_db()
    
    def _prepare_db(self) -> None:
        """ 
        Prepare all the necessary tables in the DB.
        """

        con = _connect_to_db(self.backend)
        parameter = _parameter_marker(self.backend)

        try:
            cur = con.cursor()

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS resources (
                    resource_id TEXT PRIMARY KEY,
                    upper_limit REAL NOT NULL
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS pool_supply (
                    resource_id TEXT NOT NULL,
                    pool_id TEXT NOT NULL,
                    weight REAL NOT NULL,
                    supply REAL NOT NULL,
                    PRIMARY KEY (resource_id, pool_id)
                )
                """
            )

            cur.execute(
                f"INSERT INTO resources(resource_id, upper_limit) "
                f"VALUES ({parameter}, {parameter}) "
                f"ON CONFLICT(resource_id) DO NOTHING",
                (self.resource_id, self.default_limit),
            )

            cur.execute(
                f"INSERT INTO pool_supply(resource_id, pool_id, weight, supply) "
                f"VALUES ({parameter}, {parameter}, {parameter}, {parameter}) "
                f"ON CONFLICT(resource_id, pool_id) DO UPDATE SET "
                f"weight = excluded.weight, supply = excluded.supply",
                (
                    self.resource_id,
                    self.pool_id,
                    self.weight,
                    float(self.target.supply),
                ),
            )

            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
