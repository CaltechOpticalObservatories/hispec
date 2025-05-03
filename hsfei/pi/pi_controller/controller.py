from pipython import GCSDevice, GCSError


class PIControllerBase:
    """
    Base class for communicating with a PI (Physik Instrumente) motion controller using pipython.
    """

    def __init__(self):
        self.device = GCSDevice()
        self.connected = False

    def connect_tcp(self, ip, port=50000) -> None:
        self.device.ConnectTCPIP(ip, port)
        self.connected = True

    def disconnect(self) -> None:
        self.device.CloseConnection()
        self.connected = False

    def get_serial_number(self):
        if not self.is_connected:
            raise Exception('PI device is not connected')

        serial_number = self.device.qIDN().split(',')[-2].strip()
        return serial_number

    def get_axes(self) -> str:
        if not self.is_connected:
            raise Exception('PI device is not connected')
        
        return self.device.axes

    def send_command(self, cmd, *args):
        raise NotImplementedError("Command not implemented")

    def is_connected(self) -> bool:
        return self.connected

    def get_idn(self) -> str:
        return self.device.qIDN()

    def get_position(self, axis_number):
        if not self.is_connected:
            raise Exception('PI device is not connected')

        try:
            axis = self.device.axes[axis_number]
            position = self.device.qPOS(axis)[axis]

        except GCSError as e:
            print(f'Error: {e}')
        else:
            print(f'Position for axis {axis_number} is {position}')
            return position

    # todo
    def servo_status(self, servo):
        return False

    # todo
    def get_error_code(self):
        return False
    
    # todo
    def halt_motion(self):
        return
    
    # todo
    def is_moving(self):
        return False

    # todo
    def set_position(self, axis, position):
        return

    # todo
    def go_to_named_position(self, axis, position_name):
        return

    # todo
    def set_named_position(self, axis, position_name):
        return
