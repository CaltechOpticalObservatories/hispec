"""
This module provides a base class for communicating with PI (Physik Instrumente) motion controllers
"""
import json
import os
import time
import logging
from pipython import GCSDevice, GCSError


class PIControllerBase: # pylint: disable=too-many-public-methods
    """
    Base class for communicating with PI (Physik Instrumente) motion controllers daisy-chained
    over TCP/IP via a terminal server.
    """

    def __init__(self, quiet=False):
        """
        Initialize the controller, set up logging, and prepare device storage.
        """
        self.devices = {}  # {(ip, port, device_id): GCSDevice instance}
        self.daisy_chains = {}  # {(ip, port): [(device_id, desc)]}
        self.connected = False
        self.named_position_file = "config/pi_named_positions.json"
        
        # Logging
        logfile = __name__.rsplit('.', 1)[-1] + '.log'
        self.logger = logging.getLogger(logfile)
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        if not quiet:
            file_handler = logging.FileHandler(logfile)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _require_connection(self):
        """
        Raise an error if not connected to any device.
        """
        if not self.connected:
            raise RuntimeError("Controller is not connected")

    def connect_tcp(self, ip_address, port=50000):
        """
        Connect to a single PI controller via TCP/IP (non-daisy-chain).
        """
        device = GCSDevice()
        device.ConnectTCPIP(ip_address, port)
        self.devices[(ip_address, port, 1)] = device
        self.connected = True
        self.logger.info("Connected to single PI controller at %s:%s", ip_address, port)

    def connect_tcpip_daisy_chain(self, ip_address, port, blocking=True):
        """
        Connect to all available devices on a daisy-chained set of PI controllers via TCP/IP.
        Each device is a separate GCSDevice instance.
        """
        main_device = GCSDevice()
        devices = main_device.OpenTCPIPDaisyChain(ip_address, port)
        dcid = main_device.dcid

        available = []
        for index, desc in enumerate(devices, start=1):
            if "not connected" not in desc.lower():
                available.append((index, desc))

        if not available:
            raise RuntimeError(f"No connected devices found at {ip_address}:{port}")

        self.daisy_chains[(ip_address, port)] = available

        for device_id, desc in available:
            if device_id == 1:
                dev = main_device
            else:
                dev = GCSDevice()

            dev.ConnectDaisyChainDevice(device_id, dcid)
            self.devices[(ip_address, port, device_id)] = dev
            self.logger.info("[{ip}:{port}] Connected to device %s: %s", device_id, desc)

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
            self.logger.info("Disconnected device %s", device_key)
        if not self.devices:
            self.connected = False

    def disconnect_all(self):
        """
        Disconnect from all devices (e.g., the whole daisychain).
        """
        for device_key in list(self.devices.keys()):
            self.devices[device_key].CloseConnection()
            self.logger.info("Disconnected device %s", device_key)
        self.devices.clear()
        self.connected = False
        self.logger.info("Disconnected from all PI controllers")

    def list_devices_on_chain(self, ip_address, port):
        """
        Return the list of available (device_id, description) tuples for the given daisy chain.
        """
        if (ip_address, port) not in self.daisy_chains:
            raise ValueError(f"No daisy chain found at {ip_address}:{port}")
        return self.daisy_chains[(ip_address, port)]

    def is_connected(self) -> bool:
        """
        Check if the controller is connected to any device.
        """
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
        return idn.split(",")[-2].strip()

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
        except (GCSError, IndexError) as ex:
            self.logger.error("Error getting position: %s", ex)
            return None

    def servo_status(self, device_key, axis):
        """
        Return True if the servo for the given axis is enabled, False otherwise.
        """
        self._require_connection()
        try:
            return bool(self.devices[device_key].qSVO(axis)[axis])
        except GCSError as ex:
            self.logger.error("Error checking servo status: %s", ex)
            return False

    def get_error_code(self, device_key):
        """
        Return the error code for the specified device, or None if an error occurs.
        """
        self._require_connection()
        try:
            return self.devices[device_key].qERR()
        except GCSError as ex:
            self.logger.error("Error getting error code: %s", ex)
            return None

    def halt_motion(self, device_key):
        """
        Halt all motion for the specified device.
        """
        self._require_connection()
        try:
            self.devices[device_key].HLT()
        except GCSError as ex:
            self.logger.error("Error halting motion: %s", ex)

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

        except GCSError as ex:
            self.logger.error("Error setting position: %s", ex)

    def set_named_position(self, device_key, axis, name):
        """
        Save the current position of the axis under a named label, scoped to
        the controller serial number.
        """
        device = self.devices[device_key]
        try:
            pos = device.qMOV(axis)[axis]
        except (GCSError, OSError, ValueError):
            pos = self.get_position(device_key, axis)

        if pos is None:
            self.logger.warning("Could not get position for axis %s", axis)
            return

        serial = self.get_serial_number(device_key)
        positions = {}

        if os.path.exists(self.named_position_file):
            with open(self.named_position_file, "r") as file:
                try:
                    positions = json.load(file)
                except json.JSONDecodeError:
                    self.logger.warning(
                        "Could not parse JSON from %s", self.named_position_file
                    )

        if serial not in positions:
            positions[serial] = {}

        positions[serial][name] = [axis, pos]

        with open(self.named_position_file, "w") as file:
            json.dump(positions, file, indent=2)

        self.logger.info(
            "Saved position '%s' for controller %s, axis %s: %s", name, serial, axis, pos
        )

    def go_to_named_position(self, device_key, name, blocking=True):
        """
        Move the specified device's axis to a previously saved named position.
        """
        serial = self.get_serial_number(device_key)

        if not os.path.exists(self.named_position_file):
            self.logger.warning(
                "Named positions file not found: %s", self.named_position_file
            )
            return

        try:
            with open(self.named_position_file, "r") as file:
                positions = json.load(file)
        except json.JSONDecodeError:
            self.logger.warning(
                "Failed to read positions from %s", self.named_position_file
            )
            return

        if serial not in positions:
            self.logger.warning("No named positions found for controller %s", serial)
            return

        if name not in positions[serial]:
            self.logger.warning(
                "Named position '%s' not found for controller %s", name, serial
            )
            return

        axis, pos = positions[serial][name]
        self.set_position(device_key, axis, pos, blocking)
        self.logger.info(
            "Moved axis %s to named position '%s' for controller %s: %s", axis, name, serial, pos
        )

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

    def is_controller_referenced(self, device_key, axis):
        """Check reference/home state for axis."""
        self._require_connection()
        return self.devices[device_key].qFRF(axis)[axis]

    def reference_move(self, device_key, axis, method="FRF", blocking=True, timeout=30): # pylint:disable=too-many-arguments
        """
        Execute a reference/home move (FRF, FNL, FPL).
        method: which command to use ("FRF", "FNL", "FPL")
        blocking: if True, wait until move is complete
        Returns True if successful, False otherwise.
        """
        self._require_connection()
        allowed_methods = {"FRF", "FNL", "FPL"}
        if method not in allowed_methods:
            self.logger.error(
                "Invalid reference method: %s. Must be one of %s", method, allowed_methods
            )
            return False

        device = self.devices[device_key]

        # Check if the device supports the specified method
        if not getattr(device, "Has%s", method)():
            self.logger.error("Device %s does not support method '%s'", device_key, method)
            return False

        try:
            getattr(device, method)(axis)
            self.logger.info(
                "Started reference move '%s' on axis %s (device %s)", method, axis, device_key
            )
            if blocking:
                start_time = time.time()
                while self.is_moving(device_key, axis):
                    if time.time() - start_time > timeout:
                        self.logger.error(
                            "Reference move timed out after %s seconds on axis %s", timeout, axis
                        )
                        return False
                    time.sleep(0.1)

            return True
        except (GCSError, OSError, ValueError) as ex:
            self.logger.error(
                "Error during reference move '%s' on axis %s: %s", method, axis, ex
            )
            return False
