import serial
import socket
import io
import hispec.util.helper.logger_utils as logger_utils


class SunpowerCryocooler:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600, quiet=True, connection_type='serial', tcp_host=None,
                 tcp_port=None):
        logfile = __name__.rsplit(".", 1)[-1] + ".log"
        self.logger = logger_utils.setup_logger(__name__, log_file=logfile, quiet=quiet)
        self.connection_type = connection_type

        try:
            if connection_type == 'serial':
                self.ser = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    timeout=0.1,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE
                )
                self.sio = io.TextIOWrapper(io.BufferedRWPair(self.ser, self.ser))
                self.logger.info(f"Serial connection opened: {self.ser.is_open}")
            elif connection_type == 'tcp':
                if tcp_host is None or tcp_port is None:
                    raise ValueError("tcp_host and tcp_port must be specified for TCP connection")
                self.sock = socket.create_connection((tcp_host, tcp_port), timeout=2)
                self.sio = self.sock.makefile('rwb', buffering=0)
                self.logger.info(f"TCP connection opened: {tcp_host}:{tcp_port}")
            else:
                raise ValueError("connection_type must be 'serial' or 'tcp'")
        except (socket.error, ValueError) as e:
            self.logger.error(f"Failed to establish connection: {e}")
            raise

    def _send_command(self, command: str):
        """Send a command to the Sunpower controller."""
        try:
            if self.connection_type == 'serial':
                self.ser.write(f"{command}\r".encode())
                self.sio.flush()
            elif self.connection_type == 'tcp':
                self.sio.write(f"{command}\r".encode())
                self.sio.flush()
        except (serial.SerialException, socket.error) as e:
            self.logger.error(f"Failed to send command '{command}': {e}")
            raise

    def _read_reply(self):
        """Read and parse the reply from the device."""
        try:
            while True:
                try:
                    if self.connection_type == 'serial':
                        line = self.ser.readline()
                    elif self.connection_type == 'tcp':
                        line = self.sio.readline()
                except OSError as e:
                    self.logger.error(f"Socket read error: {e}")
                    break  # Exit the loop on timeout or read error

                if not line or not line.strip():
                    break
                decoded = line.decode().strip()
                self.logger.debug(f"Received line: {decoded}")
                parts = decoded.split("= ")
                if len(parts) == 2 and parts[1] != 'GT':
                    try:
                        value = round(float(parts[1]), 6)
                        self.logger.info(f"{parts[0]}: {value}")
                    except ValueError:
                        self.logger.warning(f"Failed to parse value: {decoded}")
        except (serial.SerialException, socket.error) as e:
            self.logger.error(f"Failed to read reply: {e}")
            raise

    async def _send_and_read(self, command: str):
        """Send a command and await its reply."""
        self._send_command(command)
        self._read_reply()

    async def get_status(self):
        """Query the current status of the device."""
        await self._send_and_read('STATUS')

    async def get_error(self):
        """Query the error status."""
        await self._send_and_read('ERROR')

    async def get_version(self):
        """Query the firmware version."""
        await self._send_and_read('VERSION')

    async def get_cold_head_temp(self):
        """Get the cold head temperature setting."""
        await self._send_and_read('TC')

    async def get_reject_temp(self):
        """Get the reject temperature setting."""
        await self._send_and_read('TEMP RJ')

    async def get_target_temp(self):
        """Get the target temperature setting."""
        await self._send_and_read('TTARGET')

    async def set_target_temp(self, temp_kelvin: float):
        """Set the target temperature in Kelvin."""
        await self._send_and_read(f'TTARGET={temp_kelvin}')

    async def get_commanded_power(self):
        """Get the user commanded power setting."""
        await self._send_and_read('PWOUT')

    async def set_commanded_power(self, watts: float):
        """Set the user commanded power in Watts."""
        await self._send_and_read(f'PWOUT={watts}')

    async def turn_on_cooler(self):
        """Turn the cooler ON."""
        await self._send_and_read('COOLER=ON')

    async def turn_off_cooler(self):
        """Turn the cooler OFF."""
        await self._send_and_read('COOLER=OFF')
