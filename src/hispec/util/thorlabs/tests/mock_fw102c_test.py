#################
#Unit test
#Description: Validate software functions are correctly implemented via mocking
#################

"""Test suite for the FilterWheel class in hispec.util module."""
import unittest
from unittest.mock import patch, MagicMock
from fw102c import FilterWheelController
import pytest
pytestmark = pytest.mark.unit


class TestFilterWheelController(unittest.TestCase):
    """Unit tests for the FilterWheelController class."""

    @patch("socket.socket")
    def setUp(self, mock_socket_obj): # pylint: disable=arguments-differ
        """Set up the test case with a mocked socket connection."""
        self.mock_socket = MagicMock()
        mock_socket_obj.return_value = self.mock_socket
        self.mock_socket.read.return_value = b""
        self.controller = FilterWheelController(log=False)
        self.controller.set_connection(ip="123.456.789.101", port=1234)
        self.controller.connected = True

    def test_get_position(self):
        """Test getting the position of the filter wheel."""
        with patch.object(self.controller, "command") as mock_command:
            self.controller.get_position()
            mock_command.assert_called_once_with("pos?")

    def test_set_position(self):
        """Test setting the position of the filter wheel."""
        with patch.object(self.controller, "command") as mock_command:
            mock_command.return_value = None
            with patch.object(self.controller, "get_position") as mock_getpos:
                mock_getpos.return_value = 10
                self.controller.initialized = True
                self.controller.move(target = 10)
                mock_command.assert_called_once_with("pos=10")



if __name__ == "__main__":
    unittest.main()