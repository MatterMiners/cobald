from tempfile import NamedTemporaryFile

import pytest
import copy

from cobald.daemon.config.mapping import ConfigurationError
from cobald.daemon.core.config import load, COBalDLoader, yaml_constructor
from cobald.controller.linear import LinearController

from ...mock.pool import MockPool


# register test pool as safe for YAML configurations
COBalDLoader.add_constructor(tag="!MockPool", constructor=yaml_constructor(MockPool))


# Helpers for testing lazy/eager YAML evaluation
# Since YAML defaults to lazy evaluation, the arguments available during evaluation
# are not necessarily complete.
class TagTracker:
    """Helper to track the arguments supplied to YAML !Tags"""

    def __init__(self, *args, **kwargs):
        # the state of arguments *during* YAML evaluation
        self.orig_args = copy.deepcopy(args)
        self.orig_kwargs = copy.deepcopy(kwargs)
        # the state of arguments *after* YAML evaluation
        self.final_args = args
        self.final_kwargs = kwargs


COBalDLoader.add_constructor(
    tag="!TagTrackerEager", constructor=yaml_constructor(TagTracker, eager=True)
)
COBalDLoader.add_constructor(
    tag="!TagTrackerLazy", constructor=yaml_constructor(TagTracker, eager=False)
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
                    __config_test:
                        tagged: !TagTrackerEager
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
                tagged = get_config_section(config, "__config_test")["tagged"]
                assert isinstance(tagged, TagTracker)
                assert tagged.final_kwargs["host"] == "127.0.0.1"
                assert tagged.final_kwargs["port"] == 1234
                assert tagged.final_kwargs["algorithm"] == "HS256"
                assert tagged.final_kwargs["users"][0]["user_name"] == "tardis"
                assert tagged.final_kwargs["users"][0]["scopes"] == ["user:read"]

    def test_load_tags_eager(self):
        """Load !Tags with substructure, immediately using them"""
        with NamedTemporaryFile(suffix=".yaml") as config:
            with open(config.name, "w") as write_stream:
                write_stream.write(
                    """
                    pipeline:
                        - !MockPool
                    __config_test:
                        tagged: !TagTrackerEager
                          top: "top level value"
                          nested:
                            - leaf: "leaf level value"
                    """
                )
            with load(config.name) as config:
                tagged = get_config_section(config, "__config_test")["tagged"]
                assert isinstance(tagged, TagTracker)
                # eager loading => all data should exist immediately
                assert tagged.orig_kwargs["top"] == "top level value"
                assert tagged.orig_kwargs["nested"] == [{"leaf": "leaf level value"}]
                assert tagged.orig_kwargs == tagged.final_kwargs

    def test_load_tags_lazy(self):
        """Load !Tags with substructure, lazily using them"""
        with NamedTemporaryFile(suffix=".yaml") as config:
            with open(config.name, "w") as write_stream:
                write_stream.write(
                    """
                    pipeline:
                        - !MockPool
                    __config_test:
                        tagged: !TagTrackerLazy
                          top: "top level value"
                          nested:
                            - leaf: "leaf level value"
                    """
                )
            with load(config.name) as config:
                tagged = get_config_section(config, "__config_test")["tagged"]
                assert isinstance(tagged, TagTracker)
                # eager loading => only some data should exist immediately...
                assert tagged.orig_kwargs["top"] == "top level value"
                assert tagged.orig_kwargs["nested"] == []
                # ...but should be there in the end
                assert tagged.final_kwargs["nested"] == [{"leaf": "leaf level value"}]

    def test_load_tags_nested(self):
        """Load !Tags with nested !Tags"""
        with NamedTemporaryFile(suffix=".yaml") as config:
            with open(config.name, "w") as write_stream:
                write_stream.write(
                    """
                    pipeline:
                        - !MockPool
                    __config_test:
                        top_eager: !TagTrackerEager
                          nested:
                          - leaf: "leaf level value"
                          - leaf_lazy: !TagTrackerLazy
                              nested:
                                - leaf: "leaf level value"
                    """
                )
            with load(config.name) as config:
                top_eager = get_config_section(config, "__config_test")["top_eager"]
                # eager tags are evaluated eagerly
                assert top_eager.orig_kwargs["nested"][0] == {
                    "leaf": "leaf level value"
                }
                leaf_lazy = top_eager.orig_kwargs["nested"][1]["leaf_lazy"]
                # eagerness overrides laziness
                assert leaf_lazy.orig_kwargs["nested"] == [{"leaf": "leaf level value"}]

    def test_load_tag_settings(self):
        """Load !Tags with decorator settings"""
        # __yaml_tag_test is provided by the cobald package
        with NamedTemporaryFile(suffix=".yaml") as config:
            with open(config.name, "w") as write_stream:
                write_stream.write(
                    """
                    pipeline:
                        - !MockPool
                    __config_test:
                        settings_tag: !__yaml_tag_test
                            top: "top level value"
                            nested:
                            - leaf: "leaf level value"
                    """
                )
            with load(config.name) as config:
                section = get_config_section(config, "__config_test")
                args, kwargs = section["settings_tag"]
                assert args == ()
                assert kwargs["top"] == "top level value"
                assert kwargs["nested"] == [{"leaf": "leaf level value"}]
