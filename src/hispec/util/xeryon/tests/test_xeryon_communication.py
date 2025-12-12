""" Mock classes to simulate the Xeryon environment for testing. """
import unittest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
# pylint: disable=import-error,no-name-in-module
from xeryon.communication import Communication


@dataclass
class MockAxis:
    """A mock class to simulate an axis in the Xeryon system."""
    def __init__(self):
        """Initialize the mock axis with an empty list to store received data."""
        self.received_data = []

    def receive_data(self, data):
        """Simulate receiving data by appending it to the received_data list."""
        self.received_data.append(data)


@dataclass
class MockXeryon:
    """A mock class to simulate the Xeryon system."""
    def __init__(self):
        self.axis_list = [MockAxis()]

    # pylint: disable=unused-argument
    def get_axis(self, letter):
        """Return the first axis for simplicity."""
        return self.axis_list[0]

class MockLogger:
    """A mock logger to capture log messages."""
    def __init__(self):
        """Initialize the mock logger with an empty list to store messages."""
        self.messages = []

    def info(self, msg):
        """Capture info messages."""
        self.messages.append(('info', msg))

    def debug(self, msg):
        """Capture debug messages."""
        self.messages.append(('debug', msg))

    def warning(self, msg):
        """Capture warning messages."""
        self.messages.append(('warning', msg))

    def error(self, msg):
        """Capture error messages."""
        self.messages.append(('error', msg))

    def critical(self, msg):
        """Capture critical messages."""
        self.messages.append(('critical', msg))

class TestCommunication(unittest.TestCase):
    """Unit tests for the Communication class in the Xeryon system."""

    @patch('serial.Serial')
    # pylint: disable=no-self-use
    def test_start_sets_up_serial_connection(self, mock_serial_class):
        """Test that the Communication class sets up the serial connection correctly."""
        mock_serial = MagicMock()
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        mock_xeryon = MockXeryon()

        comm = Communication(mock_xeryon, 'COM3', 115200, MockLogger())
        comm.start()

        mock_serial_class.assert_called_with(
            'COM3', 115200, timeout=1, xonxoff=True)
        mock_serial.flush.assert_called()
        mock_serial.flushInput.assert_called()
        mock_serial.flushOutput.assert_called()

    def test_send_command_queues_command(self):
        """Test that the send_command method queues a command."""
        mock_xeryon = MockXeryon()
        comm = Communication(mock_xeryon, 'COM3', 115200, MockLogger())
        comm.send_command("DPOS=100")

        self.assertEqual(comm.readyToSend, ["DPOS=100"])

    @patch('serial.Serial')
    def test_process_data_reads_and_dispatches(self, mock_serial_class):
        """Test that the __process_data method reads from serial and dispatches commands."""
        mock_serial = MagicMock()
        mock_serial.readline.return_value = b'X:DPOS=1000\n'
        mock_serial.in_waiting = 1
        mock_serial_class.return_value = mock_serial

        mock_xeryon = MockXeryon()
        comm = Communication(mock_xeryon, 'COM3', 115200, MockLogger())
        comm.ser = mock_serial
        comm.readyToSend = ["X:MOVE=1"]

        # pylint: disable=protected-access
        comm._Communication__process_data(external_while_loop=True)

        self.assertIn("DPOS=1000\n", mock_xeryon.axis_list[0].received_data)
        mock_serial.write.assert_called_with(b"X:MOVE=1\n")


if __name__ == '__main__':
    unittest.main()
