"""Tests for the subsystem API base class."""
import pytest
from libby import KeywordError

from hispec.api import SubsystemAPI


class _Fake(SubsystemAPI):
    """Minimal concrete subsystem for exercising the base class."""
    group_id = "hsfake"


def test_group_id_required(client_factory):
    """A subsystem without a group_id cannot be constructed."""
    with pytest.raises(ValueError):
        SubsystemAPI(client_factory())


def test_keyword_and_service_naming(client_factory):
    """Keywords qualify as <group>.<device>.<name>."""
    api = _Fake(client_factory())
    assert api.keyword("dev", "positionvalue") == "hsfake.dev.positionvalue"
    assert api.service("dev") == "hsfake.dev"


def test_trigger_writes_true(client_factory):
    """Firing a trigger keyword writes true to it."""
    client = client_factory()
    _Fake(client).trigger("dev", "halt")
    assert client.sets == [("hsfake.dev.halt", True)]


def test_read_many_tolerates_failures(client_factory):
    """An unreadable keyword maps to None instead of raising."""
    client = client_factory({"hsfake.dev.a": 1})
    values = _Fake(client).read_many("dev", ("a", "b"))
    assert values == {"a": 1, "b": None}


def test_get_still_raises(client_factory):
    """A single get is not tolerant; callers see the failure."""
    with pytest.raises(KeywordError):
        _Fake(client_factory()).get("dev", "missing")


def test_snapshot_nests_by_device(client_factory):
    """A snapshot returns one dict per device."""
    client = client_factory({"hsfake.a.x": 1, "hsfake.b.y": 2})
    snapshot = _Fake(client).snapshot({"a": ("x",), "b": ("y",)})
    assert snapshot == {"a": {"x": 1}, "b": {"y": 2}}


def test_borrowed_client_is_not_closed(client_factory):
    """Closing an API that borrowed a client leaves the client open."""
    client = client_factory()
    with _Fake(client):
        pass
    assert not client.closed
