import hispec.util.helper.logger_utils as logger_utils
import json
import os
from pipython import GCSDevice, GCSError


class PIControllerBase:
    """
    Base class for communicating with a PI (Physik Instrumente) motion controller using pipython.
    """

    def __init__(self, quiet=False):
        self.device = GCSDevice()
        self.connected = False
        self.named_positions = {}
        self.named_position_file = 'config/pi_named_positions.json'

        logfile = __name__.rsplit(".", 1)[-1] + ".log"
        self.logger = logger_utils.setup_logger(__name__, log_file=logfile, quiet=quiet)

    def connect_tcp(self, ip, port=50000) -> None:
        """
        Connect to the PI controller via TCP/IP.
        """
        self.device.ConnectTCPIP(ip, port)
        self.connected = True
        self.logger.info(f"Connected to PI controller at {ip}:{port}")

    def disconnect(self) -> None:
        """
        Close the connection to the controller.
        """
        self.device.CloseConnection()
        self.connected = False
        self.logger.info("Disconnected from PI controller")
        
    def is_connected(self) -> bool:
        """
        Check if the controller is connected.
        """
        return self.connected
    
    def get_idn(self) -> str:
        """
        Query the device identification string.
        """
        if not self.is_connected():
            raise Exception('PI device is not connected')
        return self.device.qIDN()

    def get_serial_number(self) -> str:
        """
        Extract and return the serial number from the IDN string.
        """
        idn = self.get_idn()
        return idn.split(',')[-2].strip()

    def get_axes(self) -> str:
        """
        Get a string of available axes.
        """
        if not self.is_connected():
            raise Exception('PI device is not connected')
        return self.device.axes

    def get_position(self, axis_number):
        """
        Get the current position of a specified axis by index.
        """
        if not self.is_connected():
            raise Exception('PI device is not connected')

        try:
            axis = self.device.axes[axis_number]
            return self.device.qPOS(axis)[axis]
        except (GCSError, IndexError) as e:
            print(f'Error getting position: {e}')
            return None

    def servo_status(self, axis):
        """
        Check if the servo on the given axis is enabled.
        """
        if not self.is_connected():
            raise Exception('PI device is not connected')
        try:
            return bool(self.device.qSVO(axis)[axis])
        except GCSError as e:
            self.logger.error(f'Error checking servo status: {e}')
            return False
        
    def get_error_code(self):
        """
        Get the last error code from the controller.
        """
        if not self.is_connected():
            raise Exception('PI device is not connected')
        try:
            return self.device.qERR()
        except GCSError as e:
            self.logger.error(f'Error getting error code: {e}')
            return None
    
    def halt_motion(self):
        """
        Stop all motions immediately.
        """
        if not self.is_connected():
            raise Exception('PI device is not connected')
        try:
            self.device.HLT()
        except GCSError as e:
            self.logger.error(f'Error halting motion: {e}')

    def set_position(self, axis, position):
        """
        Move the specified axis to the given position.
        """
        if not self.is_connected():
            raise Exception('PI device is not connected')
        try:
            self.device.MOV(axis, position)
        except GCSError as e:
            self.logger.error(f'Error setting position: {e}')

    def set_named_position(self, axis, name):
        """
        Save the current position of the axis under a named label, scoped to the controller serial number.
        """
        pos = self.get_position(self.device.axes.index(axis))
        if pos is None:
            self.logger.warning(f"Could not get position for axis {axis}")
            return

        serial = self.get_serial_number()
        positions = {}

        if os.path.exists(self.named_position_file):
            with open(self.named_position_file, "r") as f:
                try:
                    positions = json.load(f)
                except json.JSONDecodeError:
                    self.logger.warning(f"Could not parse JSON from {self.named_position_file}")

        if serial not in positions:
            positions[serial] = {}

        positions[serial][name] = [axis, pos]

        with open(self.named_position_file, "w") as f:
            json.dump(positions, f, indent=2)

        self.logger.info(f"Saved position '{name}' for controller {serial}, axis {axis}: {pos}")


    def go_to_named_position(self, name):
        """
        Load a named position for the current controller from file and move the corresponding axis to it.
        """
        serial = self.get_serial_number()

        if not os.path.exists(self.named_position_file):
            self.logger.warning(f"Named positions file not found: {self.named_position_file}")
            return

        try:
            with open(self.named_position_file, "r") as f:
                positions = json.load(f)
        except json.JSONDecodeError:
            self.logger.warning(f"Failed to read positions from {self.named_position_file}")
            return

        if serial not in positions:
            self.logger.warning(f"No named positions found for controller {serial}")
            return

        if name not in positions[serial]:
            self.logger.warning(f"Named position '{name}' not found for controller {serial}")
            return

        axis, pos = positions[serial][name]
        self.set_position(axis, pos)
        self.logger.info(f"Moved axis {axis} to named position '{name}' for controller {serial}: {pos}")


    # TODO
    def is_moving(self, axis, position_name):
        raise NotImplementedError("is_moving is not implemented")
