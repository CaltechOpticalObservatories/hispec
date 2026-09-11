"""Tests for the subsystem API base class."""
import logging

import pytest

from hispec.api import ConfigError, DeviceSpec, ProcedureTimeout, SubsystemAPI
from hispec.api.base import resolve_config_dir


class _Fake(SubsystemAPI):
    """A subsystem whose one device is built from a recorded call."""

    group_id = "hsfei"
    DEVICE_SPECS = {
        "adc": DeviceSpec(lambda config, logger: {"config": config},
                          description="test device"),
    }


def test_group_id_required():
    """A subsystem without a group_id cannot be constructed."""
    with pytest.raises(ValueError):
        SubsystemAPI()


def test_missing_config_dir_says_where_it_looked():
    """A bad config directory names what was tried and how to fix it."""
    with pytest.raises(ConfigError) as excinfo:
        resolve_config_dir("hsnope", "/nonexistent/path")
    assert "HISPEC_CONFIG_DIR" in str(excinfo.value)


def test_config_is_read_from_the_group_directory():
    """Device config comes from config/<group>/<group>_<device>.yaml."""
    api = _Fake()
    assert api.config("adc")["peer_id"] == "adc"
    assert api.config_value("adc", "hardware.tcp_port") == 10006
    assert api.config_value("adc", "hardware.nope", "fallback") == "fallback"


def test_driver_is_built_once_and_cached():
    """A device connects on first use and is reused after that."""
    api = _Fake()
    assert api.driver("adc") is api.driver("adc")


def test_unknown_device_lists_the_real_ones():
    """Asking for a device that does not exist names the ones that do."""
    api = _Fake()
    with pytest.raises(KeyError) as excinfo:
        api.driver("nope")
    assert "adc" in str(excinfo.value)


def test_connect_reports_per_device_failures():
    """One failing device does not abort the sweep."""
    def explode(_config, _logger):
        raise OSError("no route to host")

    class _Broken(_Fake):
        DEVICE_SPECS = {
            "adc": _Fake.DEVICE_SPECS["adc"],
            "atccryo": DeviceSpec(explode),
        }

    results = _Broken().connect()
    assert results["adc"] is None
    assert results["atccryo"] == "no route to host"


def test_wait_until_returns_elapsed_time():
    """A condition already true returns immediately."""
    assert _Fake().wait_until(lambda: True, 1.0) == pytest.approx(0, abs=0.05)


def test_wait_until_times_out_with_a_description():
    """A condition that never holds raises, naming what was waited on."""
    with pytest.raises(ProcedureTimeout) as excinfo:
        _Fake().wait_until(lambda: False, 0.05, poll_s=0.01,
                           description="dewar cold")
    assert "dewar cold" in str(excinfo.value)


def test_collect_maps_failures_to_none(caplog):
    """A failing read costs that one value, not the whole snapshot."""
    def explode():
        raise OSError("device offline")

    with caplog.at_level(logging.WARNING):
        values = _Fake().collect({"good": lambda: 1, "bad": explode})
    assert values == {"good": 1, "bad": None}
    assert "device offline" in caplog.text


def test_attached_driver_is_used_instead_of_building_one():
    """An injected driver replaces the builder, for simulators and tests."""
    api = _Fake()
    sentinel = object()
    api.attach("adc", sentinel)
    assert api.driver("adc") is sentinel
