from pipython import GCSDevice, GCSError
import logging
import json
import os


class PIControllerBase:
    """
    Base class for communicating with PI (Physik Instrumente) motion controllers daisy-chained over TCP/IP via a terminal server.
    """

    def __init__(self, quiet=False):
        self.device = GCSDevice()
        self.connected = False
        self.current_id = None
        self.daisy_chains = {}  # {(ip, port): [(1, desc1), (2, desc2)]}
        self.current_connection = None
        self.named_position_file = 'config/pi_named_positions.json'

        self.logger = logging.getLogger(self.__class__.__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.WARNING if quiet else logging.INFO)

    def _require_connection(self):
        if not self.connected:
            raise RuntimeError("Controller is not connected")

    def connect_tcp(self, ip, port=50000):
        """
        Connect to a single PI controller via TCP/IP (non-daisy-chain).
        """
        self.device.ConnectTCPIP(ip, port)
        self.connected = True
        self.logger.info(f"Connected to single PI controller at {ip}:{port}")

    def connect_tcpip_daisy_chain(self, ip, port):
        """
        Connect to a daisy-chained set of PI controllers via TCP/IP over a terminal server.
        """
        devices = self.device.OpenTCPIPDaisyChain(ip, port)
        dcid = self.device.dcid

        available = []
        for index, desc in enumerate(devices, start=1):
            if "not connected" not in desc.lower():
                available.append((index, desc))

        if not available:
            raise RuntimeError(f"No connected devices found at {ip}:{port}")

        self.daisy_chains[(ip, port)] = available

        # Connect to the first device by default
        first_id, first_desc = available[0]
        self.device.ConnectDaisyChainDevice(first_id, dcid)
        self.connected = True
        self.current_connection = (ip, port, first_id)

        self.logger.info(f"[{ip}:{port}] Connected to device {first_id}: {first_desc}")

    def select_device_on_chain(self, ip, port, device_id):
        """
        Switch to a specific device on an existing daisy chain connection.
        """
        if (ip, port) not in self.daisy_chains:
            raise RuntimeError(f"Daisy chain at {ip}:{port} not initialized")

        dcid = self.device.dcid  # still valid for this connection
        self.device.ConnectDaisyChainDevice(device_id, dcid)
        self.current_connection = (ip, port, device_id)
        self.logger.info(f"Switched to device {device_id} on {ip}:{port}")

    def disconnect(self):
        self.device.CloseConnection()
        self.connected = False
        self.logger.info("Disconnected from PI controller")

    def list_devices_on_chain(self, ip, port):
        """
        Return the list of available (device_id, description) tuples for the given daisy chain.
        """
        if (ip, port) not in self.daisy_chains:
            raise ValueError(f"No daisy chain found at {ip}:{port}")
        return self.daisy_chains[(ip, port)]

    def is_connected(self) -> bool:
        return self.connected

    def get_idn(self) -> str:
        self._require_connection()
        return self.device.qIDN()

    def get_serial_number(self) -> str:
        idn = self.get_idn()
        return idn.split(',')[-2].strip()

    def get_axes(self) -> str:
        self._require_connection()
        return self.device.axes

    def get_position(self, axis_number):
        self._require_connection()
        try:
            axis = self.device.axes[axis_number]
            return self.device.qPOS(axis)[axis]
        except (GCSError, IndexError) as e:
            self.logger.error(f'Error getting position: {e}')
            return None

    def servo_status(self, axis):
        self._require_connection()
        try:
            return bool(self.device.qSVO(axis)[axis])
        except GCSError as e:
            self.logger.error(f'Error checking servo status: {e}')
            return False

    def get_error_code(self):
        self._require_connection()
        try:
            return self.device.qERR()
        except GCSError as e:
            self.logger.error(f'Error getting error code: {e}')
            return None

    def halt_motion(self):
        self._require_connection()
        try:
            self.device.HLT()
        except GCSError as e:
            self.logger.error(f'Error halting motion: {e}')

    def set_position(self, axis, position):
        self._require_connection()
        try:
            self.device.MOV(axis, position)
        except GCSError as e:
            self.logger.error(f'Error setting position: {e}')

    def set_named_position(self, axis, name):
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

    def is_moving(self, axis, position_name):
        raise NotImplementedError("is_moving is not implemented")
