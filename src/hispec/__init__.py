"""HISPEC instrument control software."""

__all__ = [
    "HispecDaemon",  # pylint: disable=undefined-all-variable
]


def __getattr__(name):
    # Imported on first use rather than at package import, so that
    # `import hispec.cli` does not pull in libby. The CLI has to keep working
    # (`hispec doctor` especially) on a host whose venv is half broken.
    if name == "HispecDaemon":
        from .daemon import HispecDaemon  # pylint: disable=import-outside-toplevel
        return HispecDaemon
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
