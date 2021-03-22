import tempfile
import os

from cobald.daemon.config.python import load_configuration


def module_content(identifier):
    return f"""\
identifier = {identifier}
"""


def test_load_pyconfig():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".py") as test_file:
        test_file.write(module_content(0))
        test_file.flush()
        module = load_configuration(test_file.name)
        assert module.identifier == 0


def test_load_pyconfig_many():
    modules = []
    for ident in range(5):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".py") as test_file:
            test_file.write(module_content(ident))
            test_file.flush()
            modules.append((ident, load_configuration(test_file.name)))
    for ident, module in modules:
        assert ident == module.identifier
