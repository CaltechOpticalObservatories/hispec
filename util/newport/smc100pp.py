# coding=utf-8
"""
The following stage controller commands are available. Note that many
are not implemented at the moment.  The asterisk indicates the commands
that are implemented.

AC    Set/Get acceleration
BA    Set/Get backlash compensation
BH    Set/Get hysteresis compensation
DV    Set/Get driver voltage Not for PP
FD    Set/Get low pass filter for Kd Not for PP
FE    Set/Get following error limit Not for PP
FF    Set/Get friction compensation Not for PP
FR    Set/Get stepper motor configuration Not for CC
HT    Set/Get HOME search type
ID    Set/Get stage identifier
JD    Leave JOGGING state
JM    Enable/disable keypad
JR    Set/Get jerk time
KD    Set/Get derivative gain Not for PP
KI    Set/Get integral gain Not for PP
KP    Set/Get proportional gain Not for PP
KV    Set/Get velocity feed forward Not for PP
MM    Enter/Leave DISABLE state
OH    Set/Get HOME search velocity
OR  * Execute HOME search
OT    Set/Get HOME search time-out
PA  * Move absolute
PR  * Move relative
PT    Get motion time for a relative move
PW    Enter/Leave CONFIGURATION state
QI    Set/Get motor’s current limits
RA    Get analog input value
RB    Get TTL input value
RS  * Reset controller
SA    Set/Get controller’s RS-485 address
SB    Set/Get TTL output value
SC    Set/Get control loop state Not for PP
SE    Configure/Execute simultaneous started move
SL  * Set/Get negative software limit
SR  * Set/Get positive software limit
ST    Stop motion
SU    Set/Get encoder increment value Not for PP
TB    Get command error string
TE  * Get last command error
TH    Get set-point position
TP  * Get current position
TS  * Get positioner error and controller state
VA    Set/Get velocity
VB    Set/Get base velocity Not for CC
VE    Get controller revision information
ZT  * Get all axis parameters
ZX    Set/Get SmartStage configuration

The values below as of 2025-Apr-30

For stage 1 & 2 current values are:
80 - Acceleration
-3600 - negative software limit, from 1SL?
+3600 - positive software limit, from 1SR?
1.76994e-05 - units per encoder increment, from 1SU?

"""
import errno
import logging
import time
import socket
import sys

