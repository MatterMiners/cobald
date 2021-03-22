import pathlib
import importlib.util
import sys


_loaded = -1


def load_configuration(path):
    """
    Load a configuration from a module stored at ``path``

    The ``path`` must end in a valid file extension for the appropriate module type,
    such as ``.py`` or ``.pyc`` for a plaintext or bytecode python module.
    """
    global _loaded
    current_index = _loaded = _loaded + 1
    module_name = f"<cobald config {current_index}>"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None:
        extension = pathlib.Path(path).suffix
        raise RuntimeError(f"Failed to load {path} of type {extension}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
