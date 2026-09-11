"""Tests for the FEI subsystem API."""
import pytest

from hispec.api import MoveTimeout, PositionError
from hispec.api.fei import FEI, devices


def _motion_values(device="ms", suffix="h", position=0.0, moving=False,
                   referenced=True):
    """Keyword values for one idle motion axis."""
    return {
        f"hsfei.{device}.positionvalue{suffix}": position,
        f"hsfei.{device}.ismoving{suffix}": moving,
        f"hsfei.{device}.isreferenced{suffix}": referenced,
        f"hsfei.{device}.positionnamed{suffix}": "custom",
    }


def test_unknown_stage_lists_available(client_factory):
    """Asking for a stage that does not exist names the ones that do."""
    fei = FEI(client_factory())
    with pytest.raises(KeyError) as excinfo:
        fei.stage("no_such_stage")
    assert "ms_h" in str(excinfo.value)


def test_stage_handles_are_cached(client_factory):
    """The same stage name hands back the same handle."""
    fei = FEI(client_factory())
    assert fei.stage("ms_h") is fei.stage("ms_h")


def test_stage_suffix_matches_daemon_keywords(client_factory):
    """A multi-axis daemon's keywords carry the axis suffix."""
    fei = FEI(client_factory())
    assert fei.stage("ms_h").keyword("positionvalue") == "positionvalueh"
    assert fei.stage("adc1").keyword("positionvalue") == "positionvalue1"
    # A single-axis daemon has no suffix.
    assert fei.stage("feipo").keyword("positionvalue") == "positionvalue"


def test_move_waits_then_reads_back(client_factory):
    """A move commands the axis, waits for it to stop, and reports position."""
    client = client_factory(_motion_values())
    assert FEI(client).stage("ms_h").move(12.5) == 12.5
    assert ("hsfei.ms.positionvalueh", 12.5) in client.sets
    # Motion is given a chance to start before the wait for it to end.
    assert [expr for expr, _timeout, _svc in client.waits] == [
        "$ismovingh == true", "$ismovingh == false"]


def test_move_times_out_while_still_moving(client_factory):
    """An axis that never stops raises rather than returning silently."""
    client = client_factory(_motion_values(moving=True))
    with pytest.raises(MoveTimeout):
        FEI(client).stage("ms_h").move(5.0, timeout_s=0.01)


def test_move_detects_missed_target(client_factory):
    """Stopping away from the target raises when a tolerance is given."""
    client = client_factory(_motion_values(position=0.0),
                            frozen=("hsfei.ms.positionvalueh",))
    with pytest.raises(PositionError):
        FEI(client).stage("ms_h").move(5.0, tolerance=0.1)


def test_move_without_wait_only_commands(client_factory):
    """A non-blocking move writes the target and does not wait."""
    client = client_factory(_motion_values())
    assert FEI(client).stage("ms_h").move(3.0, wait=False) is None
    assert client.waits == []


def test_move_adc_commands_both_prisms_before_waiting(client_factory):
    """Both ADC prisms are commanded first, so they move together."""
    client = client_factory({**_motion_values("adc", "1"),
                             **_motion_values("adc", "2")})
    assert FEI(client).move_adc(10.0, -10.0) == {"adc1": 10.0, "adc2": -10.0}
    assert client.sets == [("hsfei.adc.positionvalue1", 10.0),
                           ("hsfei.adc.positionvalue2", -10.0)]


def test_home_all_skips_referenced_axes(client_factory):
    """An axis that is already referenced is left alone."""
    client = client_factory(_motion_values(referenced=True))
    results = FEI(client).home_all(["ms_h"])
    assert results == {"ms_h": None}
    assert client.sets == []


def test_home_all_records_failures_and_continues(client_factory):
    """One unreachable axis does not stop the others from homing."""
    client = client_factory(_motion_values("ms", "h", referenced=False))
    results = FEI(client).home_all(["ms_h", "feipo"])
    assert results["ms_h"] is None
    assert results["feipo"] is not None
    assert ("hsfei.ms.isreferencedh", True) in client.sets


def test_halt_all_hits_each_motion_daemon_once(client_factory):
    """Halting the subsystem triggers halt once per daemon, not per axis."""
    client = client_factory()
    FEI(client).halt_all()
    halted = [name for name, _value in client.sets]
    assert sorted(halted) == sorted(
        f"hsfei.{device}.halt" for device in
        {device for device, _suffix, _units in devices.STAGES.values()})


def test_temperatures_cover_every_configured_sensor(client_factory):
    """Every ATC dewar sensor is read, unreadable ones included."""
    client = client_factory({"hsfei.atctherm.tA_detector": 40.2})
    temps = FEI(client).temperatures()
    assert temps["tA_detector"] == 40.2
    assert set(temps) == set(devices.ATCTHERM_SENSORS)


def test_status_never_raises_on_a_dead_subsystem(client_factory):
    """A status snapshot of an unreachable FEI reports Nones, not errors."""
    status = FEI(client_factory()).status()
    assert set(status) == {"connected", "positions", "devices"}
    assert set(status["connected"]) == set(devices.DEVICES)
    assert all(value is None for value in status["positions"].values())
