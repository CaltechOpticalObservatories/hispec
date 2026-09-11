"""Tests for the FEI subsystem API."""
import pytest

from hispec.api import DeviceError, ProcedureTimeout
from hispec.api.fei import devices


def test_axis_names_come_from_the_device_configs(fei):
    """Axis names are derived from config/hsfei, not hard-coded."""
    assert set(fei.axis_names()) == {
        "atcl", "atcp", "feipo", "lsm_h", "lsm_v", "ms_h", "ms_v"}


def test_pi_axis_resolves_the_device_key(fei):
    """An axis carries everything a PI driver call needs."""
    axis = fei.pi_axis("ms_h")
    assert axis.device == devices.MS
    # Address, port and chain position all come from hsfei_ms.yaml.
    assert axis.device_key == ("192.168.29.100", 10005, 2)
    assert axis.axis == "1"
    assert axis.units == "mm"


def test_unknown_axis_lists_the_real_ones(fei):
    """Asking for an axis that does not exist names the ones that do."""
    with pytest.raises(KeyError) as excinfo:
        fei.pi_axis("no_such_axis")
    assert "ms_h" in str(excinfo.value)


def test_move_axes_commands_every_axis_before_waiting(fei, fake_drivers):
    """Axes on one controller are commanded together, not in series."""
    result = fei.move_axes({"ms_h": 1.0, "ms_v": 2.0})
    moves = [call for call in fake_drivers[devices.MS].calls
             if call[0] == "set_pos"]
    assert [(call[2], call[3]) for call in moves] == [(1.0, False), (2.0, False)]
    assert result == {"ms_h": 1.0, "ms_v": 2.0}


def test_move_axes_raises_when_the_controller_refuses(fei, fake_drivers):
    """A rejected move is an error, not a silent no-op."""
    fake_drivers[devices.MS].refuse_moves = True
    with pytest.raises(DeviceError):
        fei.move_axes({"ms_h": 1.0})


def test_move_axes_times_out_while_an_axis_still_moves(fei, fake_drivers):
    """An axis that never stops raises instead of returning early."""
    pi = fake_drivers[devices.MS]
    pi.moving.add((("192.168.29.100", 10005, 2), "1"))
    with pytest.raises(ProcedureTimeout):
        fei.move_axes({"ms_h": 1.0}, timeout_s=0.05)


def test_move_axes_can_skip_the_wait(fei):
    """A non-blocking move commands the axis and returns."""
    assert fei.move_axes({"feipo": 3.0}, wait=False) == {"feipo": 3.0}


def test_named_positions_come_from_config(fei):
    """A named move uses the positions the daemon config defines."""
    assert fei.pi_axis("feipo").named_target("science") == 12.5
    assert fei.move_to_named(devices.FEIPO, "deployed") == {"feipo": 25.0}


def test_unknown_named_position_lists_the_configured_ones(fei):
    """A typo in a position name reports what is actually configured."""
    with pytest.raises(KeyError) as excinfo:
        fei.select_mask("slot_99")
    assert "slot_1" in str(excinfo.value)


def test_select_mask_moves_both_axes(fei):
    """The mask selector's two axes are both driven by one call."""
    assert set(fei.select_mask("slot_1")) == {"ms_h", "ms_v"}


def test_move_adc_commands_both_prisms_first(fei, fake_drivers):
    """Both ADC prisms are commanded before either wait starts."""
    assert fei.move_adc(10.0, -10.0) == {1: 10.0, 2: -10.0}
    assert fake_drivers[devices.ADC].calls == [
        ("move_abs", 1, 10.0, False), ("move_abs", 2, -10.0, False)]


def test_move_adc_raises_when_a_prism_refuses(fei, fake_drivers):
    """A refused prism move is reported, not ignored."""
    fake_drivers[devices.ADC].refuse_moves = True
    with pytest.raises(DeviceError):
        fei.move_adc(0.0, 0.0)


def test_home_all_skips_axes_already_referenced(fei, fake_drivers):
    """An axis that reports homed is left alone."""
    pi = fake_drivers[devices.FEIPO]
    pi.homed.add((("192.168.29.100", 10001, 1), "1"))
    assert fei.home_all(["feipo"]) == {"feipo": None}
    assert not [call for call in pi.calls if call[0] == "home"]


def test_home_all_covers_every_axis_and_the_adc(fei, fake_drivers):
    """Homing the subsystem reaches the PI axes and both ADC prisms."""
    results = fei.home_all()
    assert set(results) == set(fei.axis_names()) | {"adc1", "adc2"}
    assert all(error is None for error in results.values())
    assert fake_drivers[devices.ADC].calls == [("home", 1), ("home", 2)]


def test_home_all_records_failures_and_keeps_going(fei, fake_drivers):
    """One controller refusing to home does not stop the others."""
    def refuse(*_args, **_kwargs):
        raise OSError("controller offline")
    fake_drivers[devices.MS].home = refuse

    results = fei.home_all(["ms_h", "feipo"])
    assert results["ms_h"] == "controller offline"
    assert results["feipo"] is None


def test_halt_all_hits_each_connected_controller_once(fei, fake_drivers):
    """Halting sends one halt per controller, not one per axis."""
    fei.halt_all()
    halts = [call for call in fake_drivers[devices.MS].calls
             if call[0] == "halt_motion"]
    assert len(halts) == 1


def test_halt_all_does_not_connect_anything(fake_drivers):
    """Halting an FEI with nothing connected touches no device."""
    from hispec.api.fei import FEI  # local: keeps the fixture out of this test
    FEI().halt_all()
    assert all(not getattr(driver, "calls", [])
               for driver in fake_drivers.values())


def test_temperatures_use_the_configured_sensor_keywords(fei):
    """Sensor names and channels both come from the Lakeshore config."""
    temps = fei.temperatures()
    # hsfei_atctherm.yaml maps channel A to tA_detector.
    assert temps["tA_detector"] == 40.0
    # A sensor the controller will not report is None, not an exception.
    assert temps["tC_g10"] is None


def test_status_is_tolerant_of_a_dead_device(fei, fake_drivers):
    """A snapshot reports what it could not read rather than raising."""
    def refuse(*_args, **_kwargs):
        raise OSError("gauge offline")
    fake_drivers[devices.ATCPRESS].read_pressure = refuse

    status = fei.status()
    assert status["pressures"]["gauge1"] is None
    assert status["cryo"]["cold_head_temp"] == 80.0
    assert set(status["positions"]) >= set(fei.axis_names())


def test_cooldown_starts_the_cooler_then_samples_until_target(fei, fake_drivers):
    """A cooldown commands the cooler, then polls to the target temperature."""
    cryo = fake_drivers[devices.ATCCRYO]
    cryo.cold_head_temps = [120.0, 90.0, 55.0]
    seen = []

    samples = fei.cooldown(56.0, tolerance_k=1.0, timeout_s=5.0, poll_s=0.01,
                           on_sample=seen.append)

    assert cryo.calls[:2] == [("set_target_temp", 56.0), ("turn_on_cooler",)]
    assert [s["cryo"]["cold_head_temp"] for s in samples] == [120.0, 90.0, 55.0]
    assert seen == samples


def test_cooldown_times_out_without_reaching_target(fei, fake_drivers):
    """A dewar that will not cool raises rather than waiting forever."""
    fake_drivers[devices.ATCCRYO].cold_head_temps = [300.0]
    with pytest.raises(ProcedureTimeout):
        fei.cooldown(50.0, timeout_s=0.05, poll_s=0.01)
