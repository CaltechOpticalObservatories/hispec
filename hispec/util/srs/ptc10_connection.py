import serial
import socket


class PTC10Connection:
    """
    A low-level communication interface for the Stanford Research Systems PTC10 Temperature Controller.
    Supports communication over serial (RS-232) or Ethernet (TCP).
    """

    def __init__(self, method='serial', port=None, baudrate=9600, host=None, tcp_port=23, timeout=1.0):
        """
        Initialize the connection to the PTC10 controller.

        Args:
            method (str): Communication method: 'serial' or 'ethernet'.
            port (str): Serial port path (e.g. '/dev/ttyUSB0') for serial connection.
            baudrate (int): Baud rate for serial communication. Default is 9600.
            host (str): IP address of the controller for Ethernet communication.
            tcp_port (int): TCP port number for Ethernet (default is 23).
            timeout (float): Timeout in seconds for communication operations.

        Raises:
            ValueError: If an unsupported method is specified.
        """
        self.method = method
        try:
            if method == 'serial':
                self.ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)
            elif method == 'ethernet':
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(timeout)
                self.sock.connect((host, tcp_port))
            else:
                raise ValueError("Unsupported method: choose 'serial' or 'ethernet'")
        except Exception as e:
            raise ConnectionError(f"Failed to initialize connection: {e}")

    def write(self, msg: str):
        """
        Send a message to the controller (adds newline).

        Args:
            msg (str): The message to send (e.g., '3A?').
        """
        try:
            if self.method == 'serial':
                self.ser.write((msg + '\n').encode())
            else:
                self.sock.sendall((msg + '\n').encode())
        except Exception as e:
            raise IOError(f"Failed to write message: {e}")

    def read(self) -> str:
        """
        Read a response from the controller.

        Returns:
            str: The received message, stripped of trailing newline.
        """
        try:
            if self.method == 'serial':
                return self.ser.readline().decode().strip()
            else:
                return self.sock.recv(4096).decode().strip()
        except Exception as e:
            raise IOError(f"Failed to read message: {e}")

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
            if self.method == 'serial':
                self.ser.close()
            else:
                self.sock.close()
        except Exception as e:
            raise IOError(f"Failed to close connection: {e}")
