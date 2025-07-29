"""
PTC10 Controller Interface
"""
from typing import List, Dict, Optional
import hispec.util.helper.logger_utils as logger_utils
from .ptc10_connection import PTC10Connection, PTC10Config


class PTC10:
    """
    Interface for controlling the PTC10 controller.
    """
    def __init__(
            self, conn: PTC10Connection, logfile: Optional[str] = None, quiet: bool = False
    ):
        """
        Initialize the PTC10 controller interface.

        Args:
            conn (PTC10Connection): A connection object for communicating with the PTC10 controller
                                    over serial or Ethernet.
            logfile (str, optional): Path to log file.
            quiet (bool): If True, suppress console output.
        """
        self.conn = conn
        self.logger = logger_utils.setup_logger(__name__, log_file=logfile, quiet=quiet)
        self.logger.debug("PTC10 initialized with connection: %s", conn)

    @classmethod
    # pylint: disable=too-many-arguments
    def connect(
            cls,
            method: str = "serial",
            port: Optional[str] = None,
            baudrate: int = 9600,
            host: Optional[str] = None,
            tcp_port: int = 23,
            timeout: float = 1.0,
            logfile: Optional[str] = None,
            quiet: bool = False,
    ) -> "PTC10":
        """
        Create a new PTC10 instance with an internal connection setup.

        Args:
            method (str): 'serial' or 'ethernet'.
            port (str): Serial port (e.g., '/dev/ttyUSB0') for serial connection.
            baudrate (int): Baudrate for serial (default: 9600).
            host (str): IP address for ethernet connection.
            tcp_port (int): TCP port for ethernet (default: 23).
            timeout (float): Timeout for the connection (in seconds).
            logfile (str, optional): Path to log file.
            quiet (bool): Suppress console output if True.

        Returns:
            PTC10: A new connected PTC10 instance.
        """
        logger = logger_utils.setup_logger(__name__, log_file=logfile, quiet=quiet)
        logger.info("Connecting to PTC10 using method: %s", method)
        config = PTC10Config(
            method=method,
            port=port,
            baudrate=baudrate,
            host=host,
            tcp_port=tcp_port,
            timeout=timeout,
        )
        conn = PTC10Connection(config=config)
        logger.debug("Connection established: %s", conn)
        return cls(conn, logfile=logfile, quiet=quiet)

    def close(self):
        """
        Close the connection to the PTC10.
        """
        self.logger.info("Closing connection to PTC10")
        self.conn.close()

    def identify(self) -> str:
        """
        Query the device identification string.

        Returns:
            str: Device identification (e.g. manufacturer, model, serial number, firmware version).
        """
        id_str = self.conn.query("*IDN?")
        self.logger.info("Device identification: %s", id_str)
        return id_str

    def get_channel_value(self, channel: str) -> float:
        """
        Read the latest value of a specific channel.

        Args:
            channel (str): Channel name (e.g., "3A", "Out1")

        Returns:
            float: Current value, or NaN if invalid.
        """
        response = self.conn.query(f"{channel}?")
        try:
            value = float(response)
            self.logger.info("Channel %s value: %f", channel, value)
            return value
        except ValueError:
            self.logger.error(
                "Invalid float returned for channel %s: %s", channel, response
            )
            return float("nan")

    def get_all_values(self) -> List[float]:
        """
        Read the latest values of all channels.

        Returns:
            List[float]: List of float values, with NaN where applicable.
        """
        response = self.conn.query("getOutput?")
        values = [
            float(val) if val != "NaN" else float("nan") for val in response.split(",")
        ]
        self.logger.info("Output values: %s", values)
        return values

    def get_channel_names(self) -> List[str]:
        """
        Get the list of channel names corresponding to the getOutput() values.

        Returns:
            List[str]: List of channel names.
        """
        response = self.conn.query("getOutputNames?")
        names = [name.strip() for name in response.split(",")]
        self.logger.info("Channel names: %s", names)
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
        self.logger.info("Named outputs: %s", output_dict)
        return output_dict
