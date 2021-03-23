import pathlib
import importlib.util
import sys
import itertools


_unique_module_id = itertools.count()


def load_configuration(path):
    """
    Load a configuration from a module stored at ``path``

    The ``path`` must end in a valid file extension for the appropriate module type,
    such as ``.py`` or ``.pyc`` for a plaintext or bytecode python module.

    :raises ValueError: if the extension does not mark a known module type
    """
    # largely based on "Importing a source file directly"
    # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    current_index = next(_unique_module_id)
    module_name = f"<cobald config {current_index}>"
    # the following replicates the regular import machinery:
    #     1. create the module metadata (spec)
    #     2. create a module object base on the metadata
    #     3. execute the source to populate the module
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None:
        extension = pathlib.Path(path).suffix
        raise ValueError(f"Unrecognized file extension {extension} for config {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
