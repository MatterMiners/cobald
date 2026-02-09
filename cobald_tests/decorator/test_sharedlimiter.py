import os

import pytest

from ..mock.pool import FullMockPool

from cobald.decorator.sharedlimiter import SharedLimiter

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

