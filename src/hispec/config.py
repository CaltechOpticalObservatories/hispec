"""
Configuration ingestion daemons.
"""

from __future__ import annotations # for Python 3.9 compatibility
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


class ConfigError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


# Known HispecDaemon attributes that map directly from config
DAEMON_ATTRS = frozenset({
    "peer_id",
    "bind",
    "address_book",
    "discovery_enabled",
    "discovery_interval_s",
    "transport",
    "rabbitmq_url",
    "group_id",
})


def load_file(path: str | Path) -> Dict[str, Any]:
    """
    Load a configuration file (YAML).

    Args:
        path: Path to the config file

    Returns:
        Parsed configuration dictionary

    Raises:
        ConfigError: If the file cannot be loaded or parsed
    """
    path = Path(path)

    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        raise ConfigError(f"Failed to load config from {path}: {e}")


def extract_daemon_config(
    full_config: Dict[str, Any],
    daemon_id: str,
) -> Dict[str, Any]:
    """
    Extract configuration for a specific daemon from a subsystem config.

    Merges subsystem-level defaults with daemon-specific overrides.

    Args:
        full_config: Full subsystem configuration
        daemon_id: Identifier of the daemon to extract

    Returns:
        Merged configuration for the specific daemon

    Raises:
        ConfigError: If the daemon is not found in the config
    """
    daemons = full_config.get("daemons", {})

    if daemon_id not in daemons:
        available = list(daemons.keys()) if daemons else []
        raise ConfigError(
            f"Daemon '{daemon_id}' not found in config. "
            f"Available daemons: {available}"
        )

    # Start with subsystem-level defaults (excluding 'daemons' key)
    result = {k: v for k, v in full_config.items() if k != "daemons"}

    # Merge daemon-specific config (overrides subsystem defaults)
    daemon_config = daemons[daemon_id]
    if daemon_config:
        _deep_merge(result, daemon_config)

    # Ensure peer_id is set
    if "peer_id" not in result:
        result["peer_id"] = daemon_id

    return result


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    """Deep merge override into base (modifies base in place)."""
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def list_daemons(config: Dict[str, Any]) -> List[str]:
    """
    List all daemon IDs defined in a subsystem config.

    Args:
        config: Subsystem configuration dictionary

    Returns:
        List of daemon identifiers
    """
    return list(config.get("daemons", {}).keys())


def is_subsystem_config(config: Dict[str, Any]) -> bool:
    """Check if a config dict is a subsystem config (has 'daemons' key)."""
    return "daemons" in config


class DaemonConfigLoader:
    """
    Helper class for loading daemon configurations.

    Usage:
        loader = DaemonConfigLoader("config/hsfei.yaml")

        # For subsystem configs with multiple daemons
        for daemon_id in loader.daemon_ids:
            config = loader.get_daemon_config(daemon_id)
            daemon = MyDaemon.from_config(config)

        # Or load a single daemon directly
        config = loader.get_daemon_config("pickoff1", env_prefix="HISPEC_")
    """

    def __init__(self, path: str | Path):
        """
        Initialize loader with a config file path.

        Args:
            path: Path to the config file (YAML or JSON)
        """
        self.path = Path(path)
        self._config: Optional[Dict[str, Any]] = None

    @property
    def config(self) -> Dict[str, Any]:
        """Lazily load and return the raw configuration."""
        if self._config is None:
            self._config = load_file(self.path)
        return self._config

    @property
    def is_subsystem(self) -> bool:
        """Check if this is a subsystem config with multiple daemons."""
        return is_subsystem_config(self.config)

    @property
    def subsystem(self) -> Optional[str]:
        """Get the subsystem name, if defined."""
        return self.config.get("subsystem")

    @property
    def daemon_ids(self) -> List[str]:
        """List all daemon IDs in this config."""
        if self.is_subsystem:
            return list_daemons(self.config)
        # Single daemon config - use peer_id or filename
        peer_id = self.config.get("peer_id", self.path.stem)
        return [peer_id]

    def get_daemon_config(
        self,
        daemon_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get configuration for a specific daemon.

        Args:
            daemon_id: Daemon identifier (required for subsystem configs,
                      optional for single-daemon configs)

        Returns:
            Merged configuration dictionary
        """
        if self.is_subsystem:
            if daemon_id is None:
                raise ConfigError(
                    "daemon_id required for subsystem configs. "
                    f"Available: {self.daemon_ids}"
                )
            return extract_daemon_config(self.config, daemon_id)
        else:
            return self.config.copy()
