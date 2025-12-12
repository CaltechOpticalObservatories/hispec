"""
PTC10 Controller Interface
"""
from typing import List, Dict
from errno import EISCONN
import socket

from hardware_device_base import HardwareDeviceBase

class PTC10(HardwareDeviceBase):
    """
    Interface for controlling the PTC10 controller.
    """
    channel_names = None

    def __init__(self, log: bool = True, logfile: str = __name__.rsplit(".", 1)[-1] ):
        """
        Initialize the PTC10 controller interface.

        Args:
            log (bool): If True, start logging.
            logfile (str, optional): Path to log file.
        """
        super().__init__(log, logfile)
        self.sock: socket.socket | None = None

    def connect(self, *args, con_type="tcp") -> None:
        """ Connect to controller. """
        if self.validate_connection_params(args):
            if con_type == "tcp":
                host = args[0]
                port = args[1]
                if self.sock is None:
                    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    self.sock.connect((host, port))
                    self.logger.info("Connected to %(host)s:%(port)s", {
                        'host': host,
                        'port': port
                    })
                    self._set_connected(True)

                except OSError as e:
                    if e.errno == EISCONN:
                        self.logger.info("Already connected")
                        self._set_connected(True)
                    else:
                        self.logger.error("Connection error: %s", e.strerror)
                        self._set_connected(False)
                # clear socket
                if self.is_connected():
                    self._clear_socket()
            elif con_type == "serial":
                self.logger.error("Serial connection not yet implemented")
            else:
                self.logger.error("Unknown con_type: %s", con_type)
        else:
            self.logger.error("Invalid connection arguments: %s", args)

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

    def _send_command(self, command: str, *args) -> bool:
        """
        Send a message to the controller (adds newline).

        Args:
            command (str): The message to send (e.g., '3A?').
        """
        try:
            self.logger.debug('Sending: %s', command)
            with self.lock:
                self.sock.sendall((command + "\n").encode())
        except Exception as ex:
            raise IOError(f'Failed to write message: {ex}') from ex
        return True

    def _read_reply(self) -> str:
        """
        Read a response from the controller.

        Returns:
            str: The received message, stripped of trailing newline.
        """
        try:
            retval = self.sock.recv(4096).decode().strip()
            self.logger.debug('Received: %s', retval)
            return retval
        except Exception as ex:
            raise IOError(f"Failed to _read_reply message: {ex}") from ex

    def query(self, msg: str) -> str:
        """
        Send a command and _read_reply the immediate response.

        Args:
            msg (str): Command string to send.

        Returns:
            str: Response from the controller.
        """
        self._send_command(msg)
        return self._read_reply()

    def disconnect(self):
        """
        Close the connection to the controller.
        """
        try:
            self.logger.info('Closing connection to controller')
            if self.sock:
                self.sock.close()
            self._set_connected(False)
        except Exception as ex:
            raise IOError(f"Failed to close connection: {ex}") from ex

    def identify(self) -> str:
        """
        Query the device identification string.

        Returns:
            str: Device identification (e.g. manufacturer, model, serial number, firmware version).
        """
        id_str = self.query("*IDN?")
        self.logger.info("Device identification: %s", id_str)
        return id_str

    def validate_channel_name(self, channel_name: str) -> bool:
        """Is channel name valid?"""
        if self.channel_names is None:
            self.channel_names = self.get_channel_names()
        return channel_name in self.channel_names

    def get_atomic_value(self, channel: str ="") -> float:
        """
        Read the latest value of a specific channel.

        Args:
            channel (str): Channel name (e.g., "3A", "Out1")

        Returns:
            float: Current value, or NaN if invalid.
        """
        if self.validate_channel_name(channel):
            self.logger.debug("Channel name validated: %s", channel)
            # Spaces not allowed
            query_channel = channel.replace(" ", "")
            response = self.query(f"{query_channel}?")
            try:
                value = float(response)
                self.logger.debug("Channel %s value: %f", channel, value)
                return value
            except ValueError:
                self.logger.error(
                    "Invalid float returned for channel %s: %s", channel, response
                )
                return float("nan")
        else:
            self.logger.error("Invalid channel name: %s", channel)
            return float("nan")

    def get_all_values(self) -> List[float]:
        """
        Read the latest values of all channels.

        Returns:
            List[float]: List of float values, with NaN where applicable.
        """
        response = self.query("getOutput?")
        values = [
            float(val) if val != "NaN" else float("nan") for val in response.split(",")
        ]
        self.logger.debug("Output values: %s", values)
        return values

    def get_channel_names(self) -> List[str]:
        """
        Get the list of channel names corresponding to the getOutput() values.

        Returns:
            List[str]: List of channel names.
        """
        response = self.query("getOutputNames?")
        names = [name.strip() for name in response.split(",")]
        self.logger.debug("Channel names: %s", names)
        return names

    def get_named_output_dict(self) -> Dict[str, float]:
        """
        Get a dictionary mapping channel names to their current values.

        Returns:
            Dict[str, float]: Mapping of channel names to values.
        """
        names = self.get_channel_names()
        values = self.get_all_values()
        output_dict = dict(zip(names, values))
        self.logger.debug("Named outputs: %s", output_dict)
        return output_dict
