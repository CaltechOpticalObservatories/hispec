import unittest
from unittest.mock import MagicMock, patch
from ..communication import Communication


class MockAxis:
    def __init__(self):
        self.received_data = []

    def receive_data(self, data):
        self.received_data.append(data)


class MockXeryon:
    def __init__(self):
        self.axis_list = [MockAxis()]

    def get_axis(self, letter):
        return self.axis_list[0]


class TestCommunication(unittest.TestCase):

    @patch('serial.Serial')
    def test_start_sets_up_serial_connection(self, mock_serial_class):
        mock_serial = MagicMock()
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        mock_xeryon = MockXeryon()

        comm = Communication(mock_xeryon, 'COM3', 115200)
        comm.start()

        mock_serial_class.assert_called_with(
            'COM3', 115200, timeout=1, xonxoff=True)
        mock_serial.flush.assert_called()
        mock_serial.flushInput.assert_called()
        mock_serial.flushOutput.assert_called()

    def test_send_command_queues_command(self):
        mock_xeryon = MockXeryon()
        comm = Communication(mock_xeryon, 'COM3', 115200)
        comm.send_command("DPOS=100")

        self.assertEqual(comm.readyToSend, ["DPOS=100"])

    @patch('serial.Serial')
    def test_process_data_reads_and_dispatches(self, mock_serial_class):
        mock_serial = MagicMock()
        mock_serial.readline.return_value = b'X:DPOS=1000\n'
        mock_serial.in_waiting = 1
        mock_serial_class.return_value = mock_serial

        mock_xeryon = MockXeryon()
        comm = Communication(mock_xeryon, 'COM3', 115200)
        comm.ser = mock_serial
        comm.readyToSend = ["X:MOVE=1"]

        comm._Communication__process_data(external_while_loop=True)

        self.assertIn("DPOS=1000\n", mock_xeryon.axis_list[0].received_data)
        mock_serial.write.assert_called_with(b"X:MOVE=1\n")


if __name__ == '__main__':
    unittest.main()