class StageController:
    """
    Controller class for Newport SMC100PP Stage Controller.
    """

    controller_commands = ["OR",    # Execute HOME search
                           "PA",    # Absolute move
                           "PR",    # Move relative
                           "RS",    # Reset controller
                           "SL",    # Set/Get positive software limit
                           "SR",    # Set/Get negative software limit
                           "TE",    # Get last command error
                           "TP",    # Get current position
                           "TS",    # Get positioner error and controller state
                           "ZT"     # Get all axis parameters
                           ]
    return_value_commands = ["TE", "TP", "TS"]
    parameter_commands = ["PA", "PR"]
    end_code_list = ['32', '33', '34', '35']
    not_ref_list = ['0A', '0B', '0C', '0D', '0F', '10', '11']
    moving_list = ['28']
    msg = {
        "0A": "NOT REFERENCED from reset.",
        "0B": "NOT REFERENCED from HOMING.",
        "0C": "NOT REFERENCED from CONFIGURATION.",
        "0D": "NOT REFERENCED from DISABLE.",
        "0E": "NOT REFERENCED from READY.",
        "0F": "NOT REFERENCED from MOVING.",
        "10": "NOT REFERENCED ESP stage error.",
        "11": "NOT REFERENCED from JOGGING.",
        "14": "CONFIGURATION.",
        "1E": "HOMING commanded from RS-232-C.",
        "1F": "HOMING commanded by SMC-RC.",
        "28": "MOVING.",
        "32": "READY from HOMING.",
        "33": "READY from MOVING.",
        "34": "READY from DISABLE.",
        "35": "READY from JOGGING.",
        "3C": "DISABLE from READY.",
        "3D": "DISABLE from MOVING.",
        "3E": "DISABLE from JOGGING.",
        "46": "JOGGING from READY.",
        "47": "JOGGING from DISABLE."
    }
    error = {
        "@": "No error.",
        "A": "Unknown message code or floating point controller address.",
        "B": "Controller address not correct",
        "C": "Parameter missing or out of range.",
        "D": "Command not allowed.",
        "E": "Home sequence already started.",
        "F": "ESP stage name unknown.",
        "G": "Displacement out of limits.",
        "H": "Command not allowed in NOT REFERENCED state.",
        "I": "Command not allowed in CONFIGURATION state.",
        "J": "Command not allowed in DISABLE state.",
        "K": "Command not allowed in READY state.",
        "L": "Command not allowed in HOMING state.",
        "M": "Command not allowed in MOVING state.",
        "N": "Current position out of software limit.",
        "S": "Communication Time Out.",
        "U": "Error during EEPROM access.",
        "V": "Error durring command execution.",
        "W": "Command not allowed for PP version.",
        "X": "Command not allowed for CC version."
    }
    last_error = ""

    def __init__(self, num_stages=2, move_rate=5.0, log=True):

        """
        Class to handle communications with the stage controller and any faults

        :param num_stages: Int, number of stages daisey-chained
        :param move_rate: Float, move rate in degrees per second
        """

        # Set up socket
        self.socket = None
        self.connected = False

        # number of daisy-chained stages
        self.num_stages = num_stages

        # stage rate in degrees per second
        self.move_rate = move_rate

        # current position
        self.current_position = [0.0, 0.0, 0.0]

        self.custom_command = False

        if log:
            logname = __name__.rsplit(".", 1)[-1]
            self.logger = logging.getLogger(logname)
            self.logger.setLevel(logging.DEBUG)
            logging.Formatter.converter = time.gmtime
            log_handler = logging.FileHandler(logname + ".log")

            formatter = logging.Formatter(
                "%(asctime)s--%(name)s--%(levelname)s--"
                "%(module)s--%(funcName)s--%(message)s")
            log_handler.setFormatter(formatter)
            log_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(log_handler)

            console_formatter = logging.Formatter("%(asctime)s--%(message)s")
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

            self.logger.info("Starting Logger: Logger file is %s",
                        logname + ".log")
        else:
            self.logger = None

    def connect(self, ip=None, port=None):
        """ Connect to stage controller.

        :param ip: String, host ip address
        :param port: Int, Port number
        """
        start = time.time()
        if self.socket is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((ip, port))
            if self.logger:
                self.logger.info("Connected to %(host)s:%(port)s", {
                    'host': ip,
                    'port': port
                })
            self.connected = True
            ret = {'elaptime': time.time()-start, 'data': 'connected'}
        except OSError as e:
            if e.errno == errno.EISCONN:
                if self.logger:
                    self.logger.info("Already connected")
                self.connected = True
                ret = {'elaptime': time.time()-start, 'data': 'already connected'}
            else:
                if self.logger:
                    self.logger.error("Connection error: %s", e.strerror)
                self.connected = False
                ret = {'elaptime': time.time()-start, 'error': e.strerror}
        return ret

    def disconnect(self):
        """ Disconnect stage controller. """
        start = time.time()
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.socket = None
            if self.logger:
                self.logger.info("Disconnected controller")
            self.connected = False
            ret = {'elaptime': time.time()-start, 'data': 'disconnected'}
        except OSError as e:
            if self.logger:
                self.logger.info("Disconnection error: %s", e.strerror)
            self.connected = False
            self.socket = None
            ret = {'elaptime': time.time()-start, 'error': e.strerror}

        return ret

    def __read_value(self):
        # Return value commands

        # Get return value
        recv = self.socket.recv(2048)
        recv_len = len(recv)
        if self.logger:
            self.logger.info("Return: len = %d, Value = %s", recv_len, recv)

        # Are we a valid return value?
        if recv_len in [6, 11, 12, 13, 14]:
            if self.logger:
                self.logger.info("Return value validated")
        return str(recv.decode('utf-8'))

    def __read_params(self):

        # Get return value
        recv = self.socket.recv(2048)

        # Did we get all the params?
        t = 5
        while t > 0 and b'PW0' not in recv:
            recv += self.socket.recv(2048)
            t -= 1

        if b'PW0' in recv:
            recv_len = len(recv)
            if self.logger:
                self.logger.info("ZT Return: len = %d", recv_len)
        else:
            if self.logger:
                self.logger.warning("ZT command timed out")

        return str(recv.decode('utf-8'))

    def __read_blocking(self, stage_id=1, timeout=15):
        # Non-return value commands eventually return state output
        sleep_time = 0.1
        start_time = time.time()
        print_it = 0
        recv = None
        while time.time() - start_time < timeout:
            # Check state
            statecmd = f'{stage_id}TS\r\n'
            statecmd = statecmd.encode('utf-8')
            self.socket.send(statecmd)
            time.sleep(sleep_time)
            recv = self.socket.recv(1024)

            # Valid state return
            if len(recv) == 11:
                # Parse state
                recv = recv.rstrip()
                code = str(recv[-2:].decode('utf-8'))

                # Valid end code or not referenced code (done)
                if code in self.end_code_list or code in self.not_ref_list:
                    return str(recv.decode('utf-8'))

                if print_it >= 10:
                    msg = (f"{time.time()-start_time:05.2f} "
                           f"{self.msg.get(code, 'Unknown state'):s}")
                    if self.logger:
                        self.logger.info(msg)
                    else:
                        print(msg)
                    print_it = 0

            # Invalid state return (done)
            else:
                if self.logger:
                    self.logger.warning("Bad %dTS return: %s", stage_id, recv)
                return str(recv.decode('utf-8'))

            # Increment tries and read state again
            print_it += 1

        # If we get here, we ran out of tries
        recv = recv.rstrip()
        code = str(recv[-2:].decode('utf-8'))
        if self.logger:
            self.logger.warning("Command timed out, final state: %s",
                           self.msg.get(code, "Unknown state"))
        return str(recv.decode('utf-8'))

    def __send_serial_command(self, stage_id=1, cmd=''):
        """
        Send serial command to stage controller

        :param stage_id: Int, stage position in the daisy chain starting with 1
        :param cmd: String, command to send to stage controller
        :return: 
        """

        start = time.time()

        # Prep command
        cmd_send = f"{stage_id}{cmd}\r\n"
        if self.logger:
            self.logger.info("Sending command:%s", cmd_send)
        cmd_encoded = cmd_send.encode('utf-8')

        # check connection
        if not self.connected:
            msg_type = 'error'
            msg_text = "Not connected to controller!"
            if self.logger:
                self.logger.error(msg_text)

        try:
            self.socket.settimeout(30)
            # Send command
            self.socket.send(cmd_encoded)
            time.sleep(.05)
            msg_type = 'data'
            msg_text = 'Command sent successfully'

        except socket.error as e:
            msg_type = 'error'
            msg_text = f"Command send error: {e.strerror}"
            if self.logger:
                self.logger.error(msg_text)

        return {'elaptime': time.time()-start, msg_type: msg_text}

    def __send_command(self, cmd="", parameters=None, stage_id=1):
        """
        Send a command to the stage controller

        :param cmd: String, command to send to the stage controller
        :param parameters: List of string parameters associated with cmd
        :param stage_id: Int, stage position in the daisy chain starting with 1
        :return: 
        """

        # verify cmd and stage_id
        ret = self.__verify_send_command(cmd, stage_id)
        if 'error' in ret:
            return ret

        # Check if the command should have parameters
        if cmd in self.parameter_commands and parameters:
            if self.logger:
                self.logger.info("Adding parameters")
            parameters = [str(x) for x in parameters]
            parameters = " ".join(parameters)
            cmd += parameters

        if self.logger:
            self.logger.info("Input command: %s", cmd)

        # Send serial command
        return self.__send_serial_command(stage_id, cmd, timeout)

        """
        response = str(response.decode('utf-8'))
        if self.logger:
            self.logger.info("Response from stage %d:\n%s",
                             stage_id, response)

        # Parse response
        message = self.__return_parse_state(response)

        # Next check if we expect a return value from command
        if cmd in self.return_value_commands:

            # Parse position return
            if cmd.upper() == 'TP':
                response = response.rstrip()
                msg_type = 'data'
                msg_text = response[3:]

            # Parse error return
            elif cmd.upper() == 'TE':
                response = response.rstrip()
                errmsg = self.__return_parse_error(response)
                msg_type = 'error'
                msg_text = errmsg

            # Return whole message (usually from TS)
            else:
                msg_type = 'data'
                msg_text = message

            return {'elaptime': time.time() - start, msg_type: msg_text}

        # Get parameters response
        if cmd.upper() == 'ZT':
            msg_type = 'data'
            msg_text = response.strip()
            return {'elaptime': time.time() - start, msg_type: msg_text}

        # Non-return value command, but stage in unknown state
        if cmd not in self.return_value_commands and message == "Unknown state":
            msg_type = 'error'
            msg_text = response
            return {'elaptime': time.time() - start, msg_type: msg_text}

        # Not referenced (needs to be homed)
        if 'REFERENCED' in message:
            if self.logger:
                self.logger.info("State is NOT REFERENCED, recommend homing")
            msg_type = 'error'
            msg_text = message
            return {'elaptime': time.time() - start, msg_type: msg_text}

        # Valid state achieved after command
        return {'elaptime': time.time() - start, 'data': message}
        """

    def __verify_send_command(self, cmd, stage_id):
        """ Verify cmd and stage_id

        :param cmd: String, command to send to the stage controller
        :param stage_id: Int, stage position in the daisy chain starting with 1
        :return: dictionary {'elaptime': time, 'data|error': string_message}"""

        start = time.time()

        # Do we have a connection?
        if not self.connected:
            msg_type = 'error'
            msg_text = 'Not connected to controller'

        # Is stage id valid?
        elif not self.__verify_stage_id(stage_id):
            msg_type = 'error'
            msg_text = f"{stage_id} is not a valid stage"

        else:
            # Do we have a legal command?
            if cmd.rstrip().upper() in self.controller_commands:
                msg_type = 'data'
                msg_text = f"{cmd} is a valid or custom command"
            else:
                if not self.custom_command:
                    msg_type = 'error'
                    msg_text = f"{cmd} is not a valid command"
                else:
                    msg_type = 'data'
                    msg_text = f"{cmd} is a custom command"

        return {'elaptime': time.time() - start, msg_type: msg_text}

    def __verify_stage_id(self, stage_id):
        """ Check that the stage id is legal

        :param stage_id: Int, stage position in the daisy chain starting with 1
        :return: True if stage id is legal
        """
        if stage_id > self.num_stages or stage_id < 1:
            is_valid = False
        else:
            is_valid = True

        return is_valid

    def __return_parse_state(self, message=""):
        """
        Parse the return message from the controller.  The message code is
        given in the last two string characters

        :param message: String message code from the controller
        :return: String message
        """
        message = message.rstrip()
        code = message[-2:]
        return self.msg.get(code, "Unknown state")

    def __return_parse_error(self, error=""):
        """
        Parse the return error message from the controller.  The message code is
        given in the last string character

        :param error: Error code from the controller
        :return: String message
        """
        error = error.rstrip()
        code = error[-1:]
        return self.error.get(code, "Unknown error")

    def home(self, stage_id=1):
        """
        Home the stage

        :param stage_id: Int, stage position in the daisy chain starting with 1
        :return: return from __send_command
        """
        return self.__send_command(cmd='OR', stage_id=stage_id)

    def move_abs(self, position=None, stage_id=None, blocking=False):
        """
        Move stage to absolute position and return when in position
        TODO: check limits on position

        :param position: Float, absolute position in degrees
        :param stage_id: Int, stage position in the daisy chain starting with 1
        :param blocking: Boolean, block until move complete or not
        :return: return from __send_command
        """

        start = time.time()

        if position is None or stage_id is None:
            return {'elaptime': time.time() - start,
                    'error': 'must specify both position and stage_id'}

        # Send move to controller 
        ret = self.__send_command(cmd="PA", parameters=[position],
                                  stage_id=stage_id)
 
        if blocking: 
            move_len = self.current_position[stage_id] - position
            if self.move_rate <= 0:
                timeout = 5
            else:
                timeout = int(abs(move_len / self.move_rate))
            if timeout <= 0:
                timeout = 5
            if self.logger:
                self.logger.info("Timeout for move to absolute position: %d s",
                                 timeout)
            ret = self.__read_blocking(stage_id=stage_id, timeout=timeout)

        if 'error' not in ret:
            self.current_position[stage_id] = position
            ret['elaptime'] = time.time() - start
        return ret

    def move_rel(self, position=0.0, stage_id=1, blocking=False):
        """
        Move stage to relative position and return when in position
        TODO: check limits on position

        :param position: Float, relative position in degrees
        :param stage_id: Int, stage position in the daisy chain starting with 1
        :param blocking: Boolean, block until move complete or not
        :return: return from __send_command
        """

        start = time.time()

        if position is None or stage_id is None:
            return {'elaptime': time.time() - start,
                    'error': 'must specify both position and stage_id'}

        ret = self.__send_command(cmd="PR", parameters=[position],
                                  stage_id=stage_id)

        if blocking:
            if self.move_rate <= 0:
                timeout = 5
            else:
                timeout = int(abs(position / self.move_rate))
            if timeout <= 0:
                timeout = 5
            if self.logger:
                self.logger.info("Timeout for move to relative position: %d s",
                                 timeout)
            ret = self.__read_blocking(stage_id=stage_id, timeout=timeout)

        if 'error' not in ret:
            self.current_position[stage_id] += position
            ret['elaptime'] = time.time() - start
        return ret

    def get_state(self, stage_id=1):
        """ Current state of the stage

        :param stage_id: int, stage position in the daisy chain starting with 1
        :return: return from __send_command
        """

        start = time.time()

        ret = self.__send_command(cmd="TS", stage_id=stage_id)
        if 'error' not in ret:
            state = self.__return_parse_state(self.__read_value())
            ret['data'] = state
            ret['elaptime'] = time.time() - start

        return ret

    def get_last_error(self, stage_id=1):
        """ Last error

        :param stage_id: int, stage position in the daisy chain starting with 1
        :return: return from __send_command
        """

        start = time.time()

        ret = self.__send_command(cmd="TE", stage_id=stage_id)
        if 'error' not in ret:
            last_error = self.__return_parse_error(self.__read_value())
            ret['data'] = last_error
            ret['elaptime'] = time.time() - start

        return ret

    def get_position(self, stage_id=1):
        """ Current position

        :param stage_id: int, stage position in the daisy chain starting with 1
        :return: return from __send_command
        """

        start = time.time()

        ret = self.__send_command(cmd="TP", stage_id=stage_id)
        if 'error' not in ret:
            position = float(self.__read_value().rstrip()[3:])
            self.current_position[stage_id] = position
            ret['data'] = position
            ret['elaptime'] = time.time() - start

        return ret

    def get_move_rate(self):
        """ Current move rate

        :return: return from __send_command
        """
        start = time.time()
        return {'elaptime': time.time()-start, 'data': self.move_rate}

    def set_move_rate(self, rate=5.0):
        """ Set move rate

        :param rate: Float, move rate in degrees per second
        :return: dictionary {'elaptime': time, 'data': move_rate}
        """
        start = time.time()
        if rate > 0:
            self.move_rate = rate
        else:
            if self.logger:
                self.logger.error('set_move_rate input error, not changed')
        return {'elaptime': time.time()-start, 'data': self.move_rate}

    def reset(self, stage_id=1):
        """ Reset stage

        :param stage_id: int, stage position in the daisy chain starting with 1
        :return: return from __send_command
        """
        return self.__send_command(cmd="RS", stage_id=stage_id)

    def get_params(self, stage_id=1):
        """ Get stage parameters

        :param stage_id: int, stage position in the daisy chain starting with 1
        :return: return from __send_command
        """

        start = time.time()

        ret = self.__send_command(cmd="ZT", stage_id=stage_id)

        if 'error' not in ret:
            params = self.__read_params()
            ret['data'] = params
            ret['elaptime'] = time.time() - start

        return ret

    def run_manually(self, stage_id=1):
        """ Input stage commands manually

        :param stage_id: int, stage position in the daisy chain starting with 1
        :return: None
        """
        while True:

            cmd = input("Enter Command")

            if not cmd:
                break

            self.custom_command = True
            ret = self.__send_command(cmd=cmd, stage_id=stage_id)
            self.custom_command = False
            if self.logger:
                self.logger.info("End: %s", ret)
