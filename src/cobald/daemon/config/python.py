import importlib.util
import sys


_loaded = -1


def load_configuration(path):
    global _loaded
    current_index = _loaded = _loaded + 1
    module_name = f"<cobald config {current_index}>"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None:
        raise RuntimeError(f"Failed to load {path}: no import spec could be created")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
