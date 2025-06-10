from pipython import GCSDevice, GCSError
import hispec.util.helper.logger_utils as logger_utils
import json
import os
import time


class PIControllerBase:
    """
    Base class for communicating with PI (Physik Instrumente) motion controllers daisy-chained over TCP/IP via a terminal server.
    """

    def __init__(self, quiet=False):
        """
        Initialize the controller, set up logging, and prepare device storage.
        """
        self.devices = {}  # {(ip, port, device_id): GCSDevice instance}
        self.daisy_chains = {}  # {(ip, port): [(device_id, desc)]}
        self.connected = False
        self.named_position_file = 'config/pi_named_positions.json'

        logfile = __name__.rsplit(".", 1)[-1] + ".log"
        self.logger = logger_utils.setup_logger(__name__, log_file=logfile, quiet=quiet)

    def _require_connection(self):
        """
        Raise an error if not connected to any device.
        """
        if not self.connected:
            raise RuntimeError("Controller is not connected")

    def connect_tcp(self, ip, port=50000):
        """
        Connect to a single PI controller via TCP/IP (non-daisy-chain).
        """
        device = GCSDevice()
        device.ConnectTCPIP(ip, port)
        self.devices[(ip, port, 1)] = device
        self.connected = True
        self.logger.info(f"Connected to single PI controller at {ip}:{port}")

    def connect_tcpip_daisy_chain(self, ip, port, blocking=True):
        """
        Connect to all available devices on a daisy-chained set of PI controllers via TCP/IP.
        Each device is a separate GCSDevice instance.
        """
        main_device = GCSDevice()
        devices = main_device.OpenTCPIPDaisyChain(ip, port)
        dcid = main_device.dcid

        available = []
        for index, desc in enumerate(devices, start=1):
            if "not connected" not in desc.lower():
                available.append((index, desc))

        if not available:
            raise RuntimeError(f"No connected devices found at {ip}:{port}")

        self.daisy_chains[(ip, port)] = available

        for device_id, desc in available:
            if device_id == 1:
                dev = main_device
            else:
                dev = GCSDevice()

            dev.ConnectDaisyChainDevice(device_id, dcid)
            self.devices[(ip, port, device_id)] = dev
            self.logger.info(f"[{ip}:{port}] Connected to device {device_id}: {desc}")

        self.connected = True

        if blocking:
            # Wait until all devices are ready
            while not all(dev.IsControllerReady() for dev in self.devices.values()):
                time.sleep(0.1)

    def disconnect_device(self, device_key):
        """
        Disconnect from a single device specified by device_key.
        """
        if device_key in self.devices:
            self.devices[device_key].CloseConnection()
            del self.devices[device_key]
            self.logger.info(f"Disconnected device {device_key}")
        if not self.devices:
            self.connected = False

    def disconnect_all(self):
        """
        Disconnect from all devices (e.g., the whole daisychain).
        """
        for device_key in list(self.devices.keys()):
            self.devices[device_key].CloseConnection()
            self.logger.info(f"Disconnected device {device_key}")
        self.devices.clear()
        self.connected = False
        self.logger.info("Disconnected from all PI controllers")

    def list_devices_on_chain(self, ip, port):
        """
        Return the list of available (device_id, description) tuples for the given daisy chain.
        """
        if (ip, port) not in self.daisy_chains:
            raise ValueError(f"No daisy chain found at {ip}:{port}")
        return self.daisy_chains[(ip, port)]

    def is_connected(self) -> bool:
        return self.connected

    def get_idn(self, device_key) -> str:
        """
        Return the identification string for the specified device.
        """
        self._require_connection()
        return self.devices[device_key].qIDN()

    def get_serial_number(self, device_key) -> str:
        """
        Return the serial number for the specified device.
        """
        idn = self.get_idn(device_key)
        return idn.split(',')[-2].strip()

    def get_axes(self, device_key):
        """
        Return the list of axes for the specified device.
        """
        self._require_connection()
        return self.devices[device_key].axes

    def get_position(self, device_key, axis):
        """
        Return the position of the specified axis for the given device.
        """
        self._require_connection()
        device = self.devices[device_key]
        try:
            return device.qPOS(axis)[axis]
        except (GCSError, IndexError) as e:
            self.logger.error(f'Error getting position: {e}')
            return None

    def servo_status(self, device_key, axis):
        """
        Return True if the servo for the given axis is enabled, False otherwise.
        """
        self._require_connection()
        try:
            return bool(self.devices[device_key].qSVO(axis)[axis])
        except GCSError as e:
            self.logger.error(f'Error checking servo status: {e}')
            return False

    def get_error_code(self, device_key):
        """
        Return the error code for the specified device, or None if an error occurs.
        """
        self._require_connection()
        try:
            return self.devices[device_key].qERR()
        except GCSError as e:
            self.logger.error(f'Error getting error code: {e}')
            return None

    def halt_motion(self, device_key):
        """
        Halt all motion for the specified device.
        """
        self._require_connection()
        try:
            self.devices[device_key].HLT()
        except GCSError as e:
            self.logger.error(f'Error halting motion: {e}')

    def set_position(self, device_key, axis, position, blocking=True):
        """
        Move the specified axis to the given position for the specified device.
        If blocking=True, wait until move is complete.
        """
        self._require_connection()
        try:
            self.devices[device_key].MOV(axis, position)
            if blocking:
                while self.is_moving(device_key, axis):
                    time.sleep(0.1)

        except GCSError as e:
            self.logger.error(f'Error setting position: {e}')

    def set_named_position(self, device_key, axis, name):
        """
        Save the current position of the axis under a named label, scoped to the controller serial number.
        """
        device = self.devices[device_key]
        try:
            pos = device.qMOV(axis)[axis]
        except Exception:
            pos = self.get_position(device_key, axis)

        if pos is None:
            self.logger.warning(f"Could not get position for axis {axis}")
            return

        serial = self.get_serial_number(device_key)
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

    def is_moving(self, device_key, axis):
        """Check if stage/axis is moving."""
        self._require_connection()
        return self.devices[device_key].IsMoving(axis)[axis]

    def set_servo(self, device_key, axis, enable=True):
        """Open (enable) or close (disable) servo loop."""
        self._require_connection()
        return self.devices[device_key].SVO(axis, int(enable))

    def get_limit_min(self, device_key, axis):
        """Query stage minimum limit."""
        self._require_connection()
        return self.devices[device_key].qTMN(axis)[axis]

    def get_limit_max(self, device_key, axis):
        """Query stage maximum limit."""
        self._require_connection()
        return self.devices[device_key].qTMX(axis)[axis]

    def is_controller_ready(self, device_key):
        """Check if stage/controller is ready."""
        self._require_connection()
        return self.devices[device_key].IsControllerReady()

    def q_frf(self, device_key, axis):
        """Check reference/home state for axis."""
        self._require_connection()
        return self.devices[device_key].qFRF(axis)[axis]

    def reference_move(self, device_key, axis, method="FRF", blocking=True, timeout=20):
        """
        Execute a reference/home move (FRF, FNL, FPL).
        method: which command to use ("FRF", "FNL", "FPL")
        blocking: if True, wait until move is complete
        Returns True if successful, False otherwise.
        """
        self._require_connection()
        allowed_methods = {"FRF", "FNL", "FPL"}
        if method not in allowed_methods:
            self.logger.error(f"Invalid reference method: {method}. Must be one of {allowed_methods}")
            return False

        device = self.devices[device_key]
        try:
            getattr(device, method)(axis)
            self.logger.info(f"Started reference move '{method}' on axis {axis} (device {device_key})")
            if blocking:
                start_time = time.time()
                while self.is_moving(device_key, axis):
                    if time.time() - start_time > timeout:
                        self.logger.error(f"Reference move timed out after {timeout} seconds on axis {axis}")
                        return False
                    time.sleep(0.1)

            return True
        except Exception as e:
            self.logger.error(f"Error during reference move '{method}' on axis {axis}: {e}")
            return False
