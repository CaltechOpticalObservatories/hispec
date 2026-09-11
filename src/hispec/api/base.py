"""Shared plumbing for the HISPEC subsystem API.

The drivers under ``hispec.driver`` already know how to move an axis, home a
controller and read a sensor. This layer is for the functions that *use* those
driver calls: procedures that span several axes or several devices, that wait
on a physical condition, that pull one coherent snapshot out of a subsystem —
the code that otherwise gets written in a one-off script and copied.

What this base class contributes is the boilerplate every such procedure needs
before it can call a driver at all:

* find the device's settings in the same ``config/<group>/*.yaml`` files the
  daemons read, so addresses and named positions have one definition;
* construct the right driver and connect it, once, on first use;
* poll for a physical condition with a timeout (:meth:`wait_until`).
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional

import yaml

from .errors import ConfigError, ProcedureTimeout

#: Environment variable pointing at a deployment's ``config`` directory.
CONFIG_DIR_ENV = "HISPEC_CONFIG_DIR"

#: Default interval, in seconds, between polls in :meth:`SubsystemAPI.wait_until`.
DEFAULT_POLL_S = 0.2


@dataclass(frozen=True)
class DeviceSpec:
    """How to bring up one device's driver.

    Args:
        builder: Called as ``builder(config, logger)`` with the device's parsed
            YAML config; returns a connected driver instance.
        config_file: Config file name, relative to the subsystem's config
            directory. Defaults to ``<group_id>_<device>.yaml``.
        description: What the device is, for logs and ``--help`` style output.
    """

    builder: Callable[[Dict[str, Any], logging.Logger], Any]
    config_file: Optional[str] = None
    description: str = ""


def resolve_config_dir(group_id: str, override: Optional[str] = None) -> Path:
    """Locate the directory holding one subsystem's daemon configs.

    The configs are deployment data rather than package data, so an installed
    ``hispec`` has to be pointed at them. Checked in order: an explicit
    ``override``, ``$HISPEC_CONFIG_DIR/<group_id>``, then ``config/<group_id>``
    in a source checkout of this repository.
    """
    candidates = []
    if override:
        candidates.append(Path(override))
    env_dir = os.environ.get(CONFIG_DIR_ENV)
    if env_dir:
        candidates.append(Path(env_dir) / group_id)
    # src/hispec/api/base.py -> repository root
    candidates.append(Path(__file__).resolve().parents[3] / "config" / group_id)

    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise ConfigError(
        f"no config directory for '{group_id}'; tried "
        f"{', '.join(str(c) for c in candidates)}. "
        f"Pass config_dir=, or set {CONFIG_DIR_ENV}.")


@dataclass
class _DeviceState:
    """One device's lazily loaded config and driver."""

    config: Optional[Dict[str, Any]] = None
    driver: Any = None
    errors: list = field(default_factory=list)


class SubsystemAPI:
    """Base class for one subsystem's API over its device drivers.

    A subclass sets :attr:`group_id` and :attr:`DEVICE_SPECS`, then adds the
    procedures that make the subsystem do something useful. Devices connect on
    first use, so a procedure that only touches the cryostat never opens a
    socket to a motion controller.

    Args:
        config_dir: Directory of this subsystem's device configs. Resolved by
            :func:`resolve_config_dir` when omitted.
        logger: Logger to use; defaults to ``hispec.api.<group_id>``.
    """

    #: The subsystem's config/daemon group, e.g. ``"hsfei"``. Set by subclasses.
    group_id: str = ""

    #: ``{device name: DeviceSpec}`` for every device the subsystem owns.
    DEVICE_SPECS: Mapping[str, DeviceSpec] = {}

    def __init__(self, config_dir: Optional[str] = None, *,
                 logger: Optional[logging.Logger] = None) -> None:
        if not self.group_id:
            raise ValueError(f"{type(self).__name__} must set a group_id")
        self.logger = logger or logging.getLogger(f"hispec.api.{self.group_id}")
        self.config_dir = resolve_config_dir(self.group_id, config_dir)
        self._state: Dict[str, _DeviceState] = {
            name: _DeviceState() for name in self.DEVICE_SPECS}

    # -- configuration --------------------------------------------------------

    def config(self, device: str) -> Dict[str, Any]:
        """Return a device's parsed config, reading the file on first call."""
        state = self._device_state(device)
        if state.config is None:
            spec = self.DEVICE_SPECS[device]
            filename = spec.config_file or f"{self.group_id}_{device}.yaml"
            path = self.config_dir / filename
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    state.config = yaml.safe_load(handle) or {}
            except OSError as err:
                raise ConfigError(f"cannot read config for '{device}': {err}") from err
            except yaml.YAMLError as err:
                raise ConfigError(f"invalid YAML in {path}: {err}") from err
        return state.config

    def config_value(self, device: str, path: str, default: Any = None) -> Any:
        """Read a dotted path out of a device's config, e.g. ``hardware.tcp_port``."""
        node: Any = self.config(device)
        for part in path.split("."):
            if not isinstance(node, Mapping) or part not in node:
                return default
            node = node[part]
        return node

    # -- drivers --------------------------------------------------------------

    def driver(self, device: str) -> Any:
        """Return the device's driver, constructing and connecting it once.

        Subsequent calls hand back the same instance, so a procedure can reach
        for a device freely without reconnecting.
        """
        state = self._device_state(device)
        if state.driver is None:
            spec = self.DEVICE_SPECS[device]
            self.logger.info("%s: connecting (%s)", device,
                             spec.description or "device")
            state.driver = spec.builder(self.config(device), self.logger)
        return state.driver

    def attach(self, device: str, driver: Any) -> None:
        """Use an already-connected driver for a device, instead of building one.

        For sharing one open controller between APIs, and for substituting a
        simulator or a test double without touching :attr:`DEVICE_SPECS`.
        """
        self._device_state(device).driver = driver

    def is_connected(self, device: str) -> bool:
        """Report whether the device has a driver that believes it is connected."""
        state = self._device_state(device)
        if state.driver is None:
            return False
        try:
            return bool(state.driver.is_connected())
        except Exception as err:  # pylint: disable=broad-except
            self.logger.warning("%s: connection check failed: %s", device, err)
            return False

    def connect(self, devices: Optional[Iterable[str]] = None) -> Dict[str, Optional[str]]:
        """Bring up several devices at once, without stopping at the first failure.

        Returns ``{device: None}`` where the driver connected and
        ``{device: error}`` where it did not, so a caller can report what is
        missing instead of dying on one unplugged controller.
        """
        results: Dict[str, Optional[str]] = {}
        for device in self._names(devices):
            try:
                self.driver(device)
                results[device] = None
            except Exception as err:  # pylint: disable=broad-except
                self.logger.error("%s: connect failed: %s", device, err)
                results[device] = str(err)
        return results

    def disconnect(self, devices: Optional[Iterable[str]] = None) -> None:
        """Disconnect the devices that are up, and forget their drivers."""
        for device in self._names(devices):
            state = self._device_state(device)
            if state.driver is None:
                continue
            try:
                state.driver.disconnect()
            except Exception as err:  # pylint: disable=broad-except
                self.logger.error("%s: disconnect failed: %s", device, err)
            state.driver = None

    # -- procedure helpers ----------------------------------------------------

    def wait_until(self, predicate: Callable[[], bool], timeout_s: float, *,
                   poll_s: float = DEFAULT_POLL_S,
                   description: str = "condition") -> float:
        """Poll ``predicate`` until it is true, and return the seconds it took.

        For the waits the drivers do not do for you: a joint wait across two
        axes, a dewar reaching temperature, a gauge settling.

        Raises:
            ProcedureTimeout: ``predicate`` was still false at ``timeout_s``.
        """
        start = time.monotonic()
        deadline = start + timeout_s
        while True:
            if predicate():
                return time.monotonic() - start
            now = time.monotonic()
            if now >= deadline:
                raise ProcedureTimeout(
                    f"{description} not satisfied after {timeout_s}s")
            time.sleep(min(poll_s, deadline - now))

    def collect(self, reads: Mapping[str, Callable[[], Any]]) -> Dict[str, Any]:
        """Run a map of named read callables, mapping failures to ``None``.

        For status and logging paths, where one dead device should cost the
        caller that one value rather than the whole snapshot.
        """
        values: Dict[str, Any] = {}
        for name, read in reads.items():
            try:
                values[name] = read()
            except Exception as err:  # pylint: disable=broad-except
                self.logger.warning("could not read %s: %s", name, err)
                values[name] = None
        return values

    # -- lifecycle ------------------------------------------------------------

    def close(self) -> None:
        """Disconnect every device this object brought up."""
        self.disconnect()

    def __enter__(self) -> "SubsystemAPI":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # -- internals ------------------------------------------------------------

    def _device_state(self, device: str) -> _DeviceState:
        try:
            return self._state[device]
        except KeyError:
            raise KeyError(
                f"unknown {self.group_id} device '{device}'; "
                f"available: {sorted(self.DEVICE_SPECS)}") from None

    def _names(self, devices: Optional[Iterable[str]]) -> Iterable[str]:
        if devices is None:
            return list(self.DEVICE_SPECS)
        names = list(devices)
        for name in names:
            self._device_state(name)
        return names
