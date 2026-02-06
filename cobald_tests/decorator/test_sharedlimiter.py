import pytest

from ..mock.pool import FullMockPool

from cobald.decorator.sharedlimiter import SharedLimiter


class TestSharedLimiter(object):
    default_inputs = {
        "mode": "local",
        "db_path": "test.db",
        "db_pool_id": "Mock",
        "db_resource_id": "cpu",
        "db_weight": 0.5,
        "db_global_max_default": 0.8
    }
    def test_init_enforcement(self):
        pool = FullMockPool()
        with pytest.raises(ValueError):
            SharedLimiter(pool, **self.default_inputs, threshold=-1)
        with pytest.raises(ValueError):
            SharedLimiter(pool, **self.default_inputs, threshold=2)
        with pytest.raises(ValueError):
            SharedLimiter(pool, **self.default_inputs, share=-1)
        with pytest.raises(ValueError):
            SharedLimiter(pool, **self.default_inputs, share=2)
    
    def test_prepare_db(self):
        pool = FullMockPool()
        sharedlimiter = SharedLimiter(pool, **self.default_inputs)