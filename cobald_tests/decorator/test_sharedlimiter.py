import os
import threading

import pytest

from ..mock.pool import FullMockPool

from cobald.decorator.sharedlimiter import SharedLimiter

import sqlite3

test_db_path = "test.db"

db_inputs_sqlite = {"backend": ("sqlite", test_db_path)}

db_inputs = [
    db_inputs_sqlite
]

default_inputs = {
    "pool_id": "Mock",
    "resource_id": "cpu",
    "usage_weight": 0.5,
    "default_limit": 100.0
}

other_pool_inputs = {
    "pool_id": "Other",
    "resource_id": "cpu",
    "usage_weight": 1.0,
}

def _db_con(db_path):
    con = sqlite3.connect(db_path)
    return con


def _db_exec(db_path, sql: str, parameters=()):
    con = _db_con(db_path)

    try:
        cur = con.cursor()
        cur.execute(sql, parameters)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def _update_or_insert_pool_row(
    resource_id: str,
    pool_id: str,
    usage_weight: float,
    supply: float,
    shares: float = 1.0,
):
    con = _db_con(test_db_path)

    try:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO pool_supply"
            "(resource_id, pool_id, usage_weight, shares, supply) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(resource_id, pool_id) DO UPDATE SET "
            "usage_weight = excluded.usage_weight, "
            "shares = excluded.shares, supply = excluded.supply",
            (resource_id, pool_id, usage_weight, shares, supply),
        )
        con.commit()
    finally:
        con.close()

@pytest.fixture(autouse=True)
def clean_sqlite_test_db():
    try:
        os.remove(test_db_path)
    except FileNotFoundError:
        pass
    yield
    try:
        os.remove(test_db_path)
    except FileNotFoundError:
        pass

