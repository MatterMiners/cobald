import os

import pytest

from ..mock.pool import FullMockPool

from cobald.decorator.sharedlimiter import SharedLimiter
from cobald.decorator.sharedlimiter import _scale_factor

import sqlite3

db_inputs_local = {
    "mode": "local",
    "db_path": "test.db",
}

db_inputs = [
    db_inputs_local
]

default_inputs = {
    "db_pool_id": "Mock",
    "db_resource_id": "cpu",
    "db_weight": 0.5,
    "db_global_max_default": 100.0
}

other_pool_inputs = {
    "db_pool_id": "Other",
    "db_resource_id": "cpu",
    "db_weight": 1.0,
}

def _db_con(db_path):
    con = sqlite3.connect(db_path)
    return con


def _db_exec(db_path, sql: str):
    con = _db_con(db_path)

    try:
        cur = con.cursor()
        cur.execute(sql)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def _set_upper_limit(db_inputs, resource_id: str, upper: float):
    _db_exec(
        db_inputs["db_path"],
        f"UPDATE limits SET upper_limit = {upper} WHERE feature = '{resource_id}'"
    )

def _update_or_insert_pool_row(db_inputs, db_resource_id: str, db_pool_id: str, db_weight: float, usage: float):
    _db_exec(
        db_inputs["db_path"],
        f"UPDATE {db_resource_id} SET weight={db_weight}, usage={usage} WHERE id='{db_pool_id}'"
    )

    db_path = db_inputs["db_path"]

    con = _db_con(db_path)

    try:
        cur = con.cursor()
        cur.execute(f"SELECT id FROM {db_resource_id} WHERE id='{db_pool_id}'")
        row = cur.fetchone()
        if row is None:
            cur.execute(
                f"INSERT INTO {db_resource_id}(id, weight, usage) VALUES ('{db_pool_id}', {db_weight}, {usage})"
            )
            con.commit()
    finally:
        con.close()

def _scale_factor_expected(x, delta):
    return _scale_factor(x, delta)

def _calculate_x_and_delta_share(pool, limiter, other_limiter_usage,  expected=None):
    my_usage = pool.supply * limiter.db_weight
    total_usage = my_usage + other_limiter_usage

    limit = limiter.db_global_max_default
    load = min(total_usage / limit, 1.0)

    threshold = limiter.threshold
    x = (load - threshold) / (1.0 - threshold)

    delta_share = None

    if expected is not None:
        if "my_usage" in expected:
            assert my_usage == pytest.approx(expected["my_usage"])
        if "total_usage" in expected:
            assert total_usage == pytest.approx(expected["total_usage"])
        if "load" in expected:
            assert load == pytest.approx(expected["load"])

    if limiter.share is not None:
        my_share = my_usage / total_usage
        delta_share = my_share - limiter.share

        delta_share = 20.0 * max(min(delta_share, 0.05), -0.05)

    return x, delta_share

@pytest.fixture(autouse=True)
def clean_local_test_db():
    try:
        os.remove(db_inputs_local["db_path"])
    except FileNotFoundError:
        pass
    yield
    try:
        os.remove(db_inputs_local["db_path"])
    except FileNotFoundError:
        pass

class TestSharedLimiter(object):
    def test_init_enforcement(self):
        pool = FullMockPool()
        for db_ipnut in db_inputs:
            with pytest.raises(ValueError):
                SharedLimiter(pool, **db_ipnut, **default_inputs, threshold=-1)
            with pytest.raises(ValueError):
                SharedLimiter(pool, **db_ipnut, **default_inputs, threshold=2)
            with pytest.raises(ValueError):
                SharedLimiter(pool, **db_ipnut, **default_inputs, share=-1)
            with pytest.raises(ValueError):
                SharedLimiter(pool, **db_ipnut, **default_inputs, share=2)
    
    def test_prepare_db(self):
        pool = FullMockPool()
        for db_ipnut in db_inputs:
            sharedlimiter = SharedLimiter(pool, **db_ipnut, **default_inputs)
    
    def test_utilisation_limit_zero_forces_zero(self):
        pool = FullMockPool()
        pool.utilisation = 0.42
        pool.supply = 10.0

        for db_input in db_inputs:
            # create limiter (creates tables/rows)
            limiter = SharedLimiter(pool, **db_input, **default_inputs)

            # mutate DB: set upper_limit <= 0
            _set_upper_limit(db_input, default_inputs["db_resource_id"], 0.0)

            assert limiter.utilisation == 0

    def test_utilisation_below_threshold_passthrough(self):
        pool = FullMockPool()
        pool.utilisation = 0.77
        pool.supply = 0.0

        for db_input in db_inputs:
            limiter = SharedLimiter(pool, **db_input, **default_inputs, threshold=0.9)

            # ensure total_usage/limit <= threshold
            # our own row will be overwritten with supply on property access; keep supply 0 => my usage 0.
            _update_or_insert_pool_row(db_input, **other_pool_inputs, usage=10.0) # total usage = 10
            # load = 10/100 = 0.1 <= 0.9

            got = limiter.utilisation
            assert got == pytest.approx(pool.utilisation)

    def test_utilisation_total_usage_zero_division(self):
        pool = FullMockPool()
        pool.utilisation = 0.77
        pool.supply = 0.0

        for db_input in db_inputs:
            limiter = SharedLimiter(pool, **db_input, **default_inputs, threshold=0.9, share=0.2)

            # ensure total_usage/limit <= threshold
            # our own row will be overwritten with supply on property access; keep supply 0 => my usage 0.
            _update_or_insert_pool_row(db_input, **other_pool_inputs, usage=0.0) # total usage = 0
            # load = 0

            got = limiter.utilisation
            assert got == pytest.approx(pool.utilisation)

    def test_utilisation_models_delta_and_sf_ordering(self):
        """
        Combine nominal/plus/minus checks:

        Expect: util_plus < util_nom < util_minus (for same x)
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

            # --- Nominal (delta None) ---
            nominal = SharedLimiter(
                pool, **db_input, **default_inputs,
                threshold=threshold, share=None
            )

            _update_or_insert_pool_row(db_input, **other_pool_inputs, usage=other_usage)

            x_nom, delta_nom = _calculate_x_and_delta_share(pool, nominal, other_usage, expected_params)
            util_nom = nominal.utilisation

            # --- Plus (delta > 0) ---
            plus = SharedLimiter(
                pool, **db_input, **default_inputs,
                threshold=threshold, share=0.05
            )
            x_plus, delta_plus = _calculate_x_and_delta_share(pool, plus, other_usage, expected_params)
            util_plus = plus.utilisation

            # --- Minus (delta < 0) ---
            minus = SharedLimiter(
                pool, **db_input, **default_inputs,
                threshold=threshold, share=0.6
            )
            x_minus, delta_minus = _calculate_x_and_delta_share(pool, minus, other_usage, expected_params)
            util_minus = minus.utilisation

            assert x_nom == x_minus == x_plus
            assert delta_nom is None
            assert delta_plus > 0
            assert delta_minus < 0

            # SFs
            sf_nom = _scale_factor_expected(x_nom, delta_nom)
            sf_plus = _scale_factor_expected(x_plus, delta_plus)
            sf_minus = _scale_factor_expected(x_minus, delta_minus)

            # Ordering
            assert util_plus < util_nom < util_minus
