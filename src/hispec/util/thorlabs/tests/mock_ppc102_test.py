#################
#Unit test
#Description: Validate software functions are correctly implemented via mocking
#################

import unittest
from unittest.mock import patch, MagicMock
# pylint: disable=import-error,no-name-in-module
from ppc102 import PPC102_Coms
import time
import pytest
pytestmark = pytest.mark.unit


class TestPPC102_Coms(unittest.TestCase):
    """Unit tests for the SunpowerCryocooler class."""
    
    @patch("socket.socket", autospec=True)
    def setUp(self, mock_socket_obj): # pylint: disable=arguments-differ
        """Set up the test case with a mocked socket connection."""
        self.mock_socket = MagicMock()
        mock_socket_obj.return_value = self.mock_socket
        self.mock_socket.read.return_value = b""
        self.controller = PPC102_Coms(ip="123.456.789.101", port=1234, log=False)
        self.controller.sock = self.mock_socket
        self.controller.get_loop()


    def test_send_command(self):
        """Test sending _get_infocommand to the controller."""
        with patch.object(self.controller, "write") as mock_write:
            with self.assertRaises(NotImplementedError):
                self.controller._get_info()#pylint: disable=protected-access
                mock_write.assert_called_with(bytes([0x05, 0x00, 0x00, 0x00, 0x11, 0x01]))  

    def test_get_loop(self):
        """Testing sending the correct bytes to get the loop status from the gimbal."""
        with patch.object(self.controller, "write") as mock_get_loop:
            self.controller.read_buff = MagicMock(return_value=bytes([0x41, 0x06, 0x01, 0x00, 0x21, 0x01, 0x02]))
            self.controller.get_loop(channel = 1)
            mock_get_loop.assert_called_with(bytes([0x41, 0x06, 0x01, 0x00, 0x21, 0x01]))
        

    def test_set_position(self):
        """Test setting the position from the Gimbal."""
        #make get_loop and get_enable return the correct responses using MagicMock
        with patch.object(self.controller, "write") as mock_setpos:
            self.controller.get_loop = MagicMock(return_value=2)
            self.controller.get_enable = MagicMock(return_value=1)
            self.controller.set_position(channel = 1, pos = 5.0)
            dest = (0x20 + 1) | 0x80 
            converted_pos = int(round((5.0 + 10)/20*32767))
            pos_bytes = converted_pos.to_bytes(2, byteorder='little', signed=False)
            mock_setpos.assert_called_with(bytes([0x46, 0x06, 0x04, 0x00,dest, 0x01,
                0x01, 0x00,pos_bytes[0], pos_bytes[1]]))



if __name__ == "__main__":
    unittest.main()