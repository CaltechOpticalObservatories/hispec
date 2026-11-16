"""Tests for the fiber switcher sequencer, against a fake PLC."""
# The fakes mirror fiber_switcher.FiberSwitcher's methods, documented there
# pylint: disable=missing-function-docstring,too-many-instance-attributes

import threading
from dataclasses import dataclass

import pytest

from hispec.fiberswitch.jobs import JobAborted
from hispec.fiberswitch.switch import (parse_target, INSERTION_INSERTED, INSERTION_REMOVED,
                                       MSG_AUTOMATIC_OPERATION_AVAILABLE, Position,
                                       SwitchError, SwitchSequencer, parse_positions)


@dataclass
class Status:
    """The fields of fiber_switcher.SwitcherStatus the sequencer reads."""

    port_a_target: int
    port_b_target: int
    in_position: bool
    insertion_state: int
    alarms_0_15: int = 0
    alarms_16_31: int = 0
    messages_0_15: int = MSG_AUTOMATIC_OPERATION_AVAILABLE
    messages_16_31: int = 0


class FakeSwitcher:
    """A PLC whose commands complete after `lag` status reads."""

    def __init__(self, lag=2):
        self.lag = lag
        self.ports = (1, 1)
        self.current = (1, 1)
        self.insertion = INSERTION_REMOVED
        self.alarms = 0
        self.auto = True
        self.calls = []
        self._pending = []  # (reads left, callable)

    def read_status(self):
        still = []
        for left, apply in self._pending:
            if left <= 1:
                apply()
            else:
                still.append((left - 1, apply))
        self._pending = still
        return Status(self.ports[0] + 100, self.ports[1] + 100,
                      in_position=self.current == self.ports,
                      insertion_state=self.insertion,
                      alarms_0_15=self.alarms,
                      messages_0_15=MSG_AUTOMATIC_OPERATION_AVAILABLE if self.auto else 0)

    def _later(self, apply):
        self._pending.append((self.lag, apply))

    def set_target_positions(self, port_a, port_b):
        self.calls.append(("target", port_a, port_b))
        self.ports = (port_a, port_b)

    def move_to_target(self):
        self.calls.append(("move",))
        ports = self.ports
        self._later(lambda: setattr(self, "current", ports))

    def insert_fiber(self):
        self.calls.append(("insert",))
        self._later(lambda: setattr(self, "insertion", INSERTION_INSERTED))

    def retract_fiber(self):
        self.calls.append(("retract",))
        self._later(lambda: setattr(self, "insertion", INSERTION_REMOVED))

    def clean(self, mode):
        self.calls.append(("clean", mode))
        self.ports = (10, 2)
        self._later(lambda: setattr(self, "current", (10, 2)))

    def home(self, wait=True):
        self.calls.append(("home", wait))
        self.current = None
        self._later(lambda: setattr(self, "current", self.ports))

    def stop(self):
        self.calls.append(("stop",))

    def open_air_purge(self):
        self.calls.append(("purge", True))

    def close_air_purge(self):
        self.calls.append(("purge", False))


class Clock:
    """A clock that advances only when the sequencer sleeps."""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, dt):
        self.t += dt


def make(switcher=None, **kwargs):
    """A sequencer on a fake PLC and fake clock."""
    clock = Clock()
    switcher = switcher or FakeSwitcher()
    kwargs.setdefault("start_s", 0.0)
    return SwitchSequencer(switcher, clock=clock, sleep=clock.sleep, status_ttl_s=0.0,
                           **kwargs), switcher


GROUP = Position("group1", 5, 2)


def test_parse_positions():
    """Config positions become Position objects; out-of-range ports are refused."""
    positions = parse_positions({"a": {"port_a": 13, "port_b": 5}}, "input group")
    assert positions["a"].ports == (13, 5)
    with pytest.raises(ValueError, match="Port A position 14"):
        parse_positions({"a": {"port_a": 14, "port_b": 1}}, "input group")
    with pytest.raises(ValueError, match="integers"):
        parse_positions({"a": {"port_a": 1}}, "input group")


def test_parse_target():
    for text in ("5,2", "5 2", " 5 , 2 ", "A5 B2", "a5,b2"):
        assert parse_target(text).ports == (5, 2)
    for bad in ("5", "5,2,1", "x,2", "14,1", "1,6", "0,1", ""):
        with pytest.raises(ValueError):
            parse_target(bad)


def test_connect_retracts_moves_and_inserts():
    """connect retracts first, then targets, moves, and inserts once in position."""
    seq, plc = make()
    plc.insertion = INSERTION_INSERTED
    seq.connect(GROUP)
    assert plc.calls == [("retract",), ("target", 5, 2), ("move",), ("insert",)]
    assert seq.at(GROUP, inserted=True)


def test_connect_is_a_no_op_when_already_connected():
    """An inserted fiber at the requested position is left alone."""
    seq, plc = make()
    plc.ports = plc.current = GROUP.ports
    plc.insertion = INSERTION_INSERTED
    seq.connect(GROUP)
    assert not plc.calls


def test_connect_skips_retract_when_already_removed():
    """A retracted fiber is not retracted again."""
    seq, plc = make()
    seq.connect(GROUP)
    assert plc.calls[0] == ("target", 5, 2)


def test_alarm_stops_the_wait():
    """A PLC alarm during a move raises with the alarm bits."""
    seq, plc = make()
    plc.move_to_target = lambda: setattr(plc, "alarms", 0x1000)
    with pytest.raises(SwitchError, match="alarm 0x00001000"):
        seq.connect(GROUP)


def test_timeout():
    """A move that never completes times out."""
    seq, plc = make(move_timeout_s=1.0)
    plc.move_to_target = lambda: None
    with pytest.raises(SwitchError, match="timed out"):
        seq.connect(GROUP)


def test_refuses_without_automatic_operation():
    """Motion is refused unless the PLC reports automatic operation."""
    seq, plc = make()
    plc.auto = False
    with pytest.raises(SwitchError, match="automatic operation"):
        seq.connect(GROUP)
    assert not plc.calls


def test_require_auto_can_be_disabled():
    """require_auto=False skips the automatic-operation check."""
    seq, plc = make(require_auto=False)
    plc.auto = False
    seq.connect(GROUP)
    assert seq.at(GROUP, inserted=True)


def test_cancel_stops_the_switcher():
    """A set cancel event halts the PLC and raises JobAborted."""
    seq, plc = make()
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(JobAborted):
        seq.connect(GROUP, cancel)
    assert ("stop",) in plc.calls


def test_clean_retracts_then_waits_for_the_cycle():
    """clean retracts, runs the mode, and returns once the PLC settles."""
    seq, plc = make()
    plc.insertion = INSERTION_INSERTED
    seq.clean("outside")
    assert plc.calls[:2] == [("retract",), ("clean", "outside")]
    assert seq.last_clean_mode == "outside"
    with pytest.raises(ValueError):
        seq.clean("sideways")


def test_home_sets_homed():
    """homed is false until a return to origin completes."""
    seq, plc = make()
    assert not seq.homed
    seq.home()
    assert seq.homed
    assert plc.calls == [("home", False)]


def test_air_purge_records_last_command():
    """The PLC does not report the valve, so the last command is remembered."""
    seq, plc = make()
    assert seq.air_purge is None
    seq.set_air_purge(True)
    assert seq.air_purge is True and plc.calls == [("purge", True)]
