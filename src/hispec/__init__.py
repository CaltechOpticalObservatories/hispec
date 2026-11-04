"""HISPEC instrument control software."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Seen by IDEs and linters only; at runtime __getattr__ below imports lazily.
    from .daemon import HispecDaemon
    from .driverdaemon import HispecDriverDaemon

__all__ = ["HispecDaemon", "HispecDriverDaemon"]


def __getattr__(name):
    # Imported on first use rather than at package import, so that
    # `import hispec.cli` does not pull in libby. The CLI has to keep working
    # (`hispec doctor` especially) on a host whose venv is half broken.
    if name == "HispecDaemon":
        from .daemon import HispecDaemon  # pylint: disable=import-outside-toplevel
        return HispecDaemon
    if name == "HispecDriverDaemon":
        from .driverdaemon import HispecDriverDaemon  # pylint: disable=import-outside-toplevel
        return HispecDriverDaemon
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
