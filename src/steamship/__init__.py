from importlib.metadata import PackageNotFoundError, version  # pragma: no cover

try:
    # Change here if project is renamed and does not equal the package name
    dist_name = __name__
    __version__ = version(dist_name)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.1"
finally:
    del version, PackageNotFoundError

try:
    from .base import Configuration, MimeTypes, SteamshipError
    from .data import *

    from .client import Steamship  # isort:skip
except ModuleNotFoundError:
    pass
