import time
import serial
import threading

from keyring.util.platform_ import data_root

from .axis import Axis
from .utils import output_console


class Communication:
    def __init__(self, xeryon_object, com_port, baud):
        self.xeryon_object = xeryon_object
        self.COM_port = com_port
        self.baud = baud
        self.readyToSend = []
        self.thread = None
        self.ser = None
        self.stop_thread = False

    def start(self, external_communication_thread=False):
        """
        :return: None
        This starts the serial communication on the specified COM port and baudrate in a seperate thread.
        """
        if self.COM_port is None:
            self.xeryon_object.find_COM_port()
        if self.COM_port is None:  # No com port found
            raise Exception(
                "No COM_port could automatically be found. You should provide it manually.")

        self.ser = serial.Serial(
            self.COM_port, self.baud, timeout=1, xonxoff=True)
        self.ser.flush()
        # NOTE: (KPIC MOD) added flushInput() and flushOutput() per Xeryon's suggestion
        time.sleep(0.1)
        self.ser.flushInput()
        self.ser.flushOutput()
        time.sleep(0.1)

        if external_communication_thread is False:
            self.thread = threading.Thread(target=self.__process_data)
            self.thread.daemon = True
            self.thread.start()
        else:
            return self.__process_data

    def send_command(self, command):
        """
        :param command: The command that needs to be send.
        :return: None
        This function adds the command to the readyToSend list.
        """
        self.readyToSend.append(command)
        # self.ser.write(str.encode(command.rstrip("\n\r") + "\n"))

    def set_COM_port(self, com_port):
        self.COM_port = com_port

    def __process_data(self, external_while_loop=False):
        """
        :return: None
        This function is ran in a seperate thread.
        It continously listens for:
        1. If there is data to send
            Than it just writes the command.
            It strips all the new lines from the command and adds it's own.
        2. If there is data to read
            It reads the data line per line and checks if it contains "=".
            It determines the correct axis and passes that data to that axis class.
        3. Thread stop command.
        """

        while not self.stop_thread:  # Infinte looe
            # data_to_send = list(self.readyToSend)  # Make a copy of this list
            # self.readyToSend = []  # Immediately remove the list

            # SEND 10 LINES, then go further to reading.
            data_to_send = list(self.readyToSend[0:10])
            self.readyToSend = self.readyToSend[10:]

            for command in data_to_send:  # Send commands.
                try:
                    self.ser.write(str.encode(command.rstrip("\n\r") + "\n"))
                except Exception as e:
                    output_console(f"Write error: {e}", error=True)
                    continue

            max_to_read = 10
            try:
                while self.ser.in_waiting > 0 and max_to_read > 0:  # While there is data to read
                    reading = self.ser.readline().decode()  # Read a single line

                    if "=" in reading:  # Line contains a command.

                        if len(reading.split(":")) == 2:  # check if an axis is specified
                            axis = self.xeryon_object.get_axis(
                                reading.split(":")[0])
                            reading = reading.split(":")[1]
                            if axis is None:
                                axis = self.xeryon_object.axis_list[0]
                            axis.receive_data(reading)

                        else:
                            # It's a single axis system
                            axis = self.xeryon_object.axis_list[0]
                            axis.receive_data(reading)

                    max_to_read -= 1
            except Exception as e:
                output_console(f"Read error: {e}", error=True)

            if external_while_loop is True:
                return None

            # NOTE: (KPIC MOD) we added a delay here so that we don't use as much CPU power on this loop
            time.sleep(0.01)

    def close_communication(self):
        self.stop_thread = True
        time.sleep(0.1)
        self.ser.close()
