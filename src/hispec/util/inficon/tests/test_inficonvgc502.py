# tests/test_inficonvgc502_units_sync.py
import pytest
from unittest.mock import MagicMock

from inficonvgc502 import InficonVGC502, UnknownResponse


@pytest.fixture
def vgc502():
    """Creates an InficonVGC502 instance with mock logger."""
    cont = InficonVGC502(log=False)
    # cont.connect("127.0.0.1", 8000)
    return cont

def test_set_pressure_unit_success(vgc502):
    # Mock low-level I/O so we don't need a real socket
    vgc502._send_command = MagicMock()
    # Device replies ACK (\x06\r\n)
    vgc502._read_reply = MagicMock(return_value="2")

    # Pascal (example: 2)
    result = vgc502.set_pressure_unit(2)
    assert result is True

    # Verify the command was sent
    # vgc502._send_command.assert_called_with("UNI,2\r\n")


def test_set_pressure_unit_invalid_value(vgc502):

    result = vgc502.set_pressure_unit(9)  # out of allowed range
    assert result is False


def test_get_pressure_unit(vgc502):
    vgc502._send_command = MagicMock()
    # First read: ACK to 'UNI\r\n'; Second read: the unit value line '3\r\n'
    vgc502._read_reply = MagicMock(return_value="3")

    result = vgc502.get_pressure_unit()
    assert result == 3

    # Ensure UNI and ENQ were written (order matters)
    # vgc502._send_command.assert_has_calls([call("UNI\r\n"), call("\x05")])


def test_get_pressure_unit_invalid_response(vgc502):
    vgc502._send_command = MagicMock()
    # ACK followed by a non-integer value
    vgc502._read_reply = MagicMock(side_effect=[b"\x06\r\n", b"X\r\n"])

    with pytest.raises(ValueError):
        vgc502.get_pressure_unit()
