import serial
import socket
import time
import hispec.util.helper.logger_utils as logger_utils


class SunpowerCryocooler:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600, quiet=True, connection_type='serial',
                 tcp_host=None, tcp_port=None, read_timeout=1.0):
        logfile = __name__.rsplit(".", 1)[-1] + ".log"
        self.logger = logger_utils.setup_logger(__name__, log_file=logfile, quiet=quiet)
        self.connection_type = connection_type
        self.read_timeout = read_timeout

        try:
            if connection_type == 'serial':
                self.ser = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    timeout=read_timeout,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE
                )
                self.logger.info(f"Serial connection opened: {self.ser.is_open}")
            elif connection_type == 'tcp':
                if tcp_host is None or tcp_port is None:
                    raise ValueError("tcp_host and tcp_port must be specified for TCP connection")
                self.sock = socket.create_connection((tcp_host, tcp_port), timeout=2)
                self.sock.settimeout(read_timeout)
                self.logger.info(f"TCP connection opened: {tcp_host}:{tcp_port}")
            else:
                raise ValueError("connection_type must be 'serial' or 'tcp'")
        except Exception as e:
            self.logger.error(f"Failed to establish connection: {e}")
            raise

    def _send_command(self, command: str):
        """Send a command to the Sunpower controller."""
        full_cmd = f"{command}\r"
        try:
            if self.connection_type == 'serial':
                self.ser.write(full_cmd.encode())
            elif self.connection_type == 'tcp':
                self.sock.sendall(full_cmd.encode())
            self.logger.debug(f"Sent command: {repr(full_cmd)}")
        except Exception as e:
            self.logger.error(f"Failed to send command '{command}': {e}")
            raise

    def _read_reply(self):
        """Read and return lines from the device."""
        lines_out = []
        try:
            if self.connection_type == 'serial':
                raw_data = self.ser.read(1024)
            elif self.connection_type == 'tcp':
                try:
                    raw_data = self.sock.recv(1024)
                except socket.timeout:
                    self.logger.warning("TCP read timeout.")
                    return []

            if not raw_data:
                self.logger.warning("No data received.")
                return []

            self.logger.debug(f"Raw received: {repr(raw_data)}")
            lines = raw_data.decode(errors='replace').splitlines()
            for line in lines:
                stripped = line.strip()
                if stripped:
                    lines_out.append(stripped)
            return lines_out
        except Exception as e:
            self.logger.error(f"Failed to read reply: {e}")
            return []

    def _send_and_read(self, command: str):
        self._send_command(command)
        time.sleep(0.2)  # wait a bit for device to reply
        return self._read_reply()

    # --- User-Facing Methods (synchronous) ---
    def get_status(self):
        return self._send_and_read('STATUS')

    def get_error(self):
        return self._send_and_read('ERROR')

    def get_version(self):
        return self._send_and_read('VERSION')

    def get_cold_head_temp(self):
        return self._send_and_read('TC')

    def get_reject_temp(self):
        return self._send_and_read('TEMP RJ')

    def get_target_temp(self):
        return self._send_and_read('TTARGET')

    def set_target_temp(self, temp_kelvin: float):
        return self._send_and_read(f'TTARGET={temp_kelvin}')

    def get_commanded_power(self):
        return self._send_and_read('PWOUT')

    def set_commanded_power(self, watts: float):
        return self._send_and_read(f'PWOUT={watts}')

    def turn_on_cooler(self):
        return self._send_and_read('COOLER=ON')

    def turn_off_cooler(self):
        return self._send_and_read('COOLER=OFF')

