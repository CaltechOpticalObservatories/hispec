
from hispec.util.thorlabs.ppc102 import PPC102
import configparser

class BLUE_PIAA():
    """Class Decription for controling a generic Device 

    method list:
    Queries:
        is_active
        is_connected
        is_closed_loop
        get_error
        get_pos
        get_named_pos
        get_target
    Commands
        connect
        disconnect
        home
        close_loop
        reference
        set_pos
        load_presets

    Inherits from hispec.util.thorlabs.ppc102.PPC102
    """
    
    def __init__(self):
        """
            Initialize the BLUE_PIAA class
        """
        config = configparser.ConfigParser()
        config.read('hispec/hispec/middle_layer/devices.config')
        self.host = config['Front End Instrument']["yjpiaagim_host"]
        self.port = config['Front End Instrument']["yjpiaagim_port"]
        self.device = PPC102()
        self.device.set_connection(self.host, int(self.port))

        self.name = "BLUE_PIAA"

    def is_active(self) -> bool:
        """Check if the device is active

        Returns:
            bool: True if active, False otherwise
        """
        return self.device.is_active()
    
    def is_connected(self) -> bool:
        """Check if the device is connected

        Returns:
            bool: True if connected, False otherwise
        """
        return self.device.sock is not None
    
    def is_closed_loop(self) -> bool:
        """Check if the device is in closed loop

        Returns:
            bool: True if in closed loop, False otherwise
        """
        return self.device.are_closed_loop()

    
    def get_error(self) -> int:
        """Get the current error code

        Returns:
            int: error code
        """
        return self.device.get_error()
    
    def get_pos(self) -> float:
        """Get the current position

        Returns:
            float: current position
        """
        return self.device.get_pos()
    
    def get_named_pos(self, name: str) -> float:
        """Get the position of a named preset

        Args:
            name (str): name of the preset

        Returns:
            float: position of the named preset
        """
        return self.device.get_named_pos(name)
    
    def get_target(self) -> float:
        """Get the target position

        Returns:
            float: target position
        """
        return self.device.get_target()
    
    def connect(self) -> None:
        """Connect to the device"""
        self.device.open()

    def disconnect(self) -> None:
        """Disconnect from the device"""
        self.device.close()
    
    def home(self) -> None:
        """Home the device"""
        self.device.set_position(channel=1, pos = 0.0)
        self.device.set_position(channel=2, pos = 0.0)

    def open_loops(self) -> None:
        """Open the control loop"""
        self.device.set_loop(channel = 0, loop = 1)
    
    def close_loops(self) -> None:
        """Close the control loops"""
        self.device.set_loop(channel = 0, loop = 2)

    def set_pos(self, axis, position: float) -> None:
        """Set the device position

        Args:
            position (float): target position
        """
        self.device.set_position(position)