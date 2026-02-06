import pytest

from ..mock.pool import FullMockPool

from cobald.decorator.sharedlimiter import SharedLimiter

import sqlite3

try:
    import psycopg2
    _HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None
    _HAS_PSYCOPG2 = False

class TestSharedLimiter(object):
    db_inputs_local = {
        "mode": "local",
        "db_path": "test.db",
    }

    db_inputs_postgres = {
        "mode": "postgres",
        "db_path": "test.db",
    }

    db_inputs = [
        db_inputs_local
    ]

    if _HAS_PSYCOPG2:
        db_inputs.append(db_inputs_postgres)

    default_inputs = {
        "db_pool_id": "Mock",
        "db_resource_id": "cpu",
        "db_weight": 0.5,
        "db_global_max_default": 0.8
    }

    def test_init_enforcement(self):
        pool = FullMockPool()
        for db_ipnut in self.db_inputs:
            with pytest.raises(ValueError):
                SharedLimiter(pool, **db_ipnut, **self.default_inputs, threshold=-1)
            with pytest.raises(ValueError):
                SharedLimiter(pool, **db_ipnut, **self.default_inputs, threshold=2)
            with pytest.raises(ValueError):
                SharedLimiter(pool, **db_ipnut, **self.default_inputs, share=-1)
            with pytest.raises(ValueError):
                SharedLimiter(pool, **db_ipnut, **self.default_inputs, share=2)
    
    def test_prepare_db(self):
        pool = FullMockPool()
        for db_ipnut in self.db_inputs:
            sharedlimiter = SharedLimiter(pool, **db_ipnut, **self.default_inputs)
         
