from tempfile import NamedTemporaryFile

import pytest
from contextlib import contextmanager

from cobald.daemon.config.mapping import ConfigurationError
from cobald.daemon.core.config import load, COBalDLoader, yaml_constructor
from cobald.controller.linear import LinearController

from ...mock.pool import MockPool


# register test pool as safe for YAML configurations
COBalDLoader.add_constructor(tag="!MockPool", constructor=yaml_constructor(MockPool))


class TagTracker:
    """Helper to track the invocation of YAML !Tags"""

    count = -1

    def __init__(self, *args, **kwargs):
        type(self).count = self.count = type(self).count + 1
        self.args = args
        self.kwargs = kwargs

    @classmethod
    @contextmanager
    def scope(cls, base_count=-1):
        old_count, cls.count = cls.count, base_count
        try:
            yield
        finally:
            cls.count = old_count


COBalDLoader.add_constructor(
    tag="!TagTracker", constructor=yaml_constructor(TagTracker)
)


def get_config_section(config: dict, section: str):
    return next(
        content for plugin, content in config.items() if plugin.section == section
    )


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
                pipeline = get_config_section(config, "pipeline")
                assert isinstance(pipeline[0], LinearController)
                assert isinstance(pipeline[0].target, MockPool)

    def test_load_tags_substructure(self):
        """Load !Tags with substructure"""
        with NamedTemporaryFile(suffix=".yaml") as config:
            with open(config.name, "w") as write_stream:
                write_stream.write(
                    """
                    pipeline:
                        - !MockPool
                    __config_test__:
                        tagged: !TagTracker
                          host: 127.0.0.1
                          port: 1234
                          algorithm: HS256
                          users:
                            - user_name: tardis
                              scopes:
                                - user:read
                    """
                )
            with load(config.name) as config:
                tagged = get_config_section(config, "__config_test__")["tagged"]
                assert isinstance(tagged, TagTracker)
                assert tagged.kwargs["host"] == "127.0.0.1"
                assert tagged.kwargs["port"] == 1234
                assert tagged.kwargs["algorithm"] == "HS256"
                assert tagged.kwargs["users"][0]["user_name"] == "tardis"
                assert tagged.kwargs["users"][0]["scopes"] == ["user:read"]

    def test_load_tags_nested(self):
        """Load !Tags with nested !Tags"""
        with NamedTemporaryFile(suffix=".yaml") as config:
            with open(config.name, "w") as write_stream:
                write_stream.write(
                    """
                    pipeline:
                        - !MockPool
                    __config_test__:
                        tagged: !TagTracker
                          host: 127.0.0.1
                          port: 1234
                          algorithm: HS256
                          users: !TagTracker
                            - user_name: tardis
                              scopes:
                                - user:read
                    """
                )
            with TagTracker.scope():
                with load(config.name) as config:
                    top_tag = get_config_section(config, "__config_test__")["tagged"]
                    assert top_tag.kwargs["host"] == "127.0.0.1"
                    assert top_tag.kwargs["port"] == 1234
                    assert top_tag.kwargs["algorithm"] == "HS256"
                    sub_tag = top_tag.kwargs["users"]
                    assert isinstance(sub_tag, TagTracker)
                    assert sub_tag.args[0]["scopes"] == ["user:read"]
