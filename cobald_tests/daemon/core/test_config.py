from tempfile import NamedTemporaryFile

import pytest

from cobald.daemon.config.mapping import ConfigurationError
from cobald.daemon.core.config import load, COBalDLoader, yaml_constructor
from cobald.controller.linear import LinearController

from ...mock.pool import MockPool


# register test pool as safe for YAML configurations
COBalDLoader.add_constructor(tag="!MockPool", constructor=yaml_constructor(MockPool))


class TestYamlConfig:
    def test_load(self):
        """Load a valid YAML config"""
        with NamedTemporaryFile(suffix=".yaml") as config:
            with open(config.name, "w") as write_stream:
                write_stream.write(
                    """
                    pipeline:
                        - !LinearController
                          low_utilisation: 0.9
                          high_allocation: 1.1
                        - !MockPool
                    """
                )
            with load(config.name):
                assert True
            assert True

    def test_load_invalid(self):
        """Load a invalid YAML config (invalid keyword argument)"""
        with NamedTemporaryFile(suffix=".yaml") as config:
            with open(config.name, "w") as write_stream:
                write_stream.write(
                    """
                    pipeline:
                        - !LinearController
                          low_utilisation: 0.9
                          foo: 0
                        - !MockPool
                    """
                )
            with pytest.raises(TypeError):
                with load(config.name):
                    assert False

    def test_load_dangling(self):
        """Forbid loading a YAML config with dangling content"""
        with NamedTemporaryFile(suffix=".yaml") as config:
            with open(config.name, "w") as write_stream:
                write_stream.write(
                    """
                    pipeline:
                        - !LinearController
                          low_utilisation: 0.9
                          high_allocation: 1.1
                        - !MockPool
                    random_things:
                        foo: bar
                    """
                )
            with pytest.raises(ConfigurationError):
                with load(config.name):
                    assert False

    def test_load_missing(self):
        """Forbid loading a YAML config with missing content"""
        with NamedTemporaryFile(suffix=".yaml") as config:
            with open(config.name, "w") as write_stream:
                write_stream.write(
                    """
                    logging:
                        version: 1.0
                    """
                )
            with pytest.raises(ConfigurationError):
                with load(config.name):
                    assert False

    def test_load_mixed_creation(self):
        """Load a YAML config with mixed pipeline step creation methods"""
        with NamedTemporaryFile(suffix=".yaml") as config:
            with open(config.name, "w") as write_stream:
                write_stream.write(
                    """
                    pipeline:
                        - __type__: cobald.controller.linear.LinearController
                          low_utilisation: 0.9
                          high_allocation: 0.9
                        - !MockPool
                    """
                )
            with load(config.name) as config:
                pipeline = next(
                    content
                    for plugin, content in config.items()
                    if plugin.section == "pipeline"
                )
                assert isinstance(pipeline[0], LinearController)
                assert isinstance(pipeline[0].target, MockPool)
