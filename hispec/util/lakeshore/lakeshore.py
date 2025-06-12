#! @KPYTHON3@
""" Lakeshore 224/336 controller class """

from errno import ETIMEDOUT, EISCONN
import logging
import socket
import threading
import time

from hispec.util.helper import logger_utils


class LakeshoreController:
    """ Handle all correspondence with the ethernet interface of the
        Lakeshore 224/336 controller.
    """

    connected = False
    status = None
    ip = ''
    port = 0

    initialized = False
    revision = None
    success = False
    termchars = '\r\n'

    # Heater dictionaries
    resistance = {'1': 25, '2': 50}
    max_current = {'0': 0.0, '1': 0.707, '2': 1.0, '3': 1.141, '4': 2.0}
    htr_display = {'1': 'current', '2': 'power'}
    htr_errors = {'0': 'no error', '1': 'heater open load', '2': 'heater short'}

    def __init__(self, log=True, logfile=None, quiet=False, opt3062=False,
                 model336=True):

        self.lock = threading.Lock()
        self.socket = None

        self.celsius = True
        self.model336 = model336

        # set up logging
        if log:
            if logfile is None:
                logfile = __name__.rsplit(".", 1)[-1] + ".log"
            self.logger = logger_utils.setup_logger(__name__, log_file=logfile)
            if quiet:
                self.logger.setLevel(logging.INFO)
        else:
            self.logger = None

        if model336:
            if opt3062:
                self.sensors = {'A': 1, 'B': 2, 'C': 3,
                                'D1': 4, 'D2': 5, 'D3': 6, 'D4': 7, 'D5': 8}
            else:
                self.sensors = {'A': 1, 'B': 2, 'C': 3, 'D': 4}

            self.outputs = {'1':
                                {'resistance': None, 'max_current': 0.0,
                                 'user_max_current': 0.0, 'htr_display': '',
                                 'status': ''},
                            '2':
                                {'resistance': None, 'max_current': 0.0,
                                 'user_max_current': 0.0, 'htr_display': '',
                                 'status': ''},
            }
        else:
            # Model 224
            self.sensors = {'A':1, 'B':2,
                            'C1': 3, 'C2': 4, 'C3': 5, 'C4': 6, 'C5': 7,
                            'D1': 8, 'D2': 9, 'D3': 10, 'D4': 11, 'D5': 12}
            self.outputs = None

    def set_connection(self, ip=None, port=None):
        """ Configure the connection to the controller.

        :param ip: String, IP address of the controller.
        :param port: Int, port number of the controller.

        """
        self.ip = ip
        self.port = port

    def disconnect(self):
        """ Disconnect controller. """

        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.socket = None
            if self.logger:
                self.logger.debug("Disconnected controller")
            self.connected = False
            self.success = True

        except OSError as e:
            if self.logger:
                self.logger.error("Disconnection error: %s", e.strerror)
            self.connected = False
            self.socket = None
            self.success = False

        self.set_status("disconnected")

    def connect(self):
        """ Connect to controller. """
        if self.socket is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((self.ip, self.port))
            if self.logger:
                self.logger.debug("Connected to %(host)s:%(port)s", {
                    'host': self.ip,
                    'port': self.port
                })
            self.connected = True
            self.success = True
            self.set_status('ready')

        except OSError as e:
            if e.errno == EISCONN:
                if self.logger:
                    self.logger.debug("Already connected")
                self.connected = True
                self.success = True
                self.set_status('ready')
            else:
                if self.logger:
                    self.logger.error("Connection error: %s", e.strerror)
                self.connected = False
                self.success = False
                self.set_status('not connected')
        # clear socket
        if self.connected:
            self.__clear_socket()

    def __clear_socket(self):
        """ Clear socket buffer. """
        if self.socket is not None:
            self.socket.setblocking(False)
            while True:
                try:
                    _ = self.socket.recv(1024)
                except BlockingIOError:
                    break
            self.socket.setblocking(True)

    def check_status(self):
        """ Check connection status """
        if not self.connected:
            status = 'not connected'
        elif not self.success:
            status = 'unresponsive'
        else:
            status = 'ready'

        self.set_status(status)


    def set_status(self, status):
        """ Set the status of the filter wheel.

        :param status: String, status of the controller.

        """

        status = status.lower()

        if self.status is None:
            current = None
        else:
            current = self.status

        if current != 'locked' or status == 'unlocked':
            self.status = status


    def initialize(self, celsius=True):
        """ Initialize the lakeshore status. """

        self.revision = self.command('*idn?')

        if self.model336:

            for htr in self.outputs.keys():
                res, maxc, umaxc, disp = self.get_heater_settings(htr)
                status = self.get_heater_status(htr)
                self.outputs[htr]['resistance'] = self.resistance[res]
                self.outputs[htr]['max_current'] = self.max_current[maxc]
                self.outputs[htr]['user_max_current'] = float(umaxc)
                self.outputs[htr]['htr_display'] = self.htr_display[disp]
                self.outputs[htr]['status'] = status

        if celsius:
            self.set_celsius()
        else:
            self.set_kelvin()

        self.initialized = True


    def command(self, command, params=None):
        """ Wrapper to issue_command(), ensuring the command lock is
            released if an exception occurs.

        :param command: String, command to issue.
        :param params: String, parameters to issue.

        """

        with self.lock:
            try:
                result = self.issue_command(command, params)
                self.success = True
            finally:
                # Ensure that status is always checked, even on failure
                self.check_status()

        return result

    def issue_command(self, command, params=None):
        """ Wrapper to send/receive with error checking and retries.

        :param command: String, command to issue.
        :param params: String, parameters to issue.

        """

        if not self.connected:
            self.set_status('connecting')
            self.connect()

        retries = 3
        reply = ''
        if params:
            send_command = f"{command} {params}{self.termchars}".encode('utf-8')
        else:
            send_command = f"{command}{self.termchars}".encode('utf-8')

        while retries > 0:
            self.logger.debug("sending command %s", send_command)
            try:
                self.socket.send(send_command)

            except socket.error:
                self.logger.error(
                    "Failed to send command, re-opening socket, %d retries remaining", retries)
                self.disconnect()
                try:
                    self.connect()
                except OSError:
                    self.logger.error(
                        'Could not reconnect to controller, aborting')
                    return None
                retries -= 1
                continue

            # Get a reply, if needed.
            if command[-1] == '?':
                timeout = 1
                start = time.time()
                reply = self.socket.recv(1024)
                while self.termchars not in reply.decode('utf-8') and \
                        time.time() - start < timeout:
                    try:
                        reply += self.socket.recv(1024)
                        self.logger.debug("reply: %s", reply)
                    except OSError as e:
                        if e.errno == ETIMEDOUT:
                            reply = ''
                    time.sleep(0.1)

                if reply == '':
                    # Don't log here, because it happens a lot when the controller
                    # is unresponsive. Just try again.
                    retries -= 1
                    continue
                break
            break

        if isinstance(reply, str):
            reply = reply.strip()
        else:
            reply = reply.decode('utf-8').strip()

        if retries == 0:
            raise RuntimeError('unable to successfully issue command: ' + repr(command))

        return reply

    def set_celsius(self):
        """ Set units to Celsius. """
        self.celsius = True

    def set_kelvin(self):
        """ Set units to Kelvin. """
        self.celsius = False

    def get_temperature(self, sensor):
        """ Get sensor temperature.

        :param sensor: String, name of the sensor: A-D or A-C, D1=D5.

        """
        retval = None
        if sensor.upper() not in self.sensors:
            self.logger.error("Sensor %s is not available", sensor)
        else:
            if self.celsius:
                reply = self.command('crdg?', sensor)
                if len(reply) > 0:
                    retval = float(reply)
            else:
                reply = self.command('krdg?', sensor)
                if len(reply) > 0:
                    retval = float(reply)
        return retval

    def get_heater_settings(self, output):
        """ Get heater settings.
        :param output: String, output number of the sensor (1 or 2).
        1,3,+1.414,1
        """
        retval = None
        if self.model336:
            if output.upper() not in self.outputs:
                self.logger.error("Heater %s is not available", output)
            else:
                reply = self.command('htrset?', output)
                if len(reply) > 0:
                    retval = reply.split(',')
        else:
            self.logger.error("Heater is not available with this model")
        return retval

    def get_heater_status(self, output):
        """ Get heater status.

        :param output: String, output number of the sensor (1 or 2).
        returns status string
        """
        retval = 'unknown'
        if self.model336:
            if output.upper() not in self.outputs:
                self.logger.error("Heater %s is not available", output)
            else:
                reply = self.command('htrst?', output)
                if len(reply) > 0:
                    reply = reply.strip()
                    if reply in self.htr_errors:
                        retval = self.htr_errors[reply]
                    else:
                        self.logger.error("Heater error %s and status is unknown",
                                          reply)
        else:
            self.logger.error("Heater is not available with this model")
        return retval

    def get_heater_output(self, output):
        """ Get heater output.
        :param output: String, output number of the sensor (1 or 2).
        """
        retval = None
        if self.model336:
            if output.upper() not in self.outputs:
                self.logger.error("Heater %s is not available", output)
            else:
                reply = self.command('htr?', output)
                if len(reply) > 0:
                    reply = reply.strip()
                    try:
                        retval = float(reply)
                    except ValueError:
                        self.logger.error("Heater output error: %s", reply)
                else:
                    self.logger.error("Heater output error")
        else:
            self.logger.error("Heater is not available with this model")
        return retval
# end of class Controller
