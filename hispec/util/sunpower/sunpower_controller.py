import serial
import io
import hispec.util.helper.logger_utils as logger_utils

class SunpowerCryocooler:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600, quiet=True):
        logfile = __name__.rsplit(".", 1)[-1] + ".log"
        self.logger = logger_utils.setup_logger(__name__, log_file=logfile, quiet=quiet)

        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=0.1,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        self.sio = io.TextIOWrapper(io.BufferedRWPair(self.ser, self.ser))
        self.logger.info(f"Serial connection opened: {self.ser.is_open}")

    def _send_command(self, command: str):
        """Send a command to the Sunpower controller."""
        self.ser.write(f"{command}\r".encode())
        self.sio.flush()

    def _read_reply(self):
        """Read and parse the reply from the device."""
        while True:
            line = self.ser.readline()
            if not line.strip():
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

    async def get_target_temp(self):
        """Get the target temperature setting."""
        await self._send_and_read('TTARGET')

    async def set_target_temp(self, temp_kelvin: float):
        """Set the target temperature in Kelvin."""
        await self._send_and_read(f'TTARGET={temp_kelvin}')

    async def turn_on_cooler(self):
        """Turn the cooler ON."""
        await self._send_and_read('COOLER=ON')

    async def turn_off_cooler(self):
        """Turn the cooler OFF."""
        await self._send_and_read('COOLER=OFF')
