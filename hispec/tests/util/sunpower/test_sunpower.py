import unittest
import asyncio
from unittest.mock import patch
from hispec.util import SunpowerCryocooler

class TestSunpowerController(unittest.TestCase):
    @patch('hispec.util.sunpower.sunpower_controller.io.TextIOWrapper')
    @patch('hispec.util.sunpower.sunpower_controller.io.BufferedRWPair')
    @patch('hispec.util.sunpower.sunpower_controller.serial.Serial')
    def setUp(self, mock_serial, mock_buffered, mock_textio):
        self.mock_serial = mock_serial.return_value
        self.mock_buffered = mock_buffered.return_value
        self.mock_textio = mock_textio.return_value
        self.controller = SunpowerCryocooler(port='COM1', baudrate=19200, quiet=False)

    def test_send_command(self):
        self.controller._send_command('TEST')
        self.mock_serial.write.assert_called_with(b'TEST\r')
        self.mock_textio.flush.assert_called_once()

    def test_read_reply_parses_float(self):
        self.mock_serial.readline.side_effect = [
            b'TTARGET= 123.456\n', b'\n'
        ]
        with patch.object(self.controller.logger, 'info') as mock_info:
            self.controller._read_reply()
            mock_info.assert_any_call('TTARGET: 123.456')

    def test_read_reply_handles_non_float(self):
        self.mock_serial.readline.side_effect = [
            b'ERROR= notanumber\n', b'\n'
        ]
        with patch.object(self.controller.logger, 'warning') as mock_warn:
            self.controller._read_reply()
            mock_warn.assert_called_with('Failed to parse value: ERROR= notanumber')

    def test_get_commanded_power(self):
        with patch.object(self.controller, '_send_and_read') as mock_send_and_read:
            asyncio.run(self.controller.get_commanded_power())
            mock_send_and_read.assert_called_once_with('PWOUT')

    def test_set_commanded_power(self):
        with patch.object(self.controller, '_send_and_read') as mock_send_and_read:
            asyncio.run(self.controller.set_commanded_power(12.34))
            mock_send_and_read.assert_called_once_with('PWOUT=12.34')

    def test_get_reject_temp(self):
        with patch.object(self.controller, '_send_and_read') as mock_send_and_read:
            asyncio.run(self.controller.get_reject_temp())
            mock_send_and_read.assert_called_once_with('TEMP RJ')

    def test_get_cold_head_temp(self):
        with patch.object(self.controller, '_send_and_read') as mock_send_and_read:
            asyncio.run(self.controller.get_cold_head_temp())
            mock_send_and_read.assert_called_once_with('TC')

if __name__ == '__main__':
    unittest.main()