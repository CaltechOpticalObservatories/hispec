import unittest
from unittest.mock import patch, MagicMock
from hispec.util import SunpowerCryocooler


class TestSunpowerController(unittest.TestCase):

    @patch('hispec.util.sunpower.sunpower_controller.serial.Serial')
    def setUp(self, mock_serial):
        self.mock_serial = mock_serial.return_value
        self.mock_serial.read.return_value = b''
        self.controller = SunpowerCryocooler(
            port='COM1',
            baudrate=19200,
            quiet=False,
            connection_type='serial'
        )

    def test_send_command(self):
        self.controller._send_command('TEST')
        self.mock_serial.write.assert_called_with(b'TEST\r')

    def test_read_reply_parses_float(self):
        self.mock_serial.read.return_value = b'TTARGET= 123.456\r\n'
        with patch.object(self.controller.logger, 'info') as mock_info:
            result = self.controller._read_reply()
            assert 'TTARGET= 123.456' in result
            mock_info.assert_not_called()  # we don't log parsed floats directly anymore

    def test_read_reply_handles_non_float(self):
        self.mock_serial.read.return_value = b'ERROR= notanumber\r\n'
        with patch.object(self.controller.logger, 'warning') as mock_warn:
            result = self.controller._read_reply()
            assert 'ERROR= notanumber' in result
            mock_warn.assert_not_called()  # no parse attempted anymore

    def test_get_commanded_power(self):
        with patch.object(self.controller, '_send_and_read') as mock_send_and_read:
            self.controller.get_commanded_power()
            mock_send_and_read.assert_called_once_with('PWOUT')

    def test_set_commanded_power(self):
        with patch.object(self.controller, '_send_and_read') as mock_send_and_read:
            self.controller.set_commanded_power(12.34)
            mock_send_and_read.assert_called_once_with('PWOUT=12.34')

    def test_get_reject_temp(self):
        with patch.object(self.controller, '_send_and_read') as mock_send_and_read:
            self.controller.get_reject_temp()
            mock_send_and_read.assert_called_once_with('TEMP RJ')

    def test_get_cold_head_temp(self):
        with patch.object(self.controller, '_send_and_read') as mock_send_and_read:
            self.controller.get_cold_head_temp()
            mock_send_and_read.assert_called_once_with('TC')

    @patch('hispec.util.sunpower.sunpower_controller.socket.create_connection')
    def test_tcp_connection(self, mock_create_connection):
        mock_sock = MagicMock()
        mock_create_connection.return_value = mock_sock
        controller = SunpowerCryocooler(
            connection_type='tcp',
            tcp_host='127.0.0.1',
            tcp_port=1234,
            quiet=True
        )
        self.assertEqual(controller.connection_type, 'tcp')
        self.assertIs(controller.sock, mock_sock)

    @patch('hispec.util.sunpower.sunpower_controller.socket.create_connection', side_effect=OSError('fail'))
    def test_tcp_connection_error(self, mock_create_connection):
        with patch('hispec.util.sunpower.sunpower_controller.logger_utils.setup_logger') as mock_logger:
            logger = MagicMock()
            mock_logger.return_value = logger
            with self.assertRaises(OSError):
                SunpowerCryocooler(
                    connection_type='tcp',
                    tcp_host='127.0.0.1',
                    tcp_port=1234,
                    quiet=True
                )
            logger.error.assert_called()

    @patch('hispec.util.sunpower.sunpower_controller.serial.Serial', side_effect=OSError('fail'))
    def test_serial_connection_error(self, mock_serial):
        with patch('hispec.util.sunpower.sunpower_controller.logger_utils.setup_logger') as mock_logger:
            logger = MagicMock()
            mock_logger.return_value = logger
            with self.assertRaises(OSError):
                SunpowerCryocooler(
                    port='COM1',
                    baudrate=19200,
                    quiet=True
                )
            logger.error.assert_called()


if __name__ == '__main__':
    unittest.main()
