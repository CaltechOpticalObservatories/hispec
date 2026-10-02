"""Thin wrappers around systemctl and the root enable helper.

Everything that touches systemd goes through ``run``, so tests can replace it.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List, Sequence

from .instances import unit

# Root-owned and installed by install.sh, with a NOPASSWD sudoers entry for
# hispec-ops. Deliberately not part of this package: the venv is writable by
# the hispec user, so root must never run code from it.
ENABLE_HELPER = "/usr/local/sbin/hispec-enable"


def run(cmd: Sequence[str], capture: bool = False) -> subprocess.CompletedProcess:
    """Run a command, inheriting the terminal unless ``capture``."""
    try:
        return subprocess.run(list(cmd), check=False, text=True, capture_output=capture)
    except FileNotFoundError:
        message = f"{cmd[0]}: not found"
        if not capture:
            print(f"hispec: {message}", file=sys.stderr)
        return subprocess.CompletedProcess(list(cmd), 127, "", message + "\n")


@dataclass(frozen=True)
class UnitState:
    """What systemd says about one instance."""

    active: str     # active, inactive, failed, activating, deactivating
    enabled: str    # enabled, disabled, or empty if systemd does not know it
    since: str      # when ``active`` last changed, as systemd prints it

    @property
    def running(self) -> bool:
        """Up, or on its way up."""
        return self.active in ("active", "activating", "reloading")


UNKNOWN = UnitState(active="unknown", enabled="", since="")


def states(names: List[str]) -> Dict[str, UnitState]:
    """Query every instance in one systemctl call."""
    if not names:
        return {}
    proc = run(
        ["systemctl", "show", "--no-pager",
         "--property=Id,ActiveState,UnitFileState,StateChangeTimestamp",
         *[unit(n) for n in names]],
        capture=True,
    )
    found = {}
    for block in proc.stdout.split("\n\n"):
        props = dict(line.split("=", 1) for line in block.splitlines() if "=" in line)
        unit_id = props.get("Id", "")
        if not unit_id.startswith("hispec@"):
            continue
        name = unit_id[len("hispec@"):-len(".service")]
        found[name] = UnitState(
            active=props.get("ActiveState", "unknown"),
            enabled=props.get("UnitFileState", ""),
            since=_short_time(props.get("StateChangeTimestamp", "")),
        )
    return {n: found.get(n, UNKNOWN) for n in names}


def _short_time(stamp: str) -> str:
    # "Mon 2026-09-21 09:14:02 HST" -> "2026-09-21 09:14:02"
    parts = stamp.split()
    return " ".join(parts[1:3]) if len(parts) >= 3 else stamp


def systemctl(verb: str, name: str) -> bool:
    """start/stop/restart one instance. Output goes to the terminal."""
    return run(["systemctl", verb, unit(name)]).returncode == 0


def enable_helper(args: List[str]) -> subprocess.CompletedProcess:
    """Run the root enable/disable helper without a password prompt.

    ``-n`` makes sudo fail instead of prompting, so a missing sudoers entry
    is reported as such rather than as a mystery password request.
    """
    return run(["sudo", "-n", ENABLE_HELPER, *args], capture=True)
