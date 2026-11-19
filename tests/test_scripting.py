"""Tests for hispec.scripting, against an in-memory stand-in for the bus."""
# pylint: disable=redefined-outer-name,missing-function-docstring,unused-argument
from typing import Any, Dict, List, Optional

import pytest
from libby import Client, KeywordError, LibbyTimeout

from hispec import scripting
from hispec.fei import ATCFW, ATCL, MS_H, MS_V
from hispec.scripting import MoveError, NotReady


class FakeClient(Client):
    """A Client whose keywords live in a dict.

    Writing a stage's ``positionvalue`` starts a simulated move: its
    ``ismoving`` reads true for ``move_reads`` reads, then false, and the
    position becomes the target plus ``overshoot``. ``wait_for_result`` is
    the real one, so it is exercised against these reads.
    """

    def __init__(self, values: Optional[Dict[str, Any]] = None) -> None:
        # pylint: disable=super-init-not-called
        self.values: Dict[str, Any] = dict(values or {})
        self.writes: List[tuple] = []
        self.refuse: Dict[str, str] = {}
        self.move_reads = 2
        self.overshoot = 0.0
        self._moving: Dict[str, int] = {}

    def get(self, name: str, *, timeout_s: float = 3.0) -> Any:
        if name in self._moving:
            self._moving[name] -= 1
            if self._moving[name] >= 0:
                return True
            del self._moving[name]
        if name not in self.values:
            raise KeywordError(name, "unknown keyword")
        return self.values[name]

    def set(self, name: str, value: Any, *, timeout_s: Optional[float] = None) -> Any:
        if name in self.refuse:
            raise KeywordError(name, self.refuse[name])
        self.writes.append((name, value))
        if ".positionvalue" in name:
            self.values[name] = value + self.overshoot
            moving = name.replace(".positionvalue", ".ismoving")
            if moving in self.values:
                self._moving[moving] = self.move_reads
        return value

    def read(self, names, *, timeout_s: float = 3.0, chunk_size: int = 100):
        replies = {}
        for name in names:
            if name in self.values:
                replies[name] = {"ok": True, "value": self.values[name]}
            else:
                replies[name] = {"ok": False, "error": "no reply"}
        return replies

    def close(self) -> None:
        pass


@pytest.fixture
def client():
    """Connected, homed FEI stages sitting at zero."""
    return FakeClient({
        "hsfei.ms.isconnected": True,
        "hsfei.ms.isreferencedh": True,
        "hsfei.ms.isreferencedv": True,
        "hsfei.ms.positionvalueh": 0.0,
        "hsfei.ms.positionvaluev": 0.0,
        "hsfei.ms.ismovingh": False,
        "hsfei.ms.ismovingv": False,
        "hsfei.ms.lasterror": "",
        "hsfei.atcl.isconnected": True,
        "hsfei.atcl.isreferenced": True,
        "hsfei.atcl.positionvalue": 0.0,
        "hsfei.atcl.ismoving": False,
        "hsfei.atcl.lasterror": "",
        "hsfei.atcfw.isconnected": True,
        "hsfei.atcfw.positionvalue": 1,
    })


@pytest.fixture(autouse=True)
def fast_settle(monkeypatch):
    """Keep the settle window short so failing moves fail quickly."""
    monkeypatch.setattr(scripting, "SETTLE_S", 0.05)
    monkeypatch.setattr(scripting, "SETTLE_POLL_S", 0.01)


def test_stage_keywords_use_suffix():
    assert MS_H.position == "hsfei.ms.positionvalueh"
    assert MS_H.ismoving == "hsfei.ms.ismovingh"
    assert ATCL.position == "hsfei.atcl.positionvalue"
    assert MS_V.name == "hsfei.ms.v"
    assert ATCL.name == "hsfei.atcl"


def test_connect_uses_shared_broker_and_names_the_script(monkeypatch):
    seen = {}

    def fake_rabbitmq(**kwargs):
        seen.update(kwargs)
        return "client"

    monkeypatch.setattr(scripting, "broker_url", lambda: "amqp://broker")
    monkeypatch.setattr(scripting.Client, "rabbitmq", staticmethod(fake_rabbitmq))
    assert scripting.connect("psf-check") == "client"
    assert seen["rabbitmq_url"] == "amqp://broker"
    assert seen["self_id"].startswith("script-psf-check-")


def test_preflight_passes_when_ready(client):
    scripting.preflight(client, [MS_H, MS_V, ATCL, ATCFW])


def test_preflight_reports_every_problem(client):
    client.values["hsfei.ms.isconnected"] = False
    client.values["hsfei.atcl.isreferenced"] = False
    del client.values["hsfei.atcfw.isconnected"]
    with pytest.raises(NotReady) as excinfo:
        scripting.preflight(client, [MS_H, ATCL, ATCFW])
    message = str(excinfo.value)
    assert "hsfei.ms.isconnected is False" in message
    assert "hsfei.atcl.isreferenced is False" in message
    assert "hsfei.atcfw.isconnected: could not read" in message


def test_preflight_skips_isreferenced_for_filter_wheel(client):
    # The filter wheel registers no isreferenced keyword
    scripting.preflight(client, [ATCFW])


def test_move_waits_for_stop_and_returns_position(client):
    assert scripting.move_and_verify(client, ATCL, 7.15) == 7.15
    assert client.writes == [("hsfei.atcl.positionvalue", 7.15)]


def test_move_without_ismoving_does_not_wait(client):
    assert scripting.move_and_verify(client, ATCFW, 3) == 3
    assert "hsfei.atcfw.ismoving" not in client.values


def test_refused_move_raises_move_error(client):
    client.refuse["hsfei.atcl.positionvalue"] = "target 200 above softmax 100"
    with pytest.raises(MoveError, match="refused.*above softmax"):
        scripting.move_and_verify(client, ATCL, 200)


def test_move_out_of_tolerance_reports_lasterror(client):
    client.overshoot = 0.5
    client.values["hsfei.atcl.lasterror"] = "following error"
    with pytest.raises(MoveError, match="not within 0.001.*following error"):
        scripting.move_and_verify(client, ATCL, 7.15)


def test_move_that_never_stops_is_halted(client):
    client.move_reads = 10_000
    with pytest.raises(MoveError, match="still moving"):
        scripting.move_and_verify(client, ATCL, 7.15, timeout_s=0.05)
    assert ("hsfei.atcl.halt", True) in client.writes


def test_halt_all_fires_once_per_daemon_and_skips_filter_wheel(client):
    assert not scripting.halt_all(client, [MS_H, MS_V, ATCL, ATCFW])
    halts = [name for name, _ in client.writes]
    assert halts == ["hsfei.ms.halt", "hsfei.atcl.halt"]


def test_halt_all_keeps_going_past_a_failure(client):
    client.refuse["hsfei.ms.halt"] = "no reply"
    failures = scripting.halt_all(client, [MS_H, ATCL])
    assert len(failures) == 1 and failures[0].startswith("hsfei.ms")
    assert ("hsfei.atcl.halt", True) in client.writes


def test_wait_survives_a_timeout_read(client, monkeypatch):
    # A daemon restarting mid-wait answers one read with a timeout
    real_get = FakeClient.get
    calls = {"n": 0}

    def flaky_get(self, name, *, timeout_s=3.0):
        calls["n"] += 1
        if name.endswith("ismoving") and calls["n"] == 2:
            raise LibbyTimeout("no reply")
        return real_get(self, name, timeout_s=timeout_s)

    monkeypatch.setattr(FakeClient, "get", flaky_get)
    assert scripting.move_and_verify(client, ATCL, 7.15) == 7.15
