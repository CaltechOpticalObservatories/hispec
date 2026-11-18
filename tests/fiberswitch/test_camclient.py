"""Tests for CameraDaemonClient against a fake camera daemon reached by keyword."""

import json
import threading

import pytest

from hispec.fiberswitch.camclient import CameraDaemonClient, CameraDaemonError
from hispec.fiberswitch.jobs import ABORTED, ERROR_PREFIX, OK, JobAborted


class FakeCameraDaemon:  # pylint: disable=too-many-instance-attributes
    """A libby.Client stand-in that answers as the camera daemon's keywords do.

    An inspect job runs for `polls` busy reads, then finishes with `outcome`.
    """

    def __init__(self, polls=2, outcome=OK, record=None):
        self.polls = polls
        self.outcome = outcome
        self.record = record
        self.jobid = 4
        self.jobstatus = OK
        self.lastresult = {}
        self.applied = {}
        self.halted = False
        self.closed = False
        self._remaining = 0
        self._tag = None
        self.writes = []

    def get(self, name, timeout_s=None):  # pylint: disable=unused-argument
        """Read a keyword."""
        group, daemon, keyword = name.split(".")
        assert (group, daemon) == ("hsfibers", "fiberswitchredcam")
        if keyword == "busy":
            if self._remaining:
                self._remaining -= 1
                if not self._remaining:
                    self._finish()
                return True
            return False
        if keyword == "lastresult":
            return json.dumps(self.lastresult)
        return getattr(self, keyword)

    def set(self, name, value, timeout_s=None):  # pylint: disable=unused-argument
        """Write a keyword."""
        keyword = name.split(".")[-1]
        self.writes.append((keyword, value))
        if keyword == "settings":
            self.applied.update(json.loads(value))
        elif keyword == "inspect":
            request = json.loads(value)
            self._tag = request["tag"]
            self.jobid += 1
            self.jobstatus = "running"
            self._remaining = self.polls
            if not self._remaining:
                self._finish()
        elif keyword == "halt":
            self.halted = True
            self._remaining = 0
            self.jobstatus = ABORTED
        return value

    def close(self):
        """Close the connection."""
        self.closed = True

    def _finish(self):
        self.jobstatus = self.outcome
        if self.outcome == OK:
            self.lastresult = self.record or {"tag": self._tag, "image": f"/a/{self._tag}.png",
                                              "dirt": 0.002, "region": {"cx": 1}}


def make(fake, **kwargs):
    """A client on fake, polling without sleeping."""
    return CameraDaemonClient("hsfibers.fiberswitchredcam", lambda: fake, poll_s=0.0,
                              **kwargs)


def test_inspect_waits_for_the_job_and_returns_its_record():
    """inspect sends the tag and threshold, waits out busy and returns lastresult."""
    fake = FakeCameraDaemon(polls=3)
    record = make(fake).inspect("group1", max_defect_area_fraction=0.02)
    assert record["image"] == "/a/group1.png" and record["dirt"] == 0.002
    assert ("inspect", json.dumps({"tag": "group1", "max_dirt": 0.02})) in fake.writes


def test_set_setting_writes_settings():
    """A setting goes over as a one-entry JSON object of its raw value."""
    fake = FakeCameraDaemon()
    make(fake).set_setting("exposure", 5)
    assert fake.applied == {"exposure": 5.0}


def test_failed_inspection_raises_the_camera_daemons_error():
    """A job that ends in error raises it, without the error: prefix."""
    fake = FakeCameraDaemon(outcome=f"{ERROR_PREFIX}camera is not connected")
    with pytest.raises(CameraDaemonError, match="inspect group1: camera is not connected"):
        make(fake).inspect("group1")


def test_cancel_halts_the_camera_daemon():
    """A cancelled controller job halts the camera daemon's inspection."""
    fake = FakeCameraDaemon(polls=1000)
    cancel = threading.Event()
    original = fake.get

    def get(name, timeout_s=None):
        if name.endswith(".busy") and fake._remaining < 990:  # pylint: disable=W0212
            cancel.set()
        return original(name, timeout_s)

    fake.get = get
    with pytest.raises(JobAborted):
        make(fake).inspect("group1", cancel)
    assert fake.halted


def test_timeout_halts_and_raises():
    """An inspection still running at inspect_timeout_s is halted."""
    fake = FakeCameraDaemon(polls=1000)
    ticks = iter(range(1000))
    client = make(fake, inspect_timeout_s=5.0, clock=lambda: float(next(ticks)))
    with pytest.raises(CameraDaemonError, match="still running"):
        client.inspect("group1")
    assert fake.halted


def test_a_stale_result_is_refused():
    """A lastresult for another tag is not passed off as this inspection's."""
    fake = FakeCameraDaemon(record={"tag": "other", "image": "/a/other.png"})
    with pytest.raises(CameraDaemonError, match="did not report"):
        make(fake).inspect("group1")


def test_unreachable_broker_and_daemon():
    """A broker or camera daemon that cannot be reached is a CameraDaemonError."""
    def broken():
        raise OSError("connection refused")

    client = CameraDaemonClient("hsfibers.fiberswitchredcam", broken)
    with pytest.raises(CameraDaemonError, match="cannot reach the broker"):
        client.set_setting("gain", 1.0)
    assert not client.connected()

    fake = FakeCameraDaemon()
    fake.get = lambda name, timeout_s=None: (_ for _ in ()).throw(TimeoutError("timed out"))
    assert not make(fake).connected()


def test_close_closes_the_connection():
    """close releases the client's own libby connection."""
    fake = FakeCameraDaemon()
    client = make(fake)
    client.set_setting("gain", 1.0)
    client.close()
    assert fake.closed


def test_bad_daemon_name():
    """camera.daemon must be <group>.<daemon>."""
    with pytest.raises(ValueError, match="<group>.<daemon>"):
        CameraDaemonClient("fiberswitchredcam", lambda: None)
