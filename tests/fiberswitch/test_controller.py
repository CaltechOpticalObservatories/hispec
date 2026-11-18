"""Tests for the controller's policy, state, jobs and orchestration, with fakes."""

import threading

import pytest

from hispec.fiberswitch.controller import FiberSwitchController
from hispec.fiberswitch.jobs import ABORTED, OK, JobAborted, JobRunner
from hispec.fiberswitch.policy import ConnectionPolicy, ControllerState
from hispec.fiberswitch.switch import Position


# Policy and state

def test_policy_validation():
    """Bad values and unknown fields are refused; ints are accepted for floats."""
    policy = ConnectionPolicy().updated({"clean_threshold": 0, "inspect_interval_h": 12})
    assert policy.clean_threshold == 0.0 and policy.inspect_interval_h == 12.0
    with pytest.raises(ValueError, match="unknown policy fields"):
        policy.updated({"cleanliness": 1})
    with pytest.raises(ValueError, match="clean_mode"):
        policy.updated({"clean_mode": "scrub"})
    with pytest.raises(ValueError, match="inspect_position is required"):
        policy.updated({"inspect": "always"})


def test_state_persists_overrides_and_history(tmp_path):
    """Overrides and history survive a reload; {} resets to the config."""
    path = tmp_path / "state.json"
    inputs = {"group1": {"inspect_position": "inspect1"}}
    state = ControllerState(path, {"max_clean_attempts": 1}, inputs)
    state.update_policy("group1", {"inspect": "always"})
    state.record("group1", last_dirt=0.2)
    state.set_alert("dirty")

    reloaded = ControllerState(path, {"max_clean_attempts": 1}, inputs)
    assert reloaded.policy("group1").inspect == "always"
    assert reloaded.policy("group1").max_clean_attempts == 1
    assert reloaded.history("group1")["last_dirt"] == 0.2
    assert reloaded.alert == "dirty"

    reloaded.update_policy("group1", {})
    assert reloaded.policy("group1").inspect == "never"


def test_state_drops_saved_overrides_the_config_no_longer_allows(tmp_path):
    """A saved override made invalid by a config change is dropped, not fatal."""
    path = tmp_path / "state.json"
    state = ControllerState(path, {}, {"group1": {"inspect_position": "inspect1"}})
    state.update_policy("group1", {"inspect": "always"})
    reloaded = ControllerState(path, {}, {"group1": {}})
    assert reloaded.policy("group1").inspect == "never"
    assert reloaded.dropped and "inspect_position" in reloaded.dropped[0]


def test_invalid_update_is_not_saved(tmp_path):
    """A rejected policy change leaves the old policy in place."""
    state = ControllerState(tmp_path / "s.json", {}, {"group1": {}})
    with pytest.raises(ValueError):
        state.update_policy("group1", {"clean_threshold": 2})
    assert state.policy("group1").clean_threshold == 0.005


# Jobs

def test_job_runner_outcomes():
    """A job reports ok, its error, or aborted; a second job is refused while busy."""
    runner = JobRunner()
    gate = threading.Event()
    runner.start("wait", lambda cancel: gate.wait(5))
    assert runner.busy and runner.state == "wait"
    with pytest.raises(RuntimeError, match="busy with wait"):
        runner.start("other", lambda cancel: None)
    gate.set()
    assert runner.wait(5) and runner.status == OK and runner.state == "idle"

    def fail(_):
        raise ValueError("nope")
    runner.start("fail", fail)
    runner.wait(5)
    assert runner.status == "error: nope"

    def until_cancelled(cancel):
        cancel.wait(5)
        raise JobAborted("stopped")
    runner.start("abortable", until_cancelled)
    runner.abort()
    runner.wait(5)
    assert runner.status == ABORTED and runner.job_id == 3


# Orchestration

class FakeSequencer:
    """Records the switch operations the controller asks for."""

    def __init__(self):
        self.commands = []

    def connect(self, position, cancel=None):  # pylint: disable=unused-argument
        """Record a connect."""
        self.commands.append(("connect", position.name))

    def clean(self, mode, cancel=None):  # pylint: disable=unused-argument
        """Record a clean."""
        self.commands.append(("clean", mode))


class FakeCamera:
    """Returns a scripted series of dirt values from inspect."""

    def __init__(self, dirts, found=True):
        self.dirts = list(dirts)
        self.found = found
        self.settings = {}
        self.tags = []
        self.thresholds = []

    def inspect(self, tag, cancel=None, max_defect_area_fraction=None):  # pylint: disable=W0613
        """Run an inspection."""
        self.tags.append(tag)
        self.thresholds.append(max_defect_area_fraction)
        return {"image": f"/archive/{tag}-{len(self.tags)}.png", "dirt": self.dirts.pop(0),
                "region": {"cx": 1, "cy": 1, "r": 1} if self.found else None}

    def set_setting(self, name, value):
        """Apply a camera setting."""
        self.settings[name] = value