class TestSharedLimiter(object):
    def test_init_enforcement(self):
        pool = FullMockPool()
        for db_ipnut in db_inputs:
            with pytest.raises(AssertionError):
                SharedLimiter(pool, **db_ipnut, **default_inputs, threshold=-1)
            with pytest.raises(AssertionError):
                SharedLimiter(pool, **db_ipnut, **default_inputs, threshold=2)
            with pytest.raises(AssertionError):
                SharedLimiter(pool, **db_ipnut, **default_inputs, shares=0)
            with pytest.raises(AssertionError):
                SharedLimiter(
                    pool,
                    **db_ipnut,
                    **{**default_inputs, "usage_weight": 0},
                )
            with pytest.raises(AssertionError):
                SharedLimiter(pool, **db_ipnut, **default_inputs, max_share_deviation=0)
            with pytest.raises(AssertionError):
                SharedLimiter(pool, **db_ipnut, **default_inputs, max_share_deviation=2)
            with pytest.raises(AssertionError):
                SharedLimiter(
                    pool,
                    **db_ipnut,
                    **{**default_inputs, "default_limit": 0},
                )
            with pytest.raises(AssertionError):
                SharedLimiter(pool, **db_ipnut, **default_inputs, interval=0)
    
    def test_prepare_db(self):
        pool = FullMockPool()
        for db_ipnut in db_inputs:
            sharedlimiter = SharedLimiter(pool, **db_ipnut, **default_inputs)
            assert sharedlimiter.__service_unit__.flavour is threading

    def test_utilisation_uses_cached_scale(self):
        pool = FullMockPool()
        pool.utilisation = 0.8
        limiter = SharedLimiter(pool, **db_inputs_sqlite, **default_inputs)

        limiter._utilisation_scale = 0.25

        assert limiter.utilisation == pytest.approx(0.2)
    
    @pytest.mark.parametrize("invalid_limit", [0.0, -1.0])
    def test_utilisation_invalid_limit_raises(self, invalid_limit):
        pool = FullMockPool()
        pool.utilisation = 0.42
        pool.supply = 10.0

        for db_input in db_inputs:
            # create limiter (creates tables/rows)
            limiter = SharedLimiter(pool, **db_input, **default_inputs)

            # Simulate an invalid limit introduced outside SharedLimiter.
            _db_exec(
                test_db_path,
                "UPDATE resources SET upper_limit = ? WHERE resource_id = ?",
                (invalid_limit, limiter.resource_id),
            )

            with pytest.raises(RuntimeError) as error:
                limiter._update()

            message = str(error.value)
            assert "invalid resource limit read from database" in message
            assert f"resource_id={limiter.resource_id!r}" in message
            assert f"pool_id={limiter.pool_id!r}" in message
            assert "backend='sqlite'" in message
            assert f"row=({invalid_limit!r},)" in message
            assert f"supply={pool.supply!r}" in message

    def test_missing_pool_row_raises(self):
        pool = FullMockPool()
        limiter = SharedLimiter(pool, **db_inputs_sqlite, **default_inputs)
        _db_exec(
            test_db_path,
            "DELETE FROM pool_supply WHERE resource_id = ? AND pool_id = ?",
            (limiter.resource_id, limiter.pool_id),
        )

        with pytest.raises(RuntimeError, match="pool is missing"):
            limiter._update()

    def test_ids_are_scoped_and_passed_as_query_parameters(self):
        pool = FullMockPool()
        pool.supply = 12.0
        quoted_pool_id = "pool'; DROP TABLE resources; --"
        quoted_resource_id = "resource'; DROP TABLE pool_supply; --"

        SharedLimiter(
            pool,
            **db_inputs_sqlite,
            pool_id=quoted_pool_id,
            resource_id=quoted_resource_id,
            usage_weight=0.5,
            default_limit=100.0,
        )
        SharedLimiter(
            pool,
            **db_inputs_sqlite,
            pool_id=quoted_pool_id,
            resource_id="another-resource",
            usage_weight=1.0,
            default_limit=200.0,
        )

        con = _db_con(test_db_path)
        try:
            rows = con.execute(
                "SELECT resource_id, pool_id FROM pool_supply "
                "WHERE pool_id = ? ORDER BY resource_id",
                (quoted_pool_id,),
            ).fetchall()
        finally:
            con.close()

        assert rows == [
            ("another-resource", quoted_pool_id),
            (quoted_resource_id, quoted_pool_id),
        ]

    def test_restart_updates_weight_and_supply_but_preserves_limit(self):
        pool = FullMockPool()
        pool.supply = 10.0
        SharedLimiter(pool, **db_inputs_sqlite, **default_inputs)

        pool.supply = 20.0
        SharedLimiter(
            pool,
            **db_inputs_sqlite,
            **{
                **default_inputs,
                "usage_weight": 0.75,
                "default_limit": 200.0,
            },
        )

        con = _db_con(test_db_path)
        try:
            limit = con.execute(
                "SELECT upper_limit FROM resources WHERE resource_id = ?",
                (default_inputs["resource_id"],),
            ).fetchone()[0]
            pool_row = con.execute(
                "SELECT usage_weight, shares, supply FROM pool_supply "
                "WHERE resource_id = ? AND pool_id = ?",
                (default_inputs["resource_id"], default_inputs["pool_id"]),
            ).fetchone()
        finally:
            con.close()

        assert limit == 100.0
        assert pool_row == (0.75, 1.0, 20.0)

    def test_utilisation_below_threshold_passthrough(self):
        pool = FullMockPool()
        pool.utilisation = 0.77
        pool.supply = 0.0

        for db_input in db_inputs:
            limiter = SharedLimiter(pool, **db_input, **default_inputs, threshold=0.9)

            # ensure total_usage/limit <= threshold
            # our own row will be overwritten with supply on property access; keep supply 0 => my usage 0.
            _update_or_insert_pool_row(**other_pool_inputs, supply=10.0) # total usage = 10
            # load = 10/100 = 0.1 <= 0.9

            limiter._update()
            got = limiter.utilisation
            assert got == pytest.approx(pool.utilisation)

    def test_utilisation_total_usage_zero_division(self):
        pool = FullMockPool()
        pool.utilisation = 0.77
        pool.supply = 0.0

        for db_input in db_inputs:
            limiter = SharedLimiter(pool, **db_input, **default_inputs, threshold=0.9)

            # ensure total_usage/limit <= threshold
            # our own row will be overwritten with supply on property access; keep supply 0 => my usage 0.
            _update_or_insert_pool_row(**other_pool_inputs, supply=0.0) # total usage = 0
            # load = 0

            limiter._update()
            got = limiter.utilisation
            assert got == pytest.approx(pool.utilisation)

    def test_utilisation_models_curve_blend_and_sf_ordering(self):
        """
        Combine nominal/plus/minus checks:

        Expect: util_plus < util_nom < util_minus (for the same normalized load)
        """
        pool = FullMockPool()
        pool.utilisation = 1.0
        pool.supply = 50.0  # weighted my_usage = 0.5 * 50 = 25

        for db_input in db_inputs:
            threshold = 0.9
            other_usage = 70.0  # ensures load < 1.0

            expected_params = {
                "my_usage": 25.0,
                "total_usage": 95.0,
                "load": 0.95
            }

            # --- Nominal (curve_blend == 0) ---
            nominal = SharedLimiter(
                pool, **db_input, **default_inputs,
                threshold=threshold, shares=25.0
            )

            _update_or_insert_pool_row(
                **other_pool_inputs,
                supply=other_usage,
                shares=70.0,
            )

            nominal._update()
            util_nom = nominal.utilisation

            # --- Plus (curve_blend > 0) ---
            plus = SharedLimiter(
                pool, **db_input, **default_inputs,
                threshold=threshold, shares=5.0
            )
            plus._update()
            util_plus = plus.utilisation

            # --- Minus (curve_blend < 0) ---
            minus = SharedLimiter(
                pool, **db_input, **default_inputs,
                threshold=threshold, shares=60.0
            )
            minus._update()
            util_minus = minus.utilisation

            # Ordering
            assert util_plus < util_nom < util_minus
