"""
An instance is a name, e.g. ``hsfei_adc``, with three files behind it:

- ``<repo>/systemd/instances/<name>.env``, which says which daemon script to
  run and where its config is deployed;
- ``<repo>/config/<subsystem>/<name>.yaml``, the config as committed;
- their deployed copies, ``/etc/hispec/instances/<name>.env`` and whatever
  path the ``.env`` gives as ``HISPEC_CONFIG``.

Deployed means the ``.env`` is in ``/etc/hispec/instances/``, since that is
what ``hispec@<name>.service`` reads.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _default_repo_dir() -> Path:
    # install.sh does an editable install, so this file is inside the checkout
    # the daemons run from. Anything else (a wheel) gets the standard path.
    here = Path(__file__).resolve().parents[3]
    if (here / "systemd" / "instances").is_dir():
        return here
    return Path("/opt/hispec/app")


@dataclass(frozen=True)
class Paths:
    """The filesystem layout, overridable for testing and odd hosts."""

    repo: Path
    venv: Path
    etc: Path

    @classmethod
    def from_env(cls, environ: Mapping[str, str] = os.environ) -> "Paths":
        """Build from HISPEC_REPO_DIR / HISPEC_VENV_DIR / HISPEC_ETC_DIR."""
        repo = environ.get("HISPEC_REPO_DIR")
        return cls(
            repo=Path(repo) if repo else _default_repo_dir(),
            venv=Path(environ.get("HISPEC_VENV_DIR", "/opt/hispec/venv")),
            etc=Path(environ.get("HISPEC_ETC_DIR", "/etc/hispec")),
        )

    @property
    def instances(self) -> Path:
        """Deployed instance files, read by hispec@.service."""
        return self.etc / "instances"

    @property
    def repo_instances(self) -> Path:
        """Instance files as committed."""
        return self.repo / "systemd" / "instances"


class TargetError(Exception):
    """A name on the command line matched nothing."""


def unit(name: str) -> str:
    """The systemd unit for an instance."""
    return f"hispec@{name}.service"


def _names_in(directory: Path) -> List[str]:
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.env") if p.is_file())


def deployed(paths: Paths) -> List[str]:
    """Instances deployed on this host, sorted."""
    return _names_in(paths.instances)


def in_repo(paths: Paths) -> List[str]:
    """Instances defined in the repo, sorted."""
    return _names_in(paths.repo_instances)


def repo_configs(paths: Paths, name: str) -> List[Path]:
    """Committed configs for an instance. Exactly one is the healthy case."""
    return sorted((paths.repo / "config").glob(f"*/{name}.yaml"))


def read_env(path: Path) -> Dict[str, str]:
    """Parse a systemd EnvironmentFile: KEY=VALUE lines, # comments."""
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def resolve(targets: Iterable[str], names: List[str]) -> List[str]:
    """Expand command-line targets against the instances in ``names``.

    A target is an instance name (``hsfei_adc``), a subsystem prefix
    (``hsfei``, or just ``fei``), or ``all``. Targets keep their command-line
    order, so ``hispec start power fei`` powers up before it starts the
    mechanisms. Duplicates are dropped, and a target matching nothing is an
    error.
    """
    selected: List[str] = []
    for target in targets:
        if target == "all":
            hits = list(names)
        elif target in names:
            hits = [target]
        else:
            prefix = target.rstrip("_") + "_"
            hits = [n for n in names if n.startswith(prefix)]
            if not hits and not target.startswith("hs"):
                hits = [n for n in names if n.startswith("hs" + prefix)]
        if not hits:
            raise TargetError(target)
        selected.extend(n for n in hits if n not in selected)
    return selected
