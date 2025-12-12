"""Gamma Vacuum SPCe model utility functions."""
import errno
import time
import socket
import re
from typing import Union

from hardware_device_base import HardwareDeviceBase

# Constants (partial, extend as needed)
SPCE_TIME_BETWEEN_COMMANDS = 0.12

# Command codes (extend as needed)
SPCE_COMMAND_READ_MODEL = 0x01
SPCE_COMMAND_READ_VERSION = 0x02
SPCE_COMMAND_RESET = 0x07
SPCE_COMMAND_SET_ARC_DETECT = 0x91
SPCE_COMMAND_GET_ARC_DETECT = 0x92
SPCE_COMMAND_READ_CURRENT = 0x0A
SPCE_COMMAND_READ_PRESSURE = 0x0B
SPCE_COMMAND_READ_VOLTAGE = 0x0C
SPCE_COMMAND_GET_PUMP_STATUS = 0x0D
SPCE_COMMAND_SET_PRESS_UNITS = 0x0E
SPCE_COMMAND_GET_PUMP_SIZE = 0x11
SPCE_COMMAND_SET_PUMP_SIZE = 0x12
SPCE_COMMAND_GET_CAL_FACTOR = 0x1D
SPCE_COMMAND_SET_CAL_FACTOR = 0x1E
SPCE_COMMAND_SET_AUTO_RESTART = 0x33
SPCE_COMMAND_GET_AUTO_RESTART = 0x34
SPCE_COMMAND_START_PUMP = 0x37
SPCE_COMMAND_STOP_PUMP = 0x38
SPCE_COMMAND_LOCK_KEYPAD = 0x44
SPCE_COMMAND_UNLOCK_KEYPAD = 0x45
SPCE_COMMAND_GET_ANALOG_MODE = 0x50
SPCE_COMMAND_SET_ANALOG_MODE = 0x51
SPCE_COMMAND_IS_HIGH_VOLTAGE_ON = 0x61
SPCE_COMMAND_SET_HV_AUTORECOVERY = 0x68
SPCE_COMMAND_GET_HV_AUTORECOVERY = 0x69
SPCE_COMMAND_SET_COMM_MODE = 0xD3
SPCE_COMMAND_GET_COMM_MODE = 0xD4
SPCE_COMMAND_SET_COMM_INTERFACE = 0x4B

SPCE_UNITS_TORR = 'T'
SPCE_UNITS_MBAR = 'M'
SPCE_UNITS_PASCAL = 'P'


class SpceController(HardwareDeviceBase):
    """Class to control a Lesker GAMMA gauge SPCe controller over a TCP socket."""
    # pylint: disable=too-many-public-methods

    def __init__(self, bus_address: int =1, simulate: bool =False,
                 log: bool =True, logfile: str = __name__.rsplit(".", 1)[-1] ) -> None:
        """Initialize the SpceController.

        Args:
            bus_address (str): bus address of the controller (00 - FF).
            simulate (bool): If True, simulate communication.
            log (bool): If True, log outputs.
            logfile (str): If specified, write logs to this file.

            NOTE; default is INFO level logging, use set_verbose to increase verbosity.
        """
        super().__init__(log, logfile)

        # Bus address
        self.bus_address = bus_address

        # Set up socket
        self.sock = None

        # Simulate mode
        if simulate:
            self.simulate = True
            self.logger.info("Simulate mode enabled.")
        else:
            self.simulate = False

    def connect(self, *args, con_type="tcp") -> None:
        """Connect to the controller.

        :param args: for tcp connection, host and port, for serial, port and baudrate
        :param con_type: tcp or serial
        """
        if self.validate_connection_params(args):
            if self.simulate:
                self.connected = True
                self.logger.info('Connected to SPCe simulator.')
            else:
                if con_type == "tcp":
                    host = args[0]
                    port = args[1]
                    if self.sock is None:
                        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        self.sock.connect((host, port))
                        self._set_connected(True)
                        self.logger.info("Connected to SPCe controller at %s:%d bus %d",
                                         host, port, self.bus_address)
                    except OSError as e:
                        if e.errno == errno.EISCONN:
                            self.logger.debug("Already connected")
                            self._set_connected(True)
                        else:
                            self.logger.error("Connection error: %s", e.strerror)
                            self._set_connected(False)
                    if self.connected:
                        self._clear_socket()
                elif con_type == "serial":
                    self.logger.error("Serial connection not implemented.")
                    self._set_connected(False)
                else:
                    self.logger.error("Unknown con_type: %s", con_type)
                    self._set_connected(False)
        else:
            self.logger.error("Invalid connection args: %s", args)
            self._set_connected(False)

    def disconnect(self) -> None:
        """Disconnect from the controller."""
        if self.simulate:
            self.logger.info('Disconnected from SPCe simulator.')
            self.connected = False
        else:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
                self._set_connected(False)
                self.sock = None
                self.logger.info("Disconnected from SPCe controller")
            except OSError as e:
                self.logger.error("Disconnection error: %s", e.strerror)
                self._set_connected(False)
                self.sock = None

    def _clear_socket(self):
        """ Clear socket buffer. """
        if self.sock is not None:
            self.sock.setblocking(False)
            while True:
                try:
                    _ = self.sock.recv(1024)
                except BlockingIOError:
                    break
            self.sock.setblocking(True)
            self.sock.settimeout(2.0)

    def _send_command(self, command: str, *args) -> bool:
        """Send a command without expecting a response.
        Args:
            command (str): command to send.
        """
        if not self.is_connected:
            self.logger.error("Not connected to SPCe controller.")
            return False

        self.logger.debug("Sending command %s", command)
        if self.simulate:
            print(f"[SIM SEND] {command}")
            return True
        with self.lock:
            self.sock.sendall(command.encode('utf-8'))
            time.sleep(SPCE_TIME_BETWEEN_COMMANDS)
        return True

    def _read_reply(self) -> Union[str, None]:
        """Read a reply from the controller."""
        if not self.is_connected:
            self.logger.error("Not connected to SPCe controller.")
            return None
        try:
            reply = self.sock.recv(1024).decode('utf-8').strip()
            self.logger.debug("Received reply %s", reply)
            return reply
        except Exception as ex:
            raise IOError(f"Failed to _read_reply message: {ex}") from ex

    def _send_request(self, command: str, response_type: str ="S") -> Union[int, float, str]:
        """Send a command and receive a response.
        Args:
            command (str): Command to send.
            response_type (str): Type of response:
                'I' for int, 'S' for str (default), 'F' for float.
            """
        if not self.connected:
            self.logger.error("Not connected to SPCe controller.")
            return "NOT CONNECTED"

        self.logger.debug("Sending request %s", command)
        if self.simulate:
            print(f"[SIM REQ] {command}")
            return "SIM_RESPONSE"
        with self.lock:
            self.sock.sendall(command.encode('utf-8'))
            time.sleep(SPCE_TIME_BETWEEN_COMMANDS)
            try:
                recv = self.sock.recv(1024)
                recv_len = len(recv)
                self.logger.debug("Return: len = %d, Value = %s", recv_len, recv)
            except socket.timeout:
                self.logger.error("Timeout while waiting for response")
                return "TIMEOUT"
            retval = str(recv.decode('utf-8')).strip()
            if self.validate_response(retval):
                response_type = response_type.upper()
                if response_type == "F":
                    retval = extract_float_from_response(retval)
                elif response_type == "I":
                    retval = extract_int_from_response(retval)
                else:
                    retval = extract_string_from_response(retval)
                return retval
            return "NOT VALID"

    def create_command(self, code, data=None):
        """Create a properly formatted command string.

        Args:
            code (int): Command code.
            data (str): Command data.

        This function creates a command string to be passed to
        the SPCe vacuum controller. See SPCe vacuum SPCe controller user manual
        from gammavacuum.com for details.

        Commands use this format:
        {attention char} {bus_address} {command code} {data} {termination}
              ~              ba              cc         data       \r

        With
        ba   = address value between 01 and FF.
        cc   = character string representing command (2 bytes).
        data = optional value for command (e.g. baud rate, adress setting, etc.).
        """

        command = f" {self.bus_address:02X} {code:02X} "
        if data:
            command += f"{data} "

        chksm = sum(ord(c) for c in command) % 256

        command = f"~{command}{chksm:02X}\r"
        return command

    def validate_response(self, response: str) -> int:
        """
        Validate the response string from a serial device.

        Args:
            response (str): The raw response string from the device.

        Returns:
            int: 0 if valid, or an error code.
        """
        # pylint: disable=too-many-branches

        try:
            # The First field must be the bus address
            bus = int(response.split()[0])
        except (ValueError, IndexError):
            self.logger.error("Invalid response from device.")
            return False

        if bus != self.bus_address:
            self.logger.error("Invalid bus address from device.")
            return False

        # Now check for error condition or valid response
        substr = response[3:]

        if substr.startswith("ER"):
            try:
                error_code_str = substr[3:]
                self.logger.error(error_code_str)
            except ValueError:
                pass
            return False

        # Calculate and verify checksum
        offset = len(response) - 3
        try:
            rcksm = int(response[offset:], 16)  # Read hex checksum to decimal
        except ValueError:
            self.logger.error("Unable to read checksum from device.")
            return False

        # Calculate checksum (sum of all chars before checksum, mod 256)
        cksm = sum(ord(c) for c in response[:offset+1]) % 256

        if rcksm != cksm:
            self.logger.error("Invalid checksum from device.")
            return False

        return True

    # --- Command Methods ---
    def get_atomic_value(self, item: str ="") -> Union[float, int, str, None]:
        """Get an atomic telemetry value."""
        if item == "pressure":
            value = self.read_pressure()
        elif item == "current":
            value = self.read_current()
        elif item == "voltage":
            value = self.read_voltage()
        else:
            self.logger.error("Invalid item from device.")
            value = None
        return value

    def read_model(self):
        """Read the model from the controller."""
        return self._send_request(self.create_command(SPCE_COMMAND_READ_MODEL))

    def read_version(self):
        """Read the firmware version from the controller."""
        return self._send_request(self.create_command(SPCE_COMMAND_READ_VERSION))

    def reset(self):
        """Send a reset command to the controller."""
        return self._send_command(self.create_command(SPCE_COMMAND_RESET))

    def set_arc_detect(self, enable):
        """Enable or disable arc detection."""
        val = "YES" if enable else "NO"
        return self._send_request(self.create_command(SPCE_COMMAND_SET_ARC_DETECT, val))

    def get_arc_detect(self):
        """Get the current arc detection setting."""
        return self._send_request(self.create_command(SPCE_COMMAND_GET_ARC_DETECT))

    def read_current(self):
        """Read the emission current."""
        return self._send_request(
            self.create_command(SPCE_COMMAND_READ_CURRENT), "F")

    def read_pressure(self):
        """Read the pressure value."""
        return self._send_request(
            self.create_command(SPCE_COMMAND_READ_PRESSURE), "F")

    def read_voltage(self):
        """Read the ion gauge voltage."""
        return self._send_request(
            self.create_command(SPCE_COMMAND_READ_VOLTAGE), "F")

    def set_units(self, unit_char):
        """Set the pressure display units.

        Args:
            unit_char (str): One of 'T', 'M', or 'P'.
        """
        unit_char = unit_char.upper()
        if unit_char not in [SPCE_UNITS_TORR, SPCE_UNITS_MBAR, SPCE_UNITS_PASCAL]:
            raise ValueError("Invalid unit. Use 'T', 'M', or 'P'.")
        return self._send_request(self.create_command(SPCE_COMMAND_SET_PRESS_UNITS, unit_char))

    def get_pump_status(self):
        """Get the pump status."""
        return self._send_request(
            self.create_command(SPCE_COMMAND_GET_PUMP_STATUS))

    def get_pump_size(self):
        """Get the configured pump size."""
        return self._send_request(
            self.create_command(SPCE_COMMAND_GET_PUMP_SIZE), "I")

    def set_pump_size(self, size):
        """Set the pump size.

        Args:
            size (int): Pump size (0-9999).
        """
        if not 0 <= size <= 9999:
            raise ValueError("Pump size out of range (0-9999).")
        return self._send_request(self.create_command(SPCE_COMMAND_SET_PUMP_SIZE, f"{size:04d}"))

    def get_cal_factor(self):
        """Get the calibration factor."""
        return self._send_request(
            self.create_command(SPCE_COMMAND_GET_CAL_FACTOR), "F")

    def set_cal_factor(self, factor):
        """Set the calibration factor.

        Args:
            factor (float): Calibration factor (0.00 to 9.99).
        """
        if not 0.0 <= factor <= 9.99:
            raise ValueError("Calibration factor out of range (0.00 - 9.99).")
        return self._send_request(self.create_command(
            SPCE_COMMAND_SET_CAL_FACTOR, f"{factor:.2f}"))

    def set_auto_restart(self, enable: bool):
        """Enable or disable auto restart."""
        val = "YES" if enable else "NO"
        return self._send_request(self.create_command(SPCE_COMMAND_SET_AUTO_RESTART, val))

    def get_auto_restart(self):
        """Get the auto restart setting."""
        return self._send_request(self.create_command(SPCE_COMMAND_GET_AUTO_RESTART))

    def start_pump(self):
        """Start the pump."""
        return self._send_request(self.create_command(SPCE_COMMAND_START_PUMP))

    def stop_pump(self):
        """Stop the pump."""
        return self._send_request(self.create_command(SPCE_COMMAND_STOP_PUMP))

    def lock_keypad(self, lock):
        """Lock or unlock the controller keypad."""
        cmd = SPCE_COMMAND_LOCK_KEYPAD if lock else SPCE_COMMAND_UNLOCK_KEYPAD
        return self._send_request(self.create_command(cmd))

    def get_analog_mode(self):
        """Get the analog output mode."""
        return self._send_request(
            self.create_command(SPCE_COMMAND_GET_ANALOG_MODE), "I")

    def set_analog_mode(self, mode: int):
        """Set the analog output mode.

        Args:
            mode (int): Analog mode (0-6, 8-10).
        """
        if mode not in list(range(0, 7)) + [8, 9, 10]:
            raise ValueError("Invalid analog mode. Must be 0-6 or 8-10.")
        return self._send_request(self.create_command(SPCE_COMMAND_SET_ANALOG_MODE, str(mode)))

    def high_voltage_on(self):
        """Check if high voltage is on."""
        return self._send_request(self.create_command(SPCE_COMMAND_IS_HIGH_VOLTAGE_ON))

    def set_hv_autorecovery(self, mode: int):
        """Set HV autorecovery mode.

        Args:
            mode (int): Mode (0-2).
        """
        if mode not in [0, 1, 2]:
            raise ValueError("Invalid HV autorecovery mode (0-2).")
        return self._send_request(self.create_command(SPCE_COMMAND_SET_HV_AUTORECOVERY, str(mode)))

    def get_hv_autorecovery(self):
        """Get the HV autorecovery setting."""
        return self._send_request(
            self.create_command(SPCE_COMMAND_GET_HV_AUTORECOVERY))

    def set_comm_mode(self, mode):
        """Set the communication mode.

        Args:
            mode (int): Communication mode (0-2).
        """
        if mode not in [0, 1, 2]:
            raise ValueError("Invalid communication mode (0-2).")
        return self._send_request(self.create_command(SPCE_COMMAND_SET_COMM_MODE, str(mode)))

    def get_comm_mode(self):
        """Get the communication mode."""
        return self._send_request(
            self.create_command(SPCE_COMMAND_GET_COMM_MODE), "I")

    def set_comm_interface(self, interface):
        """Set the communication interface.

        Args:
            interface (int): Interface index (0-5).
        """
        if interface not in range(6):
            raise ValueError("Invalid communication interface (0-5).")
        return self._send_request(self.create_command(
            SPCE_COMMAND_SET_COMM_INTERFACE, str(interface)))

def extract_float_from_response(response):
    """Extract a float value from the response string."""
    response = response.split("OK 00 ")[-1].split()[0]
    try:
        match = re.search(r"([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)", response)
        return float(match.group(1)) if match else None
    except ValueError:
        return None

def extract_int_from_response(response):
    """Extract an integer value from the response string."""
    response = response.split("OK 00 ")[-1].split()[0]
    try:
        match = re.search(r"([-+]?[0-9]+)", response)
        return int(match.group(1)) if match else None
    except ValueError:
        return None

def extract_string_from_response(response):
    """Extract a string value from a key=value response."""
    response = " ".join(response.split("OK 00 ")[-1].split()[:-1])
    try:
        parts = response.split(',')
        for part in parts:
            if '=' in part:
                return part.split('=')[1].strip()
        return response.strip()
    except ValueError:
        return response.strip()
