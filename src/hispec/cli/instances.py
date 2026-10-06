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
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Tuple

import yaml

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# Set in an instance file, so deploying it on the wrong host is caught before
# two daemons reach for one device
HOST_KEY = "HISPEC_HOST"

# A config names the variable holding a credential, never the value itself
SECRET_KEY_SUFFIX = "_env"


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

    @property
    def secrets(self) -> Path:
        """Shared secrets, read by every unit."""
        return self.etc / "secrets.env"


def host_role(paths: Paths) -> str:
    """Return this host's role, from /etc/hispec/host or its short hostname."""
    path = paths.etc / "host"
    if path.is_file():
        role = path.read_text(encoding="utf-8").strip()
        if role:
            return role
    return socket.gethostname().split(".")[0]


def assigned_host(env_file: Path) -> Optional[str]:
    """Return the host an instance file claims, or None when it claims none."""
    if not env_file.is_file():
        return None
    return read_env(env_file).get(HOST_KEY) or None


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


def _secret_keys(node: Any, prefix: str = "") -> Iterator[Tuple[str, str]]:
    """Yield (config key, variable name) for every ``*_env`` key in a config."""
    if not isinstance(node, Mapping):
        return
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if str(key).endswith(SECRET_KEY_SUFFIX) and isinstance(value, str) and value:
            yield path, value
        else:
            yield from _secret_keys(value, path)


def _broker_secrets() -> List[str]:
    """Return the broker credential variables every daemon needs."""
    # Deferred: importing hispec.daemon pulls in libby, and the CLI has to keep
    # working on a host whose venv is broken, which is when doctor is run
    try:
        from ..daemon import (  # pylint: disable=import-outside-toplevel
            BROKER_PASSWORD_ENV, BROKER_USER_ENV,
        )
    except ImportError:
        return []
    return [BROKER_USER_ENV, BROKER_PASSWORD_ENV]


def required_secrets(paths: Paths) -> Dict[str, List[str]]:
    """Map each variable this host needs to the reasons it is needed.

    Derived from the deployed configs rather than a list someone maintains,
    which is how the installer's own list went stale.
    """
    needed: Dict[str, List[str]] = {
        name: ["every daemon (broker login)"] for name in _broker_secrets()
    }
    for instance in deployed(paths):
        config = read_env(paths.instances / f"{instance}.env").get("HISPEC_CONFIG", "")
        if not config or not Path(config).is_file():
            continue
        parsed = yaml.safe_load(Path(config).read_text(encoding="utf-8")) or {}
        for key, variable in _secret_keys(parsed):
            needed.setdefault(variable, []).append(f"{instance} ({key})")
    return needed


def secrets_set(paths: Paths) -> Optional[Dict[str, str]]:
    """Return the variables secrets.env defines, or None if it cannot be read."""
    try:
        return read_env(paths.secrets)
    except OSError:
        return None


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
