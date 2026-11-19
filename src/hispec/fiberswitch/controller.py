"""Fiber switcher controller (MechanicalSwitchController).

Connects input groups to the spectrograph per each port's ConnectionPolicy:
inspecting the fiber end with the camera, cleaning it when it is dirty,
archiving every image and raising an alert when cleaning does not help.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Mapping, Optional

from hispec.fiberswitch.policy import ConnectionPolicy, ControllerState
from hispec.fiberswitch.switch import Position

REFERENCE_SUFFIX = "-reference"


class FiberSwitchController:  # pylint: disable=too-many-instance-attributes
    """Select inputs, inspect and clean fiber ends, take reference images."""

    # pylint: disable=too-many-arguments
    def __init__(self, switch, camera, state: ControllerState, *,
                 input_groups: Mapping[str, Position],
                 inspection_positions: Mapping[str, Position],
                 logger=None, clock: Callable[[], float] = time.time) -> None:
        self.switch = switch
        self.camera = camera
        self.state = state
        self.input_groups = dict(input_groups)
        self.inspection_positions = dict(inspection_positions)
        self.logger = logger
        self._clock = clock

    def select_input(self, name: str, cancel: Optional[threading.Event] = None) -> None:
        """Connect name to the spectrograph, cleaning and inspecting first per policy."""
        policy = self.state.policy(name)
        history = self.state.history(name)
        if policy.clean_interval_h is not None and \
                self._due(history.get("last_clean"), policy.clean_interval_h):
            self._log("info", "%s: clean due (every %g h)", name, policy.clean_interval_h)
            self._clean(name, policy, cancel)
        if self._inspect_due(policy, history):
            self.inspect_and_clean(name, cancel)
        self._log("info", "connecting %s", name)
        self.switch.connect(self.input_groups[name], cancel)
        self.state.set_selected(name)

    def inspect_and_clean(self, name: str,
                          cancel: Optional[threading.Event] = None) -> Dict[str, Any]:
        """Inspect name's fiber end, clean while dirty, alert if it stays dirty.

        Leaves the fiber inserted at its inspection position; select an input
        to reconnect it.
        """
        policy = self._inspectable(name)
        self._apply_camera_settings(policy)
        cleans = 0
        while True:
            record = self._inspect(name, policy, name, cancel)
            found = record.get("region") is not None
            if found and record["dirt"] <= policy.clean_threshold:
                break
            if not found or not policy.clean_on_dirty or cleans >= policy.max_clean_attempts:
                break
            self._log("info", "%s: dirt %.4f above %.4f, cleaning (%d of %d)", name,
                      record["dirt"], policy.clean_threshold, cleans + 1,
                      policy.max_clean_attempts)
            self._clean(name, policy, cancel)
            cleans += 1

        if record.get("region") is None:
            self._alert(name, f"fiber end not found in {record['image']}")
        elif record["dirt"] > policy.alert_threshold:
            self._alert(name, f"dirt {record['dirt']:.4f} above alert threshold "
                              f"{policy.alert_threshold:.4f} after {cleans} clean(s); "
                              f"see {record['image']}")
        return record

    def take_reference(self, name: str,
                       cancel: Optional[threading.Event] = None) -> Dict[str, Any]:
        """Inspect name's fiber end and keep the image as its reference."""
        policy = self._inspectable(name)
        self._apply_camera_settings(policy)
        record = self._inspect(name, policy, f"{name}{REFERENCE_SUFFIX}", cancel,
                               reference=True)
        self.state.record(name, reference_image=record["image"])
        self._log("info", "%s: reference image %s", name, record["image"])
        return record

    # Internals

    def _inspect(self, name: str, policy: ConnectionPolicy, tag: str,
                 cancel: Optional[threading.Event], reference: bool = False) -> Dict[str, Any]:
        self.switch.connect(self.inspection_positions[policy.inspect_position], cancel)
        record = self.camera.inspect(tag, cancel,
                                     max_defect_area_fraction=policy.alert_threshold)
        if not reference:
            self.state.record(name, last_inspect=self._clock(), last_image=record["image"],
                              last_dirt=record["dirt"],
                              last_passed=record.get("region") is not None
                              and record["dirt"] <= policy.alert_threshold)
        self._log("info", "%s: inspected, dirt %.4f, image %s", name, record["dirt"],
                  record["image"])
        return record

    def _clean(self, name: str, policy: ConnectionPolicy,
               cancel: Optional[threading.Event]) -> None:
        self.switch.clean(policy.clean_mode, cancel)
        self.state.record(name, last_clean=self._clock())

    def _apply_camera_settings(self, policy: ConnectionPolicy) -> None:
        for setting, value in policy.camera.items():
            self.camera.set_setting(setting, value)

    def _inspectable(self, name: str) -> ConnectionPolicy:
        policy = self.state.policy(name)
        if not policy.inspect_position:
            raise ValueError(f"{name} has no inspect_position in its policy")
        if policy.inspect_position not in self.inspection_positions:
            raise ValueError(f"{name}: unknown inspection position "
                             f"{policy.inspect_position!r}")
        return policy

    def _inspect_due(self, policy: ConnectionPolicy, history: Dict[str, Any]) -> bool:
        if policy.inspect == "always":
            return True
        if policy.inspect == "interval":
            return self._due(history.get("last_inspect"), policy.inspect_interval_h)
        return False

    def _due(self, last: Optional[float], interval_h: float) -> bool:
        return last is None or self._clock() - float(last) >= interval_h * 3600.0

    def _alert(self, name: str, message: str) -> None:
        stamp = datetime.fromtimestamp(self._clock(), timezone.utc).isoformat(timespec="seconds")
        self.state.set_alert(f"{stamp} {name}: {message}")
        self.state.record(name, last_passed=False)
        self._log("error", "ALERT %s: %s", name, message)

    def _log(self, level: str, msg: str, *args) -> None:
        if self.logger is not None:
            getattr(self.logger, level)(msg, *args)
