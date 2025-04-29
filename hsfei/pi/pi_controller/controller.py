from pipython import GCSDevice

class PIControllerBase:
    def __init__(self):
        self.device = GCSDevice()
        self.connected = False

    def connect_tcp(self, ip, port=50000):
        self.device.ConnectTCPIP(ip, port)
        self.connected = True

    def disconnect(self):
        self.device.CloseConnection()
        self.connected = False

    def send_command(self, cmd, *args):
        raise NotImplementedError("Command not implemented")

    def is_connected(self):
        return self.connected
