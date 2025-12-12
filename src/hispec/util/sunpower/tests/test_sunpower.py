"""Test suite for the SunpowerCryocooler class in hispec.util module."""
import unittest
from unittest.mock import patch
# pylint: disable=import-error,no-name-in-module
from sunpower import SunpowerCryocooler


class TestSunpowerController(unittest.TestCase):
    """Unit tests for the SunpowerCryocooler class."""

    @patch("serial.Serial")
    def setUp(self, mock_serial): # pylint: disable=arguments-differ
        """Set up the test case with a mocked serial connection."""
        self.mock_serial = mock_serial.return_value
        self.mock_serial.read.return_value = b""
        self.controller = SunpowerCryocooler(
            port="COM1", baudrate=19200, quiet=False, connection_type="serial"
        )

    def test_send_command(self):
        """Test sending a command to the cryocooler."""
        self.controller._send_command("TEST") # pylint: disable=protected-access
        self.mock_serial.write.assert_called_with(b"TEST\r")

    def test_read_reply_parses_float(self):
        """Test reading a reply and parsing a float value."""
        self.mock_serial.read.return_value = b"TTARGET= 123.456\r\n"
        with patch.object(self.controller.logger, "info") as mock_info:
            result = self.controller._read_reply() # pylint: disable=protected-access
            assert "TTARGET= 123.456" in result
            mock_info.assert_not_called()  # we don't log parsed floats directly anymore

    def test_read_reply_handles_non_float(self):
        """Test reading a reply that does not contain a float."""
        self.mock_serial.read.return_value = b"ERROR= notanumber\r\n"
        with patch.object(self.controller.logger, "warning") as mock_warn:
            result = self.controller._read_reply() # pylint: disable=protected-access
            assert "ERROR= notanumber" in result
            mock_warn.assert_not_called()  # no parse attempted anymore

    def test_get_commanded_power(self):
        """Test getting the commanded power from the cryocooler."""
        with patch.object(self.controller, "_send_and_read") as mock_send_and_read:
            self.controller.get_commanded_power()
            mock_send_and_read.assert_called_once_with("PWOUT")

    def test_set_commanded_power(self):
        """Test setting the commanded power on the cryocooler."""
        with patch.object(self.controller, "_send_and_read") as mock_send_and_read:
            self.controller.set_commanded_power(12.34)
            mock_send_and_read.assert_called_once_with("PWOUT=12.34")

    def test_get_reject_temp(self):
        """Test getting the reject temperature from the cryocooler."""
        with patch.object(self.controller, "_send_and_read") as mock_send_and_read:
            self.controller.get_reject_temp()
            mock_send_and_read.assert_called_once_with("TEMP RJ")

    def test_get_cold_head_temp(self):
        """Test getting the cold head temperature from the cryocooler."""
        with patch.object(self.controller, "_send_and_read") as mock_send_and_read:
            self.controller.get_cold_head_temp()
            mock_send_and_read.assert_called_once_with("TC")

    def test_get_measured_power_returns_p_and_value(self):
        """Test getting the measured power from the cryocooler."""
        with patch.object(
                self.controller, "_send_and_read", return_value=["P", "72"]
        ) as mock_send_and_read:
            result = self.controller.get_measured_power()
            self.assertEqual(result, ["P", "72"])
            mock_send_and_read.assert_called_once_with("P")


if __name__ == "__main__":
    unittest.main()
