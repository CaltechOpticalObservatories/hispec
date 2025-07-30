"""
A Python class to control a Sunpower cryocooler via serial or TCP connection.
"""
import socket
import time
import serial
import hispec.util.helper.logger_utils as logger_utils


class SunpowerCryocooler:
    """A class to control a Sunpower cryocooler via serial or TCP connection."""
    def __init__(
            self,
            port="/dev/ttyUSB0",
            baudrate=9600,
            quiet=True,
            connection_type="serial",
            tcp_host=None,
            tcp_port=None,
            read_timeout=1.0,
    ): # pylint: disable=too-many-arguments
        """ Initialize the SunpowerCryocooler."""
        logfile = __name__.rsplit(".", 1)[-1] + ".log"
        self.logger = logger_utils.setup_logger(__name__, log_file=logfile, quiet=quiet)
        self.connection_type = connection_type
        self.read_timeout = read_timeout

        try:
            if connection_type == "serial":
                self.ser = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    timeout=read_timeout,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                )
                self.logger.info("Serial connection opened: %s", self.ser.is_open)
            elif connection_type == "tcp":
                if tcp_host is None or tcp_port is None:
                    raise ValueError(
                        "tcp_host and tcp_port must be specified for TCP connection"
                    )
                self.sock = socket.create_connection((tcp_host, tcp_port), timeout=2)
                self.sock.settimeout(read_timeout)
                self.logger.info("TCP connection opened: %s:%s", tcp_host, tcp_port)
            else:
                raise ValueError("connection_type must be 'serial' or 'tcp'")
        except Exception as ex:
            self.logger.error("Failed to establish connection: %s", ex)
            raise

    def _send_command(self, command: str):
        """Send a command to the Sunpower controller."""
        full_cmd = f"{command}\r"
        try:
            if self.connection_type == "serial":
                self.ser.write(full_cmd.encode())
            elif self.connection_type == "tcp":
                self.sock.sendall(full_cmd.encode())
            self.logger.debug("Sent command: %s", repr(full_cmd))
        except Exception as ex:
            self.logger.error("Failed to send command '%s': %s", command, ex)
            raise

    def _read_reply(self):
        """Read and return lines from the device."""
        lines_out = []
        try:
            if self.connection_type == "serial":
                raw_data = self.ser.read(1024)
            elif self.connection_type == "tcp":
                try:
                    raw_data = self.sock.recv(1024)
                except socket.timeout:
                    self.logger.warning("TCP read timeout.")
                    return []

            if not raw_data:
                self.logger.warning("No data received.")
                return []

            self.logger.debug("Raw received: %s", repr(raw_data))
            lines = raw_data.decode(errors="replace").splitlines()
            for line in lines:
                stripped = line.strip()
                if stripped:
                    lines_out.append(stripped)
            return lines_out
        except (serial.SerialException, socket.error, ValueError) as ex:
            self.logger.error("Failed to read reply: %s", ex)
            return []

    def _send_and_read(self, command: str):
        """Send a command and read the reply."""
        self._send_command(command)
        time.sleep(0.2)  # wait a bit for device to reply
        return self._read_reply()

    # --- User-Facing Methods (synchronous) ---
    def get_status(self):
        """Get the status of the Sunpower cryocooler."""
        return self._send_and_read("STATUS")

    def get_error(self):
        """Get the last error message from the Sunpower cryocooler."""
        return self._send_and_read("ERROR")

    def get_version(self):
        """Get the firmware version of the Sunpower cryocooler."""
        return self._send_and_read("VERSION")

    def get_cold_head_temp(self):
        """Get the temperature of the cold head."""
        return self._send_and_read("TC")

    def get_reject_temp(self):
        """Get the temperature of the reject heat."""
        return self._send_and_read("TEMP RJ")

    def get_target_temp(self):
        """Get the target temperature set for the cryocooler."""
        return self._send_and_read("TTARGET")

    def set_target_temp(self, temp_kelvin: float):
        """Set the target temperature for the cryocooler in Kelvin."""
        return self._send_and_read(f"TTARGET={temp_kelvin}")

    def get_measured_power(self):
        """Get the measured power of the cryocooler."""
        return self._send_and_read("P")

    def get_commanded_power(self):
        """Get the commanded power of the cryocooler."""
        return self._send_and_read("PWOUT")

    def set_commanded_power(self, watts: float):
        """Set the commanded power for the cryocooler in watts."""
        return self._send_and_read(f"PWOUT={watts}")

    def turn_on_cooler(self):
        """Turn on the cryocooler."""
        return self._send_and_read("COOLER=ON")

    def turn_off_cooler(self):
        """Turn off the cryocooler."""
        return self._send_and_read("COOLER=OFF")
