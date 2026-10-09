"""Which instrument this CLI drives.

Everything that differs between instruments is here, so the rest of the package
is about deploying daemons rather than about HISPEC specifically. The values
come from ``instrument.toml`` beside this module; a second instrument ships its
own and reuses the code unchanged.

These are identity, not operator settings. Where an operator needs to override
something, such as a non-standard checkout path, that stays an environment
variable on ``Paths``.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Optional

CONFIG_NAME = "instrument.toml"

SYSTEMD_DIR = Path("/etc/systemd/system")
POLKIT_RULES_DIR = Path("/etc/polkit-1/rules.d")
SUDOERS_DIR = Path("/etc/sudoers.d")
SBIN_DIR = Path("/usr/local/sbin")


# Each attribute is one fact about the instrument rather than hidden state
@dataclass(frozen=True)
class Product:  # pylint: disable=too-many-instance-attributes
    """One instrument's names, and the paths and units derived from them."""

    name: str
    user: str
    ops_group: str
    env_prefix: str
    subsystem_prefix: str
    secret_key_suffix: str = "_env"
    docs_url: str = ""
    # Units and polkit rules this product used to install, reported by doctor
    # so a host that predates a rename can be recognised
    legacy_unit: Optional[str] = field(default=None)
    legacy_polkit_rule: Optional[str] = field(default=None)

    @classmethod
    def load(cls) -> "Product":
        """Read ``instrument.toml`` from beside this module."""
        with resources.files(__package__).joinpath(CONFIG_NAME).open("rb") as handle:
            data = tomllib.load(handle)
        instrument = data["instrument"]
        secrets = data.get("secrets", {})
        legacy = data.get("legacy", {})
        return cls(
            name=instrument["name"],
            user=instrument.get("user", instrument["name"]),
            ops_group=instrument.get("ops_group", f"{instrument['name']}-ops"),
            env_prefix=instrument.get("env_prefix", instrument["name"].upper()),
            subsystem_prefix=instrument.get("subsystem_prefix", ""),
            secret_key_suffix=secrets.get("key_suffix", "_env"),
            docs_url=instrument.get("docs_url", ""),
            legacy_unit=legacy.get("unit"),
            legacy_polkit_rule=legacy.get("polkit_rule"),
        )

    def unit(self, instance: str) -> str:
        """The systemd unit for an instance."""
        return f"{self.name}@{instance}.service"

    def instance_of(self, unit_id: str) -> Optional[str]:
        """The instance a unit id names, or None if it is not one of ours."""
        prefix, suffix = f"{self.name}@", ".service"
        if not unit_id.startswith(prefix) or not unit_id.endswith(suffix):
            return None
        return unit_id[len(prefix):-len(suffix)]

    def env_key(self, name: str) -> str:
        """An instance file's variable, e.g. ``HISPEC_DAEMON`` for ``DAEMON``."""
        return f"{self.env_prefix}_{name}"

    @property
    def unit_template(self) -> Path:
        """The installed template unit every instance runs from."""
        return SYSTEMD_DIR / f"{self.name}@.service"

    @property
    def polkit_rule(self) -> Path:
        """The rule granting the ops group start/stop without a password."""
        return POLKIT_RULES_DIR / f"49-{self.name}.rules"

    @property
    def sudoers(self) -> Path:
        """The drop-in granting passwordless use of the enable helper."""
        return SUDOERS_DIR / f"{self.name}-ops"

    @property
    def enable_helper(self) -> Path:
        """Root helper behind ``enable``, which polkit cannot scope per unit."""
        return SBIN_DIR / f"{self.name}-enable"

    @property
    def legacy_unit_path(self) -> Optional[Path]:
        """Where a pre-rename template unit would still be installed."""
        return SYSTEMD_DIR / self.legacy_unit if self.legacy_unit else None

    @property
    def legacy_polkit_path(self) -> Optional[Path]:
        """Where a pre-rename polkit rule would still be installed."""
        if not self.legacy_polkit_rule:
            return None
        return POLKIT_RULES_DIR / self.legacy_polkit_rule
