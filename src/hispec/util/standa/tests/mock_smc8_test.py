#################
#Unit test
#Description: Validate software functions are correctly implemented via mocking
#################

import pytest
pytestmark = pytest.mark.unit
import unittest
from unittest.mock import patch, MagicMock
# pylint: disable=import-error,no-name-in-module
from smc8 import SMC
import time
import ctypes

class TestSMC8(unittest.TestCase):
    """Unit tests for the SunpowerCryocooler class."""
    
    def setUp(self): # pylint: disable=arguments-differ
        """Set up the test case with a mocked ximc connection."""
        patcher = patch("smc8.ximc.Axis")  # <- patch the right function
        self.addCleanup(patcher.stop)
        mock_open_device = patcher.start()
        self.mock_ximc = MagicMock()
        mock_open_device.return_value = self.mock_ximc
        self.controller = SMC(device_connection = "192.168.29.123/9219", connection_type = "xinet", log = False)
        self.controller._axis  = self.mock_ximc
        self.controller.dev_open = True
        self.controller.min_limit = -500
        self.controller.max_limit = 500
        self.mock_ximc.get_serial_number.return_value = 12345678
        self.mock_ximc.get_power_setting.return_value = 1
        self.mock_ximc.get_device_information.return_value = 5000
        self.mock_ximc.command_homezero.return_value = True
        self.mock_ximc.get_position_calb.return_value = 0 , "0.0"
        self.mock_ximc.Position = 10
        self.mock_ximc.CurPosition = 10
        self.mock_ximc.CurSpeed = 0.12

    def test_info(self):
        """Test getting the info from the attenuator."""
        assert self.controller.get_info()
        assert self.controller.serial_number is not None
        assert self.controller.power_setting is not None
        assert self.controller.device_information is not None
    

    def test_abs_move(self):
        """Testing sending the correct commands to abs move the SMC."""
        mock_axis = MagicMock()
        self.controller._axis = mock_axis  # inject the mock axis

        self.controller.move_abs(10)
        mock_axis.command_move.assert_called_once_with(10,0)
    
    def test_rel_move(self):
        """Testing sending the correct commands to rel move the SMC."""
        mock_axis = MagicMock()
        self.controller._axis = mock_axis  # inject the mock axis
        self.controller.get_position = MagicMock(return_value=0)

        self.controller.move_rel(10)
        mock_axis.command_movr.assert_called_once_with(10,0)

    def test_home(self):
        """Test setting the position from the SMC."""
        with patch.object(self.controller._axis, "command_homezero") as mock_home:
            self.controller.home()
            mock_home.assert_called_once()

    def test_get_position(self):
        """Test getting the position from the SMC."""
        self.controller._axis.get_position = MagicMock(return_value=self.mock_ximc)
        pos = self.controller.get_position()
        assert pos == 10

    def test_get_status(self):
        """Test getting the status from the SMC."""
        self.controller._axis.get_status = MagicMock(return_value=self.mock_ximc)
        status = self.controller.status()
        Position = status.CurPosition
        Moving_speed = status.CurSpeed
        assert Position is not None


if __name__ == "__main__":
    unittest.main()
    