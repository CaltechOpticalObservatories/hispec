"""Test suite for Xeryon utility functions."""
# pylint: disable=import-error,no-name-in-module
from xeryon.utils import get_actual_time, get_dpos_epos_string


def test_get_actual_time_returns_int():
    """Test that get_actual_time returns an integer."""
    timestamp = get_actual_time()
    assert isinstance(timestamp, int)


def test_get_dpos_epos_string_format():
    """Test that get_dpos_epos_string formats the string correctly."""
    dpos, epos, unit = 123, 456, 'mm'
    result = get_dpos_epos_string(dpos, epos, unit)
    assert result == "DPOS: 123 mm and EPOS: 456 mm"
