"""
Inficon VGC502 Controller Interface
"""
import sys
import socket
from errno import EISCONN
from typing import Union

from hardware_device_base import HardwareDeviceBase


class InficonVGC502(HardwareDeviceBase):
    """Class for interfacing with InficonVGC502"""
    # pylint: disable=too-many-instance-attributes

    UNIT_CODES = ("mbar", "Torr", "Pascal", "Micron", "hPascal", "Volt")

    def __init__(self, log: bool=True, logfile: str =__name__.rsplit('.', 1)[-1],
                 timeout: int=1):
        """Initialize the InficonVGC502 class.
        Args:
            log (bool): If True, start logging.
            logfile (str, optional): Path to log file.
            timeout (int, optional): Timeout in seconds.
        """
        super().__init__(log, logfile)
        self.timeout = timeout
        self.type = ""
        self.model = ""
        self.serial_number = None
        self.firmware_version = ""
        self.hardware_version = ""
        self.pressure_units = ""
        self.n_gauges = 0
        self.sock: socket.socket | None = None

    def connect(self, *args, con_type="tcp") -> None:
        """ Connect to the controller. """
        if self.validate_connection_params(args):
            if con_type == "tcp":
                host = args[0]
                port = args[1]
                if self.sock is None:
                    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    self.sock.connect((host, port))
                    self.logger.info("Connected to %s:%d", host, port)
                    self._set_connected(True)
                    # ensure subsequent ops also use timeout
                    self.sock.settimeout(self.timeout)

                except OSError as e:
                    if e.errno == EISCONN:
                        self.logger.info("Already connected")
                        self._set_connected(True)
                    else:
                        self.logger.error("Connection error: %s", e.strerror)
                        self._set_connected(False)
                if self.is_connected():
                    self._clear_socket()
            elif con_type == "serial":
                self.logger.error("Serial connection not supported")
            else:
                self.logger.error("Unknown con_type: %s", con_type)
        else:
            self.logger.error("Invalid connection arguments: %s", args)

    def _clear_socket(self):
        """Clear the socket connection."""
        if self.sock:
            self.sock.setblocking(False)
            while True:
                try:
                    _ = self.sock.recv(1024)
                except BlockingIOError:
                    break
            self.sock.setblocking(True)

    def disconnect(self):
        """Close the TCP connection."""
        try:
            self.logger.debug("Closing connection to controller")
            if self.sock:
                self.sock.close()
            self._set_connected(False)
        except Exception as ex:
            raise IOError(f"Failed to close connection: {ex}") from ex

    def _send_command(self, command: str, *args) -> bool:
        """
        Send a command to the controller.

        :param command: (str) Command to send.
        :param args: Arguments to send.
        :return: True on success, False on failure.
        """
        try:
            self.logger.debug("Sending command: %s", command)
            command += "\r\n"
            with self.lock:
                self.sock.sendall(command.encode())
        except Exception as ex:
            self.logger.error("Failed to send command: %s", ex)
            return False
            # raise IOError(f"Failed to send command: {ex}") from ex
        return True

    def _send_enq(self):
        """Send ENQ to the controller."""
        try:
            self.logger.debug("Sending ENQ to controller")
            with self.lock:
                self.sock.sendall(b"\x05")
        except Exception as ex:
            self.logger.error("Failed to send ENQ: %s", ex)
            return False
            # raise IOError(f"Failed to send ENQ: {ex}") from ex
        return True

    def _read_until(self, terminator: bytes = b"\r\n", max_bytes: int = 4096) -> bytes:
        """Read until 'terminator' or timeout. Returns bytes including the terminator."""
        buf = bytearray()
        try:
            while True:
                chunk = self.sock.recv(1)
                if not chunk:
                    # peer closed
                    break
                buf += chunk
                if buf.endswith(terminator):
                    break
                if len(buf) >= max_bytes:
                    break
                # self.logger.debug("Input buffer: %r", buf)
            return bytes(buf)
        except Exception as ex:
            raise IOError(f"Failed to _read_reply: {ex}") from ex

    def _read_reply(self) -> Union[str, None]:
        """Read reply from controller."""
        try:
            ack = self._read_until(b"\r\n").strip()
            self.logger.debug("Reply received: %r", ack)
        except socket.timeout:
            return None

        # ACK received
        if ack == b"\x06":
            self.logger.debug("ACK received, sending ENQ")
            try:
                if self._send_enq():
                    response = self._read_until(b"\r\n").decode().strip()
                else:
                    self.logger.error("Error sending ENQ")
                    return None
            except socket.timeout:
                return None
            except OSError as e:
                self.logger.error("IO error while receiving response: %s", e)
                return None

            self.logger.debug("Response received: %s", response)
            return response

        if ack == b'\x15':
            self.logger.error("NAK received, try command again.")
        else:
            self.logger.error("ACK NOT received")
        return None

    def initialize(self):
        """Initialize the controller."""
        self.logger.debug("Initializing controller")
        if self._send_command("UNI"):
            unit_code = int(self._read_reply())
            if 0 <= unit_code <= 5:
                self.pressure_units = self.UNIT_CODES[unit_code]
        if self._send_command("AYT"):
            devinfo = self._read_reply()
            dev_items = devinfo.split(",")
            if len(dev_items) == 5:
                self.type = dev_items[0]
                self.model = dev_items[1]
                self.serial_number = int(dev_items[2])
                self.firmware_version = dev_items[3]
                self.hardware_version = dev_items[4]
                try:
                    self.n_gauges = int(self.type[-1])
                except ValueError:
                    self.logger.error("Invalid gauge type, unable to parse n_gauges: %s", self.type)
                    self.n_gauges = 0
            else:
                self.logger.error("Error initializing controller: %s", devinfo)
        else:
            self.logger.error("Failed to initialize controller")

    def set_pressure_unit(self, unit_code: int =1) -> bool:
        """ Set the pressure units
        :param unit_code: (int) Pressure unit code
        :return: True on success, False on failure.

        Codes: 0 - mbar, 1 - Torr, 2 - Pascal, 3 - Micron, 4 - hPascal, 5 - Volt
        """
        retval = False
        if unit_code < 0 or unit_code > 5:
            self.logger.error("Invalid pressure unit code: %s\nMust be between 0 and 5 inclusive",
                              unit_code)
        else:
            if self._send_command(f"UNI,{unit_code}"):
                received = int(self._read_reply())
                if received != unit_code:
                    self.logger.error("Requested pressure unit code not achieved: %d", received)
                else:
                    retval = True
                if 0 <= received <= 5:
                    self.pressure_units = self.UNIT_CODES[received]
                else:
                    self.logger.error("Invalid pressure unit received: %d", received)
            else:
                retval = False
        return retval

    def get_pressure_unit(self) -> int:
        """ Get the pressure units"""
        if self._send_command("UNI"):
            received = int(self._read_reply())
            self.pressure_units = self.UNIT_CODES[received]
        else:
            received = None
        return received

    def read_temperature(self) -> float:
        """ Read temperature from controller."""
        command = "TMP"
        try:
            self._send_command(command)
        except DeviceConnectionError:
            self.logger.error("Connection error: %s", command)
            raise
        except OSError as e:
            self.logger.error("Failed to send command: %s", e)
            raise DeviceConnectionError("Write failed") from e

        response = self._read_reply()
        self.logger.debug("Temperature response: %s", response)
        try:
            value = float(response)
            return value
        except ValueError as e:
            self.logger.error("Failed to parse response: %s", e)
            return sys.float_info.max

    def read_pressure(self, gauge: int = 1) -> float:
        """Read pressure from gauge 1 to n.
        Returns float, or sys.float_info.max on timeout/parse error."""
        # pylint: disable=too-many-branches
        if self.n_gauges == 0:
            self.initialize()
        if not isinstance(gauge, int) or gauge < 1 or gauge > self.n_gauges:
            self.logger.error("gauge number must be between 1 and %d, inclusive", self.n_gauges)
            return sys.float_info.max

        # Command format: PR{gauge}
        command = f"PR{gauge}"
        try:
            self._send_command(command)
        except DeviceConnectionError:
            self.logger.error("Connection error: %s", command)
            raise
        except OSError as e:
            self.logger.error("Failed to send command: %s", e)
            raise DeviceConnectionError("Write failed") from e

        # Read acknowledgment line (controller typically replies with ACK/NAK ending CRLF)
        response = self._read_reply()
        self.logger.debug("Pressure response: %s", response)

        # Expected like: "PR1,<value>"
        try:
            parts = response.split(",")
            value = float(parts[1])
            return value
        except (IndexError, ValueError, AttributeError) as e:
            self.logger.error("Failed to parse response: %s", e)
            return sys.float_info.max

    def get_atomic_value(self, item: str ="") -> float:
        """
            Read the latest value of a specific channel.

            Args:
                item (str): Channel name (e.g., "3A", "Out1")

            Returns:
                float: Current value, or NaN if invalid.
        """
        if "pressure" in item:
            try:
                gauge_num = int(item.split("pressure")[-1])
                value = self.read_pressure(gauge=gauge_num)
            except ValueError:
                self.logger.error("Invalid item: %s", item)
                value = sys.float_info.max
        elif "temperature" in item:
            value = float(self.read_temperature())
        elif "units" in item:
            self.get_pressure_unit()
            value = self.pressure_units
        else:
            self.logger.error("Unknown item received: %r", item)
            value = sys.float_info.max
        return value

    def run_manually(self):
        """Input commands manually."""
        while True:
            cmd = input("> ")
            if not cmd:
                break

            if self._send_command(cmd):
                ret = self._read_reply()
                print(ret)

        print("End.")

class WrongCommandError(Exception):
    """Exception raised when a wrong command is sent."""


class UnknownResponse(Exception):
    """Exception raised when an unknown response is received."""


class DeviceConnectionError(Exception):
    """Exception raised when a device connection error occurs."""
