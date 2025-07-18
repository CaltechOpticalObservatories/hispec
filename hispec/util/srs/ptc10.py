from typing import List, Dict, Optional
from .ptc10_connection import PTC10Connection

class PTC10:
    def __init__(self, conn: PTC10Connection):
        """
        Initialize the PTC10 controller interface.

        Args:
            conn (PTC10Connection): A connection object for communicating with the PTC10 controller
                                    over serial or Ethernet.
        """
        self.conn = conn

    @classmethod
    def connect(cls,
                method: str = "serial",
                port: Optional[str] = None,
                baudrate: int = 9600,
                host: Optional[str] = None,
                tcp_port: int = 23,
                timeout: float = 1.0) -> "PTC10":
        """
        Create a new PTC10 instance with an internal connection setup.

        Args:
            method (str): 'serial' or 'ethernet'.
            port (str): Serial port (e.g., '/dev/ttyUSB0') for serial connection.
            baudrate (int): Baudrate for serial (default: 9600).
            host (str): IP address for ethernet connection.
            tcp_port (int): TCP port for ethernet (default: 23).
            timeout (float): Timeout for the connection (in seconds).

        Returns:
            PTC10: A new connected PTC10 instance.
        """
        conn = PTC10Connection(
            method=method,
            port=port,
            baudrate=baudrate,
            host=host,
            tcp_port=tcp_port,
            timeout=timeout
        )
        return cls(conn)

    def close(self):
        """
        Close the connection to the PTC10.
        """
        self.conn.close()

    def identify(self) -> str:
        """
        Query the device identification string.

        Returns:
            str: Device identification (e.g. manufacturer, model, serial number, firmware version).
        """
        return self.conn.query("*IDN?")

    def get_channel_value(self, channel: str) -> float:
        """
        Read the latest value of a specific channel.

        Args:
            channel (str): Channel name (e.g., "3A", "Out1")

        Returns:
            float: Current value, or NaN if invalid.
        """
        response = self.conn.query(f"{channel}?")
        return float(response)

    def get_all_values(self) -> List[float]:
        """
        Read the latest values of all channels.

        Returns:
            List[float]: List of float values, with NaN where applicable.
        """
        response = self.conn.query("getOutput?")
        return [float(val) if val != "NaN" else float("nan") for val in response.split(",")]

    def get_channel_names(self) -> List[str]:
        """
        Get the list of channel names corresponding to the getOutput() values.

        Returns:
            List[str]: List of channel names.
        """
        response = self.conn.query("getOutputNames?")
        return [name.strip() for name in response.split(",")]

    def get_named_output_dict(self) -> Dict[str, float]:
        """
        Get a dictionary mapping channel names to their current values.

        Returns:
            Dict[str, float]: Mapping of channel names to values.
        """
        names = self.get_channel_names()
        values = self.get_all_values()
        return dict(zip(names, values))
