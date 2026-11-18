"""Per-port connection policy and the controller's persisted state.

A ConnectionPolicy says, for one input group, when to inspect and clean its
fiber end before connecting it, the dirt thresholds, and the camera settings
to inspect with. Defaults come from the config; changes made at runtime
through the policy keywords are saved to a JSON state file so they survive a
restart, along with each port's inspection history and reference image.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import asdict, dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from hispec.fiberswitch.switch import CLEAN_MODES

INSPECT_MODES = ("never", "always", "interval")


@dataclass(frozen=True)
class ConnectionPolicy:  # pylint: disable=too-many-instance-attributes
    """When and how to inspect and clean one port before connecting it."""

    # Inspection position (from the switch config) that images this port's fiber end
    inspect_position: Optional[str] = None
    # never, always (on every select), or interval (once per inspect_interval_h)
    inspect: str = "never"
    inspect_interval_h: float = 24.0
    # Clean on select once this many hours have passed since the last clean;
    # null to clean only when an inspection finds dirt
    clean_interval_h: Optional[float] = None
    clean_mode: str = "both"
    clean_on_dirty: bool = True
    max_clean_attempts: int = 2
    # Dirt as a fraction of the fiber-end area: clean above clean_threshold,
    # alert if still above alert_threshold once cleaning attempts run out
    clean_threshold: float = 0.005
    alert_threshold: float = 0.01
    # Camera settings applied before inspecting, by name (exposure, gain, ...)
    camera: Dict[str, float] = field(default_factory=dict)

    def validate(self) -> None:
        """Raise ValueError if a field is out of range."""
        if self.inspect not in INSPECT_MODES:
            raise ValueError(f"inspect must be one of {INSPECT_MODES}, not {self.inspect!r}")
        if self.clean_mode not in CLEAN_MODES:
            raise ValueError(f"clean_mode must be one of {CLEAN_MODES}, not {self.clean_mode!r}")
        if self.inspect_interval_h <= 0:
            raise ValueError("inspect_interval_h must be positive")
        if self.clean_interval_h is not None and self.clean_interval_h <= 0:
            raise ValueError("clean_interval_h must be positive or null")
        if self.max_clean_attempts < 0:
            raise ValueError("max_clean_attempts must be zero or more")
        for name in ("clean_threshold", "alert_threshold"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must be a fraction between 0 and 1")
        if self.inspect != "never" and not self.inspect_position:
            raise ValueError("inspect_position is required unless inspect is never")
        if not isinstance(self.camera, dict):
            raise ValueError("camera must be a mapping of setting name to value")

    def updated(self, changes: Mapping[str, Any]) -> "ConnectionPolicy":
        """A copy with changes applied and validated; unknown fields are an error."""
        known = {f.name for f in fields(self)}
        unknown = set(changes) - known
        if unknown:
            raise ValueError(f"unknown policy fields {sorted(unknown)}; known: {sorted(known)}")
        policy = replace(self, **_coerce(dict(changes)))
        policy.validate()
        return policy

    def to_dict(self) -> Dict[str, Any]:
        """The policy as a JSON-safe dict."""
        return asdict(self)


def _coerce(changes: Dict[str, Any]) -> Dict[str, Any]:
    """Cast the numeric fields, since JSON and YAML may give ints for floats."""
    for name in ("inspect_interval_h", "clean_threshold", "alert_threshold"):
        if name in changes:
            changes[name] = float(changes[name])
    if changes.get("clean_interval_h") is not None:
        changes["clean_interval_h"] = float(changes["clean_interval_h"])
    if "max_clean_attempts" in changes:
        changes["max_clean_attempts"] = int(changes["max_clean_attempts"])
    if "camera" in changes:
        changes["camera"] = {str(k): float(v) for k, v in (changes["camera"] or {}).items()}
    return changes


class ControllerState:  # pylint: disable=too-many-instance-attributes
    """Policies and per-port history, saved to a JSON file on every change.

    Each port's history holds last_inspect and last_clean (epoch seconds),
    last_image, last_dirt, last_passed and reference_image.
    """

    def __init__(self, path: Optional[str | os.PathLike],
                 defaults: Mapping[str, Any], inputs: Mapping[str, Mapping[str, Any]]) -> None:
        self.path = Path(path).expanduser() if path else None
        self._lock = threading.RLock()
        base = ConnectionPolicy().updated(defaults or {})
        self._configured = {name: base.updated(overrides or {})
                            for name, overrides in inputs.items()}
        self._overrides: Dict[str, Dict[str, Any]] = {}
        self._history: Dict[str, Dict[str, Any]] = {name: {} for name in inputs}
        self.alert = ""
        self.selected = ""
        # Saved overrides ignored on load, as "<input>: <reason>", for the daemon to log
        self.dropped: list[str] = []
        self._load()

    @property
    def inputs(self):
        """The configured input group names."""
        return list(self._configured)

    def policy(self, name: str) -> ConnectionPolicy:
        """The effective policy: config, then any runtime overrides."""
        with self._lock:
            return self._configured[name].updated(self._overrides.get(name, {}))

    def update_policy(self, name: str, changes: Mapping[str, Any]) -> ConnectionPolicy:
        """Apply and save runtime overrides; an empty mapping resets to the config."""
        with self._lock:
            if not changes:
                self._overrides.pop(name, None)
            else:
                merged = {**self._overrides.get(name, {}), **changes}
                self._configured[name].updated(merged)  # validate before keeping
                self._overrides[name] = merged
            self._save()
            return self.policy(name)

    def history(self, name: str) -> Dict[str, Any]:
        """A copy of one port's history."""
        with self._lock:
            return dict(self._history[name])

    def record(self, name: str, **values: Any) -> None:
        """Update and save one port's history."""
        with self._lock:
            self._history[name].update(values)
            self._save()

    def set_alert(self, alert: str) -> None:
        """Set (or clear, with '') the standing alert and save it."""
        with self._lock:
            self.alert = alert
            self._save()

    def set_selected(self, name: str) -> None:
        """Record the input group last connected, and save it."""
        with self._lock:
            self.selected = name
            self._save()

    def _load(self) -> None:
        if self.path is None or not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        for name, overrides in (data.get("policies") or {}).items():
            if name not in self._configured:
                self.dropped.append(f"{name}: no longer a configured input group")
                continue
            try:
                self._configured[name].updated(overrides)
            except (TypeError, ValueError) as e:
                # The config changed under a saved override; keep the config's
                self.dropped.append(f"{name}: {e}")
                continue
            self._overrides[name] = overrides
        for name, history in (data.get("history") or {}).items():
            if name in self._history:
                self._history[name].update(history)
        self.alert = data.get("alert", "")
        self.selected = data.get("selected", "")

    def _save(self) -> None:
        if self.path is None:
            return
        data = {"policies": self._overrides, "history": self._history,
                "alert": self.alert, "selected": self.selected}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Write then rename, so a crash mid-write cannot leave a truncated file
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=f".{self.path.name}.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=True)
                f.write("\n")
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
