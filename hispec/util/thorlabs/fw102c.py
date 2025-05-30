#! @KPYTHON3@
""" Thorlabs FW102C controller class """
from errno import ETIMEDOUT, EISCONN
import logging
import socket
import threading
import time

from hispec.util.helper import logger_utils


class FilterWheelController:
    """ Handle all correspondence with the serial interface of the
        Thorlabs FW102C filter wheel.
    """

    lock = threading.Lock()
    socket = None
    connected = False
    status = None
    current_position = 0
    ip = ''
    port = 0

    initialized = False
    revision = None
    success = False

    def __init__(self, log=True, logfile=None, quiet=False):

        # set up logging
        if log:
            if logfile is None:
                logfile = __name__.rsplit(".", 1)[-1] + ".log"
            self.logger = logger_utils.setup_logger(__name__, log_file=logfile)
            if quiet:
                self.logger.setLevel(logging.INFO)
        else:
            self.logger = None

    def set_connection(self, ip=None, port=None):
        """ Configure the connection to the controller."""
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
        """ Set the status of the filter wheel. """

        status = status.lower()

        if self.status is None:
            current = None
        else:
            current = self.status

        if current != 'locked' or status == 'unlocked':
            self.status = status


    def initialize(self):
        """ Initialize the filter wheel. """

        save = False

        # Give it an initial dummy command to flush out the buffer.
        self.command('*idn?')

        self.revision = self.command('*idn?')

        # Turn off the position sensors when the wheel is
        # idle to mitigate stray light.

        sensors = self.command('sensors?')

        if sensors != '0':
            self.command('sensors=0')
            save = True

        # Make sure the wheel is set to move at "high" speed,
        # which takes ~3 seconds to rotate 180 degrees.

        speed = self.command('speed?')

        if speed != '1':
            self.command('speed=1')
            save = True

        # Make sure the external trigger is in 'output' mode.

        trigger = self.command('trig?')

        if trigger != '1':
            self.command('trig=1')
            save = True

        if save is True:
            self.command('save')

        self.initialized = True


    def command(self, command):
        """ Wrapper to issueCommand(), ensuring the command lock is
            released if an exception occurs.
        """

        try:
            result = self.issue_command(command)
        except:
            self.lock.acquire(False)
            self.lock.release()
            if not self.connected:
                self.initialized = False
            self.success = False
            self.check_status()
            raise

        self.success = True
        self.check_status()

        return result

    def issue_command(self, command):
        """ Wrapper to send/receive with error checking and retries.
        """

        if not self.connected:
            self.set_status('connecting')
            self.connect()
            self.set_status('ready')

        retries = 3
        reply = ''
        send_command = f"{command}\r"
        send_command = send_command.encode('utf-8')

        self.lock.acquire()

        while retries > 0:
            self.logger.info("sending command %s", send_command)
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

            # Wait for a reply.
            delimiter = '>'

            if 'pos=' in command:
                # The next response will wait
                # until the filter wheel is
                # actually in position.
                timeout = 5
            else:
                timeout = 1

            start = time.time()
            time.sleep(0.1)
            reply = self.socket.recv(1024)
            while delimiter not in reply and time.time() - start < timeout:
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

        self.lock.release()

        if isinstance(reply, str):
            reply = reply.strip()
        else:
            reply = reply.decode('utf-8')

        if retries == 0:
            raise RuntimeError('unable to successfully issue command: ' + repr(command))

        # For a command with a reply, the response always looks like:
        #
        #    command\rreply\r>
        #
        # For commands that do not have a reply, the response is:
        #
        #    command\r>

        if command[-1] == '?':
            expected = 3
        else:
            expected = 2

        chunks = reply.split('\r')

        if len(chunks) != expected:
            raise ValueError('unexpected number of fields in response: ' + repr(reply))

        if expected == 3:
            return chunks[1]

        return None

    def get_position(self):
        """ Get the current position from the controller."""
        return self.command('pos?')

    def move(self, target):
        """ Move the filter wheel to the target position."""
        if not self.initialized:
            self.initialize()

        target = int(target)
        command = f"pos={target:d}"

        response = self.command(command)

        if response is not None:
            raise RuntimeError('error response to command: ' + response)


        current = self.get_position()
        current = int(current)

        if current != target:
            raise RuntimeError(
                f"wound up at position {response:d} instead of commanded {target:d}")

# end of class Controller
