"""
An instance is a name, e.g. ``hsfei_adc``, with three files behind it:

- ``<repo>/systemd/instances/<name>.env``, which says which daemon script to
  run and where its config is deployed;
- ``<repo>/config/<subsystem>/<name>.yaml``, the config as committed;
- their deployed copies, ``<etc>/instances/<name>.env`` and whatever path the
  ``.env`` gives as the config.

Deployed means the ``.env`` is in ``<etc>/instances/``, since that is what the
template unit reads.
"""
from __future__ import annotations

import os
import re
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Tuple

import yaml

from .product import Product

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _default_repo_dir(product: Product) -> Path:
    # install.sh does an editable install, so this file is inside the checkout
    # the daemons run from. Anything else (a wheel) gets the standard path.
    here = Path(__file__).resolve().parents[3]
    if (here / "systemd" / "instances").is_dir():
        return here
    return Path(f"/opt/{product.name}/app")


@dataclass(frozen=True)
class Paths:
    """The filesystem layout, overridable for testing and odd hosts.

    Carries the product so every command reaches it through the one argument
    they all already take.
    """

    product: Product
    repo: Path
    venv: Path
    etc: Path

    @classmethod
    def from_env(cls, product: Optional[Product] = None,
                 environ: Optional[Mapping[str, str]] = None) -> "Paths":
        """Build from <PREFIX>_REPO_DIR / _VENV_DIR / _ETC_DIR."""
        product = product or Product.load()
        environ = os.environ if environ is None else environ
        repo = environ.get(product.env_key("REPO_DIR"))
        return cls(
            product=product,
            repo=Path(repo) if repo else _default_repo_dir(product),
            venv=Path(environ.get(product.env_key("VENV_DIR"),
                                  f"/opt/{product.name}/venv")),
            etc=Path(environ.get(product.env_key("ETC_DIR"),
                                 f"/etc/{product.name}")),
        )

    @property
    def instances(self) -> Path:
        """Deployed instance files, read by the template unit."""
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
    """Return this host's role, from <etc>/host or its short hostname."""
    path = paths.etc / "host"
    if path.is_file():
        role = path.read_text(encoding="utf-8").strip()
        if role:
            return role
    return socket.gethostname().split(".")[0]


def assigned_host(product: Product, env_file: Path) -> Optional[str]:
    """Return the host an instance file claims, or None when it claims none."""
    if not env_file.is_file():
        return None
    return read_env(env_file).get(product.env_key("HOST")) or None


class TargetError(Exception):
    """A name on the command line matched nothing."""


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


def _secret_keys(node: Any, suffix: str,
                 prefix: str = "") -> Iterator[Tuple[str, str]]:
    """Yield (config key, variable name) for every credential key in a config."""
    if not isinstance(node, Mapping):
        return
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if str(key).endswith(suffix) and isinstance(value, str) and value:
            yield path, value
        else:
            yield from _secret_keys(value, suffix, path)


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
        env = read_env(paths.instances / f"{instance}.env")
        config = env.get(paths.product.env_key("CONFIG"), "")
        if not config or not Path(config).is_file():
            continue
        parsed = yaml.safe_load(Path(config).read_text(encoding="utf-8")) or {}
        for key, variable in _secret_keys(parsed, paths.product.secret_key_suffix):
            needed.setdefault(variable, []).append(f"{instance} ({key})")
    return needed


def secrets_set(paths: Paths) -> Optional[Dict[str, str]]:
    """Return the variables secrets.env defines, or None if it cannot be read."""
    try:
        return read_env(paths.secrets)
    except OSError:
        return None


def resolve(product: Product, targets: Iterable[str], names: List[str]) -> List[str]:
    """Expand command-line targets against the instances in ``names``.

    A target is an instance name (``hsfei_adc``), a subsystem prefix
    (``hsfei``, or just ``fei`` where the product sets one), or ``all``.
    Targets keep their command-line order, so ``start power fei`` powers up
    before it starts the mechanisms. Duplicates are dropped, and a target
    matching nothing is an error.
    """
    shorthand = product.subsystem_prefix
    selected: List[str] = []
    for target in targets:
        if target == "all":
            hits = list(names)
        elif target in names:
            hits = [target]
        else:
            prefix = target.rstrip("_") + "_"
            hits = [n for n in names if n.startswith(prefix)]
            if not hits and shorthand and not target.startswith(shorthand):
                hits = [n for n in names if n.startswith(shorthand + prefix)]
        if not hits:
            raise TargetError(target)
        selected.extend(n for n in hits if n not in selected)
    return selected
