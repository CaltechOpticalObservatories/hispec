# pylint: skip-file
import time
import serial
import threading
import socket


class Communication:
    """
    Manages serial or TCP/IP communication with a Xeryon device.

    Supports automatic COM port detection, background data processing,
    and queuing commands for asynchronous communication.
    """

    def __init__(self, xeryon_object, com_port, baud, logger,
                 connection_type='serial', tcp_host=None, tcp_port=None):
        """
        Initializes the Communication object.

        :param xeryon_object: Object that manages Xeryon device and axes.
        :param com_port: COM port to use (for serial communication).
        :param baud: Baud rate for serial communication.
        :param logger: Logger instance for error and status messages.
        :param connection_type: 'serial' or 'tcp' (default is 'serial').
        :param tcp_host: Hostname or IP address for TCP connection.
        :param tcp_port: Port number for TCP connection.
        """
        self.xeryon_object = xeryon_object
        self.COM_port = com_port
        self.baud = baud
        self.readyToSend = []
        self.thread = None
        self.ser = None
        self.sock = None
        self.sio = None
        self.stop_thread = False
        self.logger = logger
        self.connection_type = connection_type
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port

    def start(self, external_communication_thread=False):
        """
        Starts communication with the device and optionally launches a background thread.

        :param external_communication_thread: If True, returns the internal data handler
                                              instead of starting a background thread.
        :return: None or a callable for external data handling.
        :raises Exception: If required connection parameters are missing or invalid.
        """
        if self.connection_type == 'serial':
            if self.COM_port is None:
                self.xeryon_object.find_COM_port()
            if self.COM_port is None:
                raise Exception("No COM port found. Please provide one manually.")
            self.ser = serial.Serial(self.COM_port, self.baud, timeout=1, xonxoff=True)
            self.ser.flush()
            time.sleep(0.1)
            self.ser.flushInput()
            self.ser.flushOutput()
            time.sleep(0.1)

        elif self.connection_type == 'tcp':
            if not self.tcp_host or not self.tcp_port:
                raise Exception("TCP host and port must be specified.")
            self.sock = socket.create_connection((self.tcp_host, self.tcp_port), timeout=2)
            self.sio = self.sock.makefile('rwb', buffering=0)

        else:
            raise Exception(f"Unknown connection_type: {self.connection_type}")

        if not external_communication_thread:
            self.thread = threading.Thread(target=self.__process_data)
            self.thread.daemon = True
            self.thread.start()
        else:
            return self.__process_data

    def send_command(self, command):
        """
        Queues a command to be sent to the device.

        :param command: Command string to send.
        """
        self.readyToSend.append(command)

    def set_COM_port(self, com_port):
        """
        Sets the COM port manually.

        :param com_port: New COM port string.
        """
        self.COM_port = com_port

    def __process_data(self, external_while_loop=False):
        """
        Handles sending commands and reading responses in a loop.

        :param external_while_loop: If True, run a single iteration and return (for external loops).
        :return: None
        """
        while not self.stop_thread:
            data_to_send = self.readyToSend[:10]
            self.readyToSend = self.readyToSend[10:]

            # Send commands
            for command in data_to_send:
                try:
                    msg = (command.rstrip("\n\r") + "\n").encode()
                    if self.connection_type == 'serial':
                        self.ser.write(msg)
                    elif self.connection_type == 'tcp':
                        self.sio.write(msg)
                        self.sio.flush()
                except Exception as e:
                    self.logger.info(f"Write error: {e}", error=True)
                    continue

            # Read responses
            try:
                for _ in range(10):
                    if self.connection_type == 'serial':
                        if self.ser.in_waiting == 0:
                            break
                        reading = self.ser.readline().decode()
                    elif self.connection_type == 'tcp':
                        self.sock.settimeout(0.1)
                        reading = self.sio.readline().decode()
                        if not reading:
                            break
                    else:
                        break

                    if "=" in reading:
                        if ":" in reading:
                            key, value = reading.split(":", 1)
                            axis = self.xeryon_object.get_axis(key) or self.xeryon_object.axis_list[0]
                            axis.receive_data(value)
                        else:
                            axis = self.xeryon_object.axis_list[0]
                            axis.receive_data(reading)

            except Exception as e:
                self.logger.info(f"Read error: {e}", error=True)

            if external_while_loop:
                return

            # NOTE: (KPIC MOD) we added a delay here so that we don't use as much CPU power on this loop
            time.sleep(0.01)

    def close_communication(self):
        """
        Closes the communication channel and stops the background thread.
        """
        self.stop_thread = True
        time.sleep(0.1)

        if self.connection_type == 'serial' and self.ser:
            self.ser.close()
        elif self.connection_type == 'tcp' and self.sock:
            self.sio.close()
            self.sock.close()
