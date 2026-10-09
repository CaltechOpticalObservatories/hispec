"""The ``hispec`` command: instrumentctl, driven by this instrument's config.

Everything the command does lives in instrumentctl, which knows nothing about
HISPEC. What stays here is the configuration describing this instrument, and
where to find the checkout.
"""
from importlib import resources
from pathlib import Path
from typing import List, Optional

from instrumentctl import run

CONFIG = "instrument.toml"


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the ``hispec`` console script."""
    # parents[3] is the checkout under an editable install, which is what lets
    # a `git pull` change the CLI without reinstalling
    return run(resources.files(__package__).joinpath(CONFIG),
               repo_hint=Path(__file__).resolve().parents[3], argv=argv)
