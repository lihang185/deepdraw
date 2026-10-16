"""Load the maintained pybind11 modules from their fixed runtime directory."""
import importlib.util
import os
from pathlib import Path
import sys

DIRECTORY = Path(__file__).resolve().parent
_dll_directory = None


def load(name):
    global _dll_directory
    if name not in ('suapi', 'suapi_extra', 'skp_exporter'):
        raise ValueError('Unknown SketchUp module: ' + name)
    if _dll_directory is None:
        _dll_directory = os.add_dll_directory(str(DIRECTORY))
    if name != 'suapi':
        load('suapi')
    path = DIRECTORY / (name + '.cp38-win_amd64.pyd')
    existing = sys.modules.get(name)
    if existing is not None:
        if Path(existing.__file__).resolve() != path.resolve():
            raise ImportError('A different SketchUp binding is already loaded: ' + name)
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[name] = module
    return module
