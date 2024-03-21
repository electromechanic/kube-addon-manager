import importlib as _importlib
from importlib import resources as _resources


def _import(package, plugin):
    """
    Import the given plugin file from a package
    """
    _importlib.import_module(f"{package}.{plugin}")


def _import_all(package):
    """
    Import all plugins in a package
    """
    files = _resources.contents(package)
    plugins = [f[:-3] for f in files if f.endswith(".py") and f[0] != "_"]
    for plugin in plugins:
        _import(package, plugin)


_import_all(__name__)
