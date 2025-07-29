"""
PTC10Connection - Low-level communication interface for the PTC10 Temperature Controller
"""
import socket
from dataclasses import dataclass
import serial


@dataclass
class PTC10Config:
    """Configuration for the PTC10Connection."""
    method: str = "serial"
    port: str = None
    baudrate: int = 9600
    host: str = None
    tcp_port: int = 23
    timeout: float = 1.0


class PTC10Connection:
    """
    A low-level communication interface for the Stanford Research Systems
    PTC10 Temperature Controller.
    Supports communication over serial (RS-232) or Ethernet (TCP).
    """

    def __init__(
            self,
            config: PTC10Config,
    ):
        """
        Initialize the PTC10Connection with the given configuration.
        """
        self.method = config.method
        try:
            if config.method == "serial":
                self.ser = serial.Serial(config.port, baudrate=config.baudrate,
                                         timeout=config.timeout)
            elif config.method == "ethernet":
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(config.timeout)
                self.sock.connect((config.host, config.tcp_port))
            else:
                raise ValueError("Unsupported method: choose 'serial' or 'ethernet'")
        except Exception as ex:
            raise ConnectionError(f"Failed to initialize connection: {ex}")

    def write(self, msg: str):
        """
        Send a message to the controller (adds newline).

        Args:
            msg (str): The message to send (e.g., '3A?').
        """
        try:
            if self.method == "serial":
                self.ser.write((msg + "\n").encode())
            else:
                self.sock.sendall((msg + "\n").encode())
        except Exception as ex:
            raise IOError(f"Failed to write message: {ex}")

    def read(self) -> str:
        """
        Read a response from the controller.

        Returns:
            str: The received message, stripped of trailing newline.
        """
        try:
            if self.method == "serial":
                return self.ser.readline().decode().strip()

            return self.sock.recv(4096).decode().strip()
        except Exception as ex:
            raise IOError(f"Failed to read message: {ex}")

    def query(self, msg: str) -> str:
        """
        Send a command and read the immediate response.

        Args:
            msg (str): Command string to send.

        Returns:
            str: Response from the controller.
        """
        self.write(msg)
        return self.read()

    def close(self):
        """
        Close the connection to the controller.
        """
        try:
            if self.method == "serial":
                self.ser.close()
            else:
                self.sock.close()
        except Exception as ex:
            raise IOError(f"Failed to close connection: {ex}")
