"""Sequencing for the fiber switcher PLC (MechanicalSwitch).

fiber_switcher.FiberSwitcher sends each PLC command and returns at once; the
only way to know a move or an insertion has finished is to poll the PLC's
status words. SwitchSequencer turns those commands into operations that wait
for the PLC to report completion, stop on an alarm, and can be cancelled.

Positions are named in the config: input groups are where the spectrograph
fibers connect for science, inspection positions put a fiber end in front of
the Lightel camera. Both are a (Port A, Port B) pair.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from hispec.fiberswitch.jobs import JobAborted

# fiber_switcher's insertion_state codes
INSERTION_REMOVED = 1
INSERTION_INSERTED = 3
INSERTION_NAMES = {INSERTION_REMOVED: "removed", INSERTION_INSERTED: "inserted"}

# messages_0_15 bit: the PLC is in automatic operation, so it accepts
# insert, retract and move commands
MSG_AUTOMATIC_OPERATION_AVAILABLE = 0x0004

PORT_A_RANGE = (1, 13)
PORT_B_RANGE = (1, 5)

CLEAN_MODES = ("inside", "outside", "both")

# The mm registers the daemon exposes, keyed by keyword suffix
AXIS_SETTINGS = {
    "retractdist": ("get_retract_distance_mm", "set_retract_distance_mm",
                    "Insertion axis retract-back distance."),
    "caminsertpos": ("get_camera_insertion_position_mm",
                     "set_camera_insertion_position_mm",
                     "Insertion position used at camera (inspection) ports."),
    "noncaminsertpos": ("get_noncamera_insertion_position_mm",
                        "set_noncamera_insertion_position_mm",
                        "Insertion position used at non-camera ports."),
}


class SwitchError(RuntimeError):
    """The switcher refused a command, raised an alarm or timed out."""


@dataclass(frozen=True)
class Position:
    """A named (Port A, Port B) pair."""

    name: str
    port_a: int
    port_b: int

    @property
    def ports(self) -> Tuple[int, int]:
        """The (Port A, Port B) pair."""
        return (self.port_a, self.port_b)


def parse_positions(spec: Optional[Dict[str, Any]], kind: str) -> Dict[str, Position]:
    """Build named positions from a config mapping of name -> {port_a, port_b}."""
    positions = {}
    for name, entry in (spec or {}).items():
        if not isinstance(entry, dict):
            raise ValueError(f"{kind} {name!r}: expected a mapping with port_a and port_b")
        try:
            port_a, port_b = int(entry["port_a"]), int(entry["port_b"])
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"{kind} {name!r}: port_a and port_b must be integers") from e
        _check_port("A", port_a, PORT_A_RANGE, f"{kind} {name!r}")
        _check_port("B", port_b, PORT_B_RANGE, f"{kind} {name!r}")
        positions[str(name)] = Position(str(name), port_a, port_b)
    return positions


def parse_target(value: str) -> Position:
    """A Port A, Port B pair typed by hand: "5,2", "5 2" or "A5 B2"."""
    parts = str(value).replace(",", " ").split()
    try:
        if len(parts) != 2:
            raise ValueError
        port_a = int(parts[0][1:] if parts[0][:1] in "Aa" else parts[0])
        port_b = int(parts[1][1:] if parts[1][:1] in "Bb" else parts[1])
    except ValueError as e:
        raise ValueError(f"expected Port A and Port B, like '5,2'; got {value!r}") from e
    _check_port("A", port_a, PORT_A_RANGE, "target")
    _check_port("B", port_b, PORT_B_RANGE, "target")
    return Position(f"A{port_a}B{port_b}", port_a, port_b)


def _check_port(port: str, value: int, limits: Tuple[int, int], where: str) -> None:
    if not limits[0] <= value <= limits[1]:
        raise ValueError(f"{where}: Port {port} position {value} outside "
                         f"{limits[0]}-{limits[1]}")


def alarm_word(status) -> int:
    """Both alarm words as one 32-bit value."""
    return status.alarms_0_15 | (status.alarms_16_31 << 16)


def message_word(status) -> int:
    """Both message words as one 32-bit value."""
    return status.messages_0_15 | (status.messages_16_31 << 16)


def ports_of(status) -> Tuple[int, int]:
    """The (Port A, Port B) target positions in a status reply."""
    return (status.port_a_target - 100, status.port_b_target - 100)


# pylint: disable=too-many-instance-attributes
class SwitchSequencer:
    """Blocking, cancellable operations on a FiberSwitcher.

    Every operation polls the PLC until it reports the expected state, and
    raises SwitchError on an alarm or a timeout. Pass the job's cancel event
    to make an operation stop, and the switcher halt, when it is set.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, switcher, *, move_timeout_s: float = 30.0,
                 insert_timeout_s: float = 15.0, clean_timeout_s: float = 180.0,
                 home_timeout_s: float = 60.0, start_s: float = 2.0,
                 poll_s: float = 0.2, status_ttl_s: float = 0.5,
                 require_auto: bool = True,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.switcher = switcher
        self.move_timeout_s = move_timeout_s
        self.insert_timeout_s = insert_timeout_s
        self.clean_timeout_s = clean_timeout_s
        self.home_timeout_s = home_timeout_s
        self.start_s = start_s
        self.poll_s = poll_s
        self.status_ttl_s = status_ttl_s
        self.require_auto = require_auto
        self._clock = clock
        self._sleep = sleep
        self._cache_lock = threading.Lock()
        self._cached: Tuple[Optional[float], Any] = (None, None)
        self.last_clean_mode: Optional[str] = None
        self.air_purge: Optional[bool] = None
        # Whether this process has seen a return to origin complete; the PLC
        # does not report it, so it reads false after a daemon restart
        self.homed = False

    # Status

    def status(self, fresh: bool = False):
        """Return the PLC status, reusing one younger than status_ttl_s."""
        with self._cache_lock:
            fetched_at, value = self._cached
            now = self._clock()
            if not fresh and fetched_at is not None and now - fetched_at < self.status_ttl_s:
                return value
            value = self.switcher.read_status()
            self._cached = (now, value)
            return value

    def ports(self) -> Tuple[int, int]:
        """Current (Port A, Port B) target positions."""
        return ports_of(self.status())

    def insertion(self) -> str:
        """removed, inserted, or moving while between the two."""
        return INSERTION_NAMES.get(self.status().insertion_state, "moving")

    def auto_ready(self) -> bool:
        """The PLC reports automatic operation, so it will take motion commands."""
        return bool(self.status().messages_0_15 & MSG_AUTOMATIC_OPERATION_AVAILABLE)

    def at(self, position: Position, inserted: bool) -> bool:
        """True when the switcher is at position, in position and (if asked) inserted."""
        status = self.status()
        if ports_of(status) != position.ports or not status.in_position:
            return False
        return status.insertion_state == INSERTION_INSERTED if inserted else True

    # Operations

    def home(self, cancel: Optional[threading.Event] = None) -> None:
        """Return to origin; the PLC needs this once after power-on.

        in_position can still be set from before the command, so this waits
        start_s for the motion to begin before polling for it.
        """
        self.homed = False
        self.switcher.home(wait=False)
        self._invalidate()
        self._pause(self.start_s, cancel)
        self._wait(lambda s: s.in_position, self.home_timeout_s, "return to origin", cancel)
        self.homed = True

    def connect(self, position: Position, cancel: Optional[threading.Event] = None) -> None:
        """Retract, move to position, and insert the fiber there.

        Does nothing if the fiber is already inserted at position, rather than
        pulling it out and pushing it back in.
        """
        self._require_auto()
        self._invalidate()
        if self.at(position, inserted=True):
            return
        self.retract(cancel)
        self._move(position, cancel)
        self.insert(cancel)

    def move(self, position: Position, cancel: Optional[threading.Event] = None) -> None:
        """Retract and move to position, leaving the fiber retracted."""
        self._require_auto()
        self.retract(cancel)
        self._move(position, cancel)

    def retract(self, cancel: Optional[threading.Event] = None) -> None:
        """Retract the fiber at the current position, if not already retracted."""
        self._require_auto()
        if self.status(fresh=True).insertion_state == INSERTION_REMOVED:
            return
        self.switcher.retract_fiber()
        self._invalidate()
        self._wait(lambda s: s.insertion_state == INSERTION_REMOVED,
                   self.insert_timeout_s, "retract", cancel)

    def insert(self, cancel: Optional[threading.Event] = None) -> None:
        """Insert the fiber at the current position."""
        self._require_auto()
        self.switcher.insert_fiber()
        self._invalidate()
        self._wait(lambda s: s.insertion_state == INSERTION_INSERTED,
                   self.insert_timeout_s, "insert", cancel)

    def clean(self, mode: str, cancel: Optional[threading.Event] = None) -> None:
        """Retract, then run a cleaning cycle and wait for the PLC to settle.

        The PLC moves to its cleaning position itself. It publishes no
        cleaning-done flag, so this waits start_s for the cycle to
        begin, then for the switcher to be in position with the insertion
        axis at rest.
        """
        if mode not in CLEAN_MODES:
            raise ValueError(f"unknown clean mode {mode!r}; expected one of {CLEAN_MODES}")
        self._require_auto()
        self.retract(cancel)
        self.switcher.clean(mode)
        self.last_clean_mode = mode
        self._invalidate()
        self._pause(self.start_s, cancel)
        self._wait(lambda s: s.in_position and s.insertion_state in INSERTION_NAMES,
                   self.clean_timeout_s, f"clean ({mode})", cancel)

    def stop(self) -> None:
        """Stop motion now; safe to call from any thread."""
        self.switcher.stop()
        self._invalidate()

    def set_air_purge(self, value: bool) -> None:
        """Open (True) or close the air purge valve."""
        if value:
            self.switcher.open_air_purge()
        else:
            self.switcher.close_air_purge()
        self.air_purge = bool(value)

    # Internals

    def _move(self, position: Position, cancel: Optional[threading.Event]) -> None:
        self.switcher.set_target_positions(position.port_a, position.port_b)
        self.switcher.move_to_target()
        self._invalidate()
        self._wait(lambda s: s.in_position and ports_of(s) == position.ports,
                   self.move_timeout_s, f"move to {position.name}", cancel)

    def _require_auto(self) -> None:
        if self.require_auto and not self.status(fresh=True).messages_0_15 \
                & MSG_AUTOMATIC_OPERATION_AVAILABLE:
            raise SwitchError("switcher is not in automatic operation; "
                              "check the PLC mode and home it")

    def _wait(self, done: Callable[[Any], bool], timeout_s: float, what: str,
              cancel: Optional[threading.Event]) -> Any:
        deadline = self._clock() + timeout_s
        while True:
            self._check_cancel(cancel, what)
            status = self.status(fresh=True)
            alarms = alarm_word(status)
            if alarms:
                raise SwitchError(f"{what}: switcher alarm 0x{alarms:08X}")
            if done(status):
                return status
            if self._clock() >= deadline:
                raise SwitchError(f"{what}: timed out after {timeout_s:g} s")
            self._sleep(self.poll_s)

    def _pause(self, seconds: float, cancel: Optional[threading.Event]) -> None:
        deadline = self._clock() + seconds
        while self._clock() < deadline:
            self._check_cancel(cancel, "pause")
            self._sleep(min(self.poll_s, max(deadline - self._clock(), 0.0)))

    def _check_cancel(self, cancel: Optional[threading.Event], what: str) -> None:
        if cancel is not None and cancel.is_set():
            self.stop()
            raise JobAborted(f"{what} halted")

    def _invalidate(self) -> None:
        with self._cache_lock:
            self._cached = (None, None)
