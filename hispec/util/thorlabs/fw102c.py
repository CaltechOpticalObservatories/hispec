#! @KPYTHON3@
#
# kpython safely sets RELDIR, KROOT, LROOT, and PYTHONPATH before invoking
# the actual Python interpreter.

#
# #
# Required libraries.
# #
#

import configparser
import logging
import socket
import threading

from hispec.util.helper import logger_utils
#
# #
# Controller classes.
# #
#

class FilterWheel:

    def __init__(self, configuration, section):

        address = configuration.get(section, 'address')
        locked = False
        name = configuration.get(section, 'name')
        port = configuration.get(section, 'port')
        status = name + 'STA'

        self.name = name
        self.section = section


        self.controller = FilterWheelController(address, port, status)
        self.check_status = self.controller.check_status
        self.set_status = self.controller.set_status

    def initialize_controller(self):

        self.controller.initialize()


    def current(self):

        if not self.controller.initialized:
            self.initialize_controller()

        return self.controller.command('pos?')


    def move(self, target):

        if not self.controller.initialized:
            self.initialize_controller()

        target = int(target)
        command = "pos=%d" % (target)

        response = self.controller.command(command)

        if response is not None:
            raise RuntimeError('error response to command: ' + response)


        current = self.current()
        current = int(current)

        if current != target:
            raise RuntimeError(
                "wound up at position %d instead of commanded %d" %
                (response, target))


# end of class FilterWheel



class FilterWheelController:
    """ Handle all corresponence with the serial interface of the
        Thorlabs filter wheel.
    """

    def __init__(self, log=True, logfile=None, quiet=False):

        self.lock = threading.Lock()
        self.socket = None
        self.connected = False
        self.status = None
        self.current_position = 0

        self.initialized = False
        self.revision = None
        self.success = False

        # set up logging
        if log:
            if logfile is None:
                logfile = __name__.rsplit(".", 1)[-1] + ".log"
            self.logger = logger_utils.setup_logger(__name__, log_file=logfile)
            if quiet:
                self.logger.setLevel(logging.INFO)
        else:
            self.logger = None

    def check_status(self):

        if not self.socket.connected:
            status = 'not connected'
        elif not self.success:
            status = 'unresponsive'
        else:
            status = 'ready'

        self.set_status(status)


    def set_status(self, status):

        """
        if isinstance(self.status, str):
            try:
                self.status = main.Service[self.status]
            except TypeError:
                # Not done initializing yet.
                return
        """

        status = status.lower()

        if self.status.value is None:
            current = None
        else:
            current = self.status.mapped(lower=True)

        if current != 'locked' or status == 'unlocked':
            self.status.set(status)


    def initialize(self):

        save = False
        command = self.command

        # Give it an initial dummy command to flush out the buffer.
        command('*idn?')

        self.revision = command('*idn?')


        # Turn off the position sensors when the wheel is
        # idle to mitigate stray light.

        sensors = command('sensors?')

        if sensors != '0':
            command('sensors=0')
            save = True


        # Make sure the wheel is set to move at "high" speed,
        # which takes ~3 seconds to rotate 180 degrees.

        speed = command('speed?')

        if speed != '1':
            command('speed=1')
            save = True


        # Make sure the external trigger is in 'output' mode.

        trigger = command('trig?')

        if trigger != '1':
            command('trig=1')
            save = True

        if save is True:
            command('save')

        self.initialized = True


    def command(self, command, response=False):
        """ Wrapper to issueCommand(), ensuring the command lock is
            released if an exception occurs.
        """

        try:
            result = self.issueCommand(command, response)
        except:
            self.lock.acquire(False)
            self.lock.release()
            if not self.socket.connected:
                self.initialized = False
            self.success = False
            self.check_status()
            raise

        self.success = True
        self.check_status()

        return result


    def issue_command(self, command, response):
        """ Wrapper to send/receive with error checking and retries.
        """

        if not self.socket.connected:
            self.set_status('connecting')
            self.socket.connect()
            self.set_status('ready')

        retries = 3

        self.lock.acquire()


        while retries > 0:
            try:
                self.socket.send(command)

            except socket.error:
                self.logger.error(
                    "Failed to send command, re-opening socket, %d retries remaining" % retries)
                self.socket.disconnect()
                try:
                    self.socket.connect()
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

            try:
                reply = self.socket.receive(delimiter, timeout)
            except self.socket.TimeoutError:
                reply = ''

            if reply == '':
                # Don't log here, because it happens a lot when the controller
                # is unresponsive. Just try again.
                retries -= 1
                continue

        self.lock.release()



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
        else:
            return None


# end of class Controller
