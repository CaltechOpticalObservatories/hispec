
import pytest
pytestmark = pytest.mark.unit
@pytest.mark.unit
import unittest
from unittest.mock import patch, MagicMock
# pylint: disable=import-error,no-name-in-module
from smc8 import SMC
import time

class TestSMC8(unittest.TestCase):
    """Unit tests for the SunpowerCryocooler class."""
    
    @patch("socket.socket", autospec=True)
    def setUp(self, mock_ximc_obj): # pylint: disable=arguments-differ
        """Set up the test case with a mocked ximc connection."""
        self.mock_ximc = MagicMock()
        mock_ximc_obj.return_value = self.mock_ximc
        self.mock_ximc.read.return_value = b""
        self.controller = SMC(ip="123.456.789.101", port=1234, log=False)
        self.controller.axis  = self.mock_ximc
        self.mock_ximc.get_serial_number.return_value = 12345678
        self.mock_ximc.get_power_setting.return_value = 1
        self.mock_ximc.get_device_information.return_value = 5000
        self.mock_ximc.command_read_settings.return_value = 1000
        self.mock_ximc.command_homezero.return_value = True
        self.mock_ximc.get_position_calb.return_value = 0 , "0.0"

    def test_info(self):
        """Test getting the info from the attenuator."""
        assert self.controller.get_info()
        assert self.controller.serial_number is not None
        assert self.controller.power_setting is not None
        assert self.controller.device_information is not None
        assert self.controller.command_read_setting is not None
    

    def test_abs_move(self):
        """Testing sending the correct commands to abs move the SMC."""
        with patch.object(self.controller.axis, "command_move_calb") as mock_move:
            self.controller.axis.get_position_calb = MagicMock(return_value={Error = None, Position = 10.0,Moving = True})
            self.controller.move_abs(10)
            assert mock_move.assert_called_once_with(10)
    
    def test_rel_move(self):
        """Testing sending the correct commands to rel move the SMC."""
        with patch.object(self.controller.axis, "command_movr_calb") as mock_move:
            self.controller.axis.get_position_calb = MagicMock(return_value={Error = None, Position = 10.0,Moving = False})
            self.controller.move_rel(10)
            assert mock_move.assert_called_once_with(10)

    def test_home(self):
        """Test setting the position from the SMC."""
        with patch.object(self.controller.axis, "command_homezero") as mock_home:
            mock_home.assert_called_once()

    def test_get_position(self):
        """Test getting the position from the SMC."""
        self.controller.axis.get_position_calb = MagicMock(return_value={Error = None, Position = 10.0,Moving = False})
        position = self.controller.get_position().Position
        assert position == 10.0

    def test_get_status(self):
        """Test getting the status from the SMC."""
        self.controller.axis.get_status_calb = MagicMock(return_value={Error = None, Status = 0, Position = 10.0,Moving = False })
        status = self.controller.get_status().Status
        Error = self.controller.get_status().Error
        Position = self.controller.get_status().Position
        Moving = self.controller.get_status().Moving
        assert status is not None
        assert Error is None
        assert Position is not None
        assert Moving is not None


if __name__ == "__main__":
    unittest.main()