# coding=utf-8
"""
The following controller commands are available.  Not that many are not implemented at the moment.
The asterisk indicates the commands that are implemented.

A<n>      * - Sets attenuation to <n>.
        Two digits to the right of the decimal point are allowed, but not required.
A?        * - Gets attenuation.
B         * - Steps the attenuator one step backward.
        Returns the final position after the command is completed.
CD          - Sends the current unit configuration only to the RS-232 communications port.
CH<hh>      - Sets the I2C address to the hexadecimal address <hh>
        when the address <hh> is a valid I2C address between 0x00 and 0x7F.
CI<ddd>     - Sets the I2C address to the decimal address <ddd>
        when the address <ddd> is a valid I2C address between 0 and 127.
CS<cp><dp>  - Sets the SPI parameters to <cp> and <dp>,
        where <cp> is clock polarity and <dp> is data position.
D         * - Gets current attenuation and step position.
E0        * - In RS-232 mode, sets echo to OFF.
        The unit does not echo any characters received through the RS-232 interface.
E1        * - In RS-232 mode, sets echo to ON.
        The unit echoes all characters received through the RS-232 interface.
EVA8        - Set the unit in EVA8 mode
EVA9        - Set the unit in EVA9 mode
EVA?        - Requests the current EVA configuration mode
F         * - Steps the attenuator one step forward.
H         * - Re-homes the unit.
I2C?        - Gets I2C/SPI bus  Voltage
I2C3        - Sets I2C/SPI bus voltage to 3.3V
I2C5        - Sets I2C/SPI bus voltage to 5.0V
L<n>        - Sets the unit’s insertion loss to <n>.
        Two digits following the decimal point are allowed, but not required.
RES?      * - Read previous command response
RST       * - Restarts in response to a hardware or software reset (RST) command
        and is in self-test mode.
S?        * - Requests the current position of the attenuator.
        Returns the current number of steps from the home position.
S<n>      * - Sets the position of the attenuator to <n> steps from the home position.
S+<n>     * - Sets the step position of the attenuator to <n> steps
        numerically greater than the current position.
S-<n>     * - Sets the step position of the attenuator to <n> steps
        numerically less than the current position.
W<n>        - Selects the wavelength using <n>.
    This command is valid only when the unit is calibrated for more than one wavelength.

"""
import dataclasses
import enum
import errno
import time
import socket
from typing import Union

from hardware_device_base import HardwareDeviceBase

class ResponseType(enum.Enum):
    """Controller response types."""
    ATTEN = "attenuation"
    POS = "steps"
    DIFF = "diff"
    BOTH = "attenuation and steps"
    STRING = "string"
    ERROR = "error"


@dataclasses.dataclass
class OzResponse:
    """Oz controller response data."""
    type: ResponseType
    value: Union[float, int, str, dict, None]


class OZController(HardwareDeviceBase):
    """
    Controller class for OZ Optics DD-100-MC Attenuator Controller.
    """
    # pylint: disable=too-many-instance-attributes

    controller_commands = ["A",     # Set attenuation
                           "A?",    # Get attenuation
                           "B",     # Move attenuator one step backward
                           "CD",    # Configuration Display
                           "D",     # Gets current attenuation and step position
                           "E0",    # In RS232 mode, sets echo to OFF
                           "E1",    # In RS232 mode, sets echo to ON
                           "F",     # Move attenuator one step forward
                           "H",     # Re-homes the unit
                           "L",     # Insertion loss
                           "RES?",  # Read previous command response
                           "RST",   # Restarts in self-test mode
                           "S?",    # Requests current position of the attenuator
                           "S",     # Sets the position of the attenuator to <n> steps from home
                           "S+",    # Adds <n> steps to current position
                           "S-"     # Subtracts <n> steps from current position
                           ]
    return_value_commands = ["A", "A?", "B", "CD", "D", "F", "H", "L",
                             "RES?", "RST", "S?", "S", "S+", "S-" ]
    parameter_commands = ["A", "L", "S", "S+", "S-"]
    error = {
        "Done": "No error.",
        "Error-2": "Bad command.  The command is ignored.",
        "Error-5": "Home sensor error.  Return unit to factory for repair.",
        "Error-6": "Overflow.  The command is ignored.",
        "Error-7": "Motor voltage exceeds safe limits"
    }

    def __init__(self, log: bool =True, logfile: str =__name__.rsplit(".", 1)[-1]):

        """
        Class to handle communications with the stage controller and any faults

        :param log: Boolean, whether to log to file or not
        :param logfile: Filename for log

        NOTE: default is INFO level logging, use set_verbose to increase verbosity.
        """
        super().__init__(log, logfile)

        # Set up socket
        self.socket = None

        self.current_attenuation = None
        self.current_position = None
        self.current_diff = None
        self.configuration = ""
        self.homed = False
        self.last_error = ""

    def _clear_socket(self):
        """ Clear socket buffer. """
        if self.socket is not None:
            self.socket.setblocking(False)
            while True:
                try:
                    _ = self.socket.recv(1024)
                except BlockingIOError:
                    break
            self.socket.setblocking(True)

    def _read_reply(self) -> dict:
        """Read the return message from stage controller."""
        # Get return value
        recv = self.socket.recv(2048)

        # Did we get the entire return?
        tries = 5
        while tries > 0 and b'Done' not in recv:
            recv += self.socket.recv(2048)
            if b'Error' in recv:
                self.logger.error(recv)
                return {'error': self._return_parse_error(str(recv.decode('utf-8')))}
            tries -= 1

        recv_len = len(recv)
        self.logger.debug("Return: len = %d, Value = %s", recv_len, recv)

        if b'Done' not in recv:
            self.logger.warning("Read from controller timed out")
            msg_type = 'error'
            msg_data = str(recv.decode('utf-8'))
        else:
            resp = self._parse_response(str(recv.decode('utf-8')))
            msg_data = resp.value
            if resp.type == ResponseType.ERROR:
                msg_type = 'error'
            else:
                msg_type = 'data'

        return {msg_type: msg_data}

    def _parse_response(self, raw: str) -> OzResponse:
        """Parse the response from stage controller."""
        # pylint: disable=too-many-branches
        raw = raw.strip()

        if 'Pos:' in raw:
            try:
                pos = int(raw.split('Pos:')[1].split()[0])
                self.current_position = pos
                pos_read = True
            except ValueError:
                self.logger.error("Error parsing position")
                pos = None
                pos_read = False
        else:
            pos = None
            pos_read = False

        if 'Atten:' in raw:
            try:
                if 'unknown' in raw:
                    atten = None
                else:
                    atten = float(raw.split('Atten:')[1].split('(')[0])
                self.current_attenuation = atten
                atten_read = True
            except ValueError:
                self.logger.error("Error parsing attenuation")
                atten = None
                atten_read = False
        else:
            atten = None
            atten_read = False

        # Diff (after homing)
        if 'Diff=' in raw:
            try:
                diff = float(raw.split('Diff=')[1].split()[0])
                self.current_diff = diff
                self.current_position = 0
                diff_read = True
            except ValueError:
                self.logger.error("Error parsing diff")
                diff = None
                diff_read = False
        else:
            diff = None
            diff_read = False

        # Error case
        if 'Error' in raw:
            return OzResponse(ResponseType.ERROR, raw)

        # Both Attenuation and Steps
        if pos_read and atten_read:
            return OzResponse(ResponseType.BOTH, {"pos": pos, "atten": atten})

        # Attenuation
        if atten_read:
            return OzResponse(ResponseType.ATTEN, atten)

        # Pos
        if pos_read:
            return OzResponse(ResponseType.POS, pos)

        # Diff (after homing)
        if diff_read:
            return OzResponse(ResponseType.DIFF, diff)

        # Default to string
        return OzResponse(ResponseType.STRING, raw)

    def _send_serial_command(self, cmd=''):
        """
        Send serial command to stage controller

        :param cmd: String, command to send to stage controller
        :return: dictionary {'data|error': string_message}
        """

        # check connection
        if not self.connected:
            msg_text = "Not connected to controller!"
            self.logger.error(msg_text)

        # Prep command
        cmd_send = f"{cmd}\r\n"
        self.logger.debug("Sending command: %s", cmd_send)
        cmd_encoded = cmd_send.encode('utf-8')

        try:
            self.socket.settimeout(30)
            # Send command
            self.socket.send(cmd_encoded)
            time.sleep(.05)
            msg_type = 'data'
            msg_text = 'Command sent successfully'

        except socket.error as ex:
            msg_type = 'error'
            msg_text = f"Command send error: {ex.strerror}"
            self.logger.error(msg_text)

        return {msg_type: msg_text}

    def _send_command(self, command: str, *args, custom_command=False) -> dict:
        """
        Send a command to the stage controller

        :param command: String, command to send to the stage controller
        :param *args: List of string parameters associated with cmd
        :param custom_command: Boolean, if true, command is custom
        :return: dictionary {'data|error': string_message}
        """

        # verify cmd and stage_id
        ret = self._verify_send_command(command, custom_command)
        if 'error' in ret:
            return ret

        # Check if the command should have parameters
        if command in self.parameter_commands and args:
            self.logger.debug("Adding parameters")
            parameters = [str(x) for x in args]
            parameters = "".join(parameters)
            command += parameters

        self.logger.debug("Input command: %s", command)

        # Send serial command
        with self.lock:
            result = self._send_serial_command(command)

        return result

    def _verify_send_command(self, cmd, custom_command=False):
        """ Verify cmd and stage_id

        :param cmd: String, command to send to the stage controller
        :param custom_command: Boolean, if true, command is custom
        :return: dictionary {'data|error': string_message}"""

        # Do we have a connection?
        if not self.connected:
            msg_type = 'error'
            msg_text = 'Not connected to controller'

        else:
            # Do we have a legal command?
            if cmd.rstrip().upper() in self.controller_commands:
                msg_type = 'data'
                msg_text = f"{cmd} is a valid or custom command"
            else:
                if not custom_command:
                    msg_type = 'error'
                    msg_text = f"{cmd} is not a valid command"
                else:
                    msg_type = 'data'
                    msg_text = f"{cmd} is a custom command"

        return {msg_type: msg_text}

    def _return_parse_error(self, error=""):
        """
        Parse the return error message from the controller.  The message code is
        given in the last string character

        :param error: Error code from the controller
        :return: String message
        """
        error = error.rstrip()
        return self.error.get(error, "Unknown error")

    # --- User-Facing Methods
    def connect(self, *args,  con_type: str="tcp") -> None:
        """ Connect to stage controller.

        :param args: for tcp connection, host and port, for serial, port and baudrate
        :param con_type: tcp or serial
        """
        if self.validate_connection_params(args):
            if con_type == "tcp":
                host = args[0]
                port = args[1]
                if self.socket is None:
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    self.socket.connect((host, port))
                    self.logger.info("Connected to %s:%d", host, port)
                    self._set_connected(True)

                except OSError as ex:
                    if ex.errno == errno.EISCONN:
                        self.logger.debug("Already connected")
                        self._set_connected(True)
                    else:
                        self.logger.error("Connection error: %s", ex.strerror)
                        self._set_connected(False)
                # clear socket
                if self.is_connected():
                    self._clear_socket()
            elif con_type == "serial":
                self.logger.error("Serial connection not implemented")
                self._set_connected(False)
            else:
                self.logger.error("Unknown con_type: %s", con_type)
                self._set_connected(False)
        else:
            self.logger.error("Invalid connection args: %s", args)
            self._set_connected(False)

    def disconnect(self):
        """ Disconnect stage controller. """
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.socket = None
            self.logger.debug("Disconnected controller")
            self._set_connected(False)
        except OSError as ex:
            self.logger.error("Disconnection error: %s", ex.strerror)
            self._set_connected(False)
            self.socket = None

    def home(self):
        """
        Home the stage

        :return: return from __send_command
        """

        if not self.homed:
            ret = self._send_command('H')
            self.current_attenuation = None
            self.current_position = None

            if 'data' in ret:
                ret = self._read_reply()
                if 'error' in ret:
                    self.logger.error(ret['error'])
                else:
                    self.logger.debug(ret['data'])
                    self.homed = True
            else:
                self.logger.error(ret['error'])
        else:
            ret = {'data': 'already homed' }

        return ret

    def get_atomic_value(self, item: str ="") -> Union[float, int, str, None]:
        """Return single value for item"""
        if "pos" in item:
            result = self.get_position()
            if 'error' in result:
                self.logger.error(result['error'])
                value = None
            else:
                value = int(result['data'])
        elif "atten" in item:
            value = self.current_attenuation
        else:
            self.logger.error("Unknown item: %s, choose pos or atten", item)
            value = None
        return value

    def set_attenuation(self, atten: float=None):
        """
        Move stage to input attenuation and return when in position

        :param atten: Float, absolute attenuation in dB (0. - 60.)
        :return: dictionary {'data|error': current_attenuation|string_message}
        """
        # check attenuation limits
        if atten is None or atten < 0.0 or atten > 60.0:
            self.logger.error("Invalid attenuation: %s, cannot be < 0. or > 60.", atten)
            return {'error': 'Invalid attenuation'}

        # Send move to controller
        ret = self._send_command("A", atten)

        if 'data' in ret:
            ret = self._read_reply()
            if 'error' in ret:
                self.logger.error(ret['error'])
            else:
                time.sleep(0.5)
                cur_atten = self.get_attenuation()['data']
                self.logger.debug(cur_atten)
                if cur_atten != atten:
                    self.logger.error("Attenuation setting not achieved!")
                return {'data': cur_atten}

        return ret

    def set_position(self, pos=None):
        """
        Move stage to absolute position and return when in position

        :param pos: Int, absolute position in steps
        :return: dictionary {'data|error': current_attenuation|string_message}
        """

        # Send move to controller
        ret = self._send_command("S", pos)

        if 'data' in ret:
            ret = self._read_reply()
            if 'error' in ret:
                self.logger.error(ret['error'])
            else:
                time.sleep(0.5)
                cur_pos = ret['data']
                self.logger.debug(cur_pos)
                if cur_pos != pos:
                    self.logger.error("Position not achieved!")
                self.get_attenuation()
                return {'data': cur_pos}

        return ret

    def step(self, direction:str = 'F'):
        """
        Move stage to relative position and return when in position
        :param direction: String, 'F' - forward or 'B' - backward
        :return: dictionary {'data|error': current_position|string_message}
        """
        direc = direction.upper()
        # check inputs
        if direc not in ['F', 'B']:
            self.logger.error("Invalid direction: use F or B")
            return {'error': 'Invalid direction'}

        ret = self._send_command(direc)
        if 'data' in ret:
            ret = self._read_reply()
            if 'error' in ret:
                self.logger.error(ret['error'])
            else:
                self.logger.debug(ret['data'])
                cur_pos = ret['data']
                if cur_pos != self.current_position:
                    self.logger.error("Position setting not achieved!")
                    self.current_position = cur_pos
                return {'data': cur_pos}
        return ret

    def get_position(self):
        """ Current position

        :return: dictionary {'data|error': current_position|string_message}
        """

        ret = self._send_command("S?")
        if 'data' in ret:
            ret = self._read_reply()
            if 'error' in ret:
                self.logger.error(ret['error'])
            else:
                self.logger.debug(ret['data'])
        return ret

    def get_attenuation(self):
        """ Current attenuation

        :return: dictionary {'data|error': current_attenuation|string_message}
        """

        ret = self._send_command("A?")
        if 'data' in ret:
            ret = self._read_reply()
            if 'error' in ret:
                self.logger.error(ret['error'])
            else:
                self.logger.debug(ret['data'])
        return ret

    def reset(self):
        """ Reset stage

        :return: return from __send_command
        """

        ret = self._send_command("RS")
        time.sleep(2.)

        if 'data' in ret:
            ret = self._read_reply()
            if 'error' in ret:
                self.logger.error(ret['error'])
            else:
                self.logger.debug(ret['data'])

        return ret

    def get_params(self):
        """ Get stage parameters

        :return: return from __send_command
        """

        ret = self._send_command("CD")

        if 'data' in ret:
            ret = self._read_reply()
            if 'error' in ret:
                self.logger.error(ret['error'])
            else:
                self.logger.debug(ret['data'])
                self.configuration = ret['data']

        return ret

    def initialize_controller(self):
        """ Initialize stage controller. """
        ret = self.home()
        if 'error' in ret:
            self.logger.error(ret['error'])
        return ret

    def read_from_controller(self):
        """ Read from controller"""
        self.socket.setblocking(False)
        try:
            recv = self.socket.recv(2048)
            recv_len = len(recv)
            self.logger.debug("Return: len = %d, Value = %s", recv_len, recv)
        except BlockingIOError:
            recv = b""
        self.socket.setblocking(True)
        return str(recv.decode('utf-8'))

    def run_manually(self):
        """ Input stage commands manually

        :return: None
        """

        while True:

            cmd = input("Enter Command")

            if not cmd:
                break

            ret = self._send_command(cmd, custom_command=True)
            if 'error' not in ret:
                output = self.read_from_controller()
                self.logger.info(output)

            self.logger.info("End: %s", ret)