class Now:  # pylint: disable=too-few-public-methods
    """A settable epoch clock."""

    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


GROUPS = {"group1": Position("group1", 1, 1)}
INSPECTION = {"inspect1": Position("inspect1", 13, 1)}


def make_controller(tmp_path, dirts=(0.0,), found=True, **policy):
    """A controller over fakes with one input, group1."""
    state = ControllerState(tmp_path / "state.json", {},
                            {"group1": {"inspect_position": "inspect1", **policy}})
    switch, camera, now = FakeSequencer(), FakeCamera(dirts, found), Now()
    ctl = FiberSwitchController(switch, camera, state, input_groups=GROUPS,
                                inspection_positions=INSPECTION, clock=now)
    return ctl, switch, camera, now


def test_clean_fiber_is_inspected_once(tmp_path):
    """A clean fiber end needs no cleaning and raises no alert."""
    ctl, switch, camera, _ = make_controller(tmp_path, dirts=[0.001])
    record = ctl.inspect_and_clean("group1")
    assert record["dirt"] == 0.001
    assert switch.commands == [("connect", "inspect1")]
    assert camera.tags == ["group1"]
    assert camera.thresholds == [0.01]  # the policy's alert threshold
    assert ctl.state.alert == ""
    history = ctl.state.history("group1")
    assert history["last_passed"] is True and history["last_image"] == record["image"]


def test_dirty_fiber_is_cleaned_until_clean(tmp_path):
    """Dirt above clean_threshold is cleaned and re-inspected."""
    ctl, switch, _, _ = make_controller(tmp_path, dirts=[0.05, 0.001])
    ctl.inspect_and_clean("group1")
    assert switch.commands == [("connect", "inspect1"), ("clean", "both"),
                               ("connect", "inspect1")]
    assert ctl.state.alert == ""
    assert ctl.state.history("group1")["last_clean"] is not None


def test_stays_dirty_alerts_after_max_attempts(tmp_path):
    """Dirt still above alert_threshold after the last clean raises an alert."""
    ctl, switch, _, _ = make_controller(tmp_path, dirts=[0.05, 0.05, 0.05],
                                        max_clean_attempts=2)
    ctl.inspect_and_clean("group1")
    assert [c for c in switch.commands if c[0] == "clean"] == [("clean", "both")] * 2
    assert "group1: dirt 0.0500 above alert threshold" in ctl.state.alert
    assert ctl.state.history("group1")["last_passed"] is False


def test_fiber_not_found_alerts_without_cleaning(tmp_path):
    """No fiber end in the image is an alert, not a reason to clean."""
    ctl, switch, _, _ = make_controller(tmp_path, dirts=[0.0], found=False)
    ctl.inspect_and_clean("group1")
    assert ("clean", "both") not in switch.commands
    assert "fiber end not found" in ctl.state.alert


def test_camera_settings_are_applied_first(tmp_path):
    """The policy's camera settings are written before inspecting."""
    ctl, _, camera, _ = make_controller(tmp_path, camera={"gain": 4})
    ctl.inspect_and_clean("group1")
    assert camera.settings == {"gain": 4.0}


def test_select_inspects_only_when_due(tmp_path):
    """interval inspects on the first select and again once the interval passes."""
    ctl, switch, camera, now = make_controller(tmp_path, dirts=[0.0, 0.0],
                                               inspect="interval", inspect_interval_h=1)
    ctl.select_input("group1")
    assert camera.tags == ["group1"]
    assert switch.commands[-1] == ("connect", "group1")
    assert ctl.state.selected == "group1"

    now.t += 1800
    ctl.select_input("group1")
    assert len(camera.tags) == 1

    now.t += 1800
    ctl.select_input("group1")
    assert len(camera.tags) == 2


def test_select_cleans_on_its_interval(tmp_path):
    """clean_interval_h cleans before connecting when it has elapsed."""
    ctl, switch, _, _ = make_controller(tmp_path, clean_interval_h=24)
    ctl.select_input("group1")
    assert switch.commands == [("clean", "both"), ("connect", "group1")]
    ctl.select_input("group1")
    assert switch.commands[-1] == ("connect", "group1")
    assert switch.commands.count(("clean", "both")) == 1


def test_take_reference(tmp_path):
    """A reference image is stored without touching the inspection history."""
    ctl, _, camera, _ = make_controller(tmp_path)
    record = ctl.take_reference("group1")
    assert camera.tags == ["group1-reference"]
    history = ctl.state.history("group1")
    assert history["reference_image"] == record["image"]
    assert "last_inspect" not in history


def test_inspect_needs_a_position():
    """An input without inspect_position cannot be inspected."""
    state = ControllerState(None, {}, {"group1": {}})
    ctl = FiberSwitchController(FakeSequencer(), FakeCamera([0.0]), state,
                                input_groups=GROUPS, inspection_positions=INSPECTION)
    with pytest.raises(ValueError, match="no inspect_position"):
        ctl.inspect_and_clean("group1")
