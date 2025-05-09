from .communication import Communication

class XeryonController:
    
    def __init__(self, COM_port = None, baudrate = 115200):
        """
            :param COM_port: Specify the COM port used
            :type COM_port: string
            :param baudrate: Specify the baudrate
            :type baudrate: int
            :return: Return a Xeryon object.

            Main Xeryon Drive Class, initialize with the COM port and baudrate for communication with the driver.
        """
        self.comm = Communication(self, COM_port, baudrate)
        print('XeryonController')

    