"""
Defines the XeryonController class, the main interface for communicating with
Xeryon motion controllers.

Includes setup of communication, management of connected axes, settings handling,
and motion control utilities.
"""
import time
import serial
import os
import logging
from .communication import Communication
from .axis import Axis
from .config import AUTO_SEND_SETTINGS, SETTINGS_FILENAME


class XeryonController:
    """
    Main controller class for Xeryon motion systems.

    Handles communication setup, axis registration, system initialization, and command execution.
    Supports both serial and TCP communication, single or multi-axis setups,
    and persistent settings.

    Typical usage:
        controller = XeryonController(COM_port="COM3")
        controller.add_axis(stage="linear", axis_letter="X")
        controller.start()
    """
    # pylint: disable=too-many-arguments
    def __init__(self, COM_port=None, baudrate=115200, log=True, logfile=None,
                 settings_filename=SETTINGS_FILENAME,
                 connection_type='serial', tcp_host=None, tcp_port=None):
        """
            :param COM_port: Specify the COM port used.
            :type COM_port: string
            :param baudrate: Specify the baudrate.
            :type baudrate: int
            :param quiet: If True, suppresses logger output to stdout.
            :type quiet: bool
            :param settings_filename: Path to the settings file to use for this controller instance.
            :type settings_filename: str
            :return: A XeryonController object.

            Main Xeryon Drive Class, onitialize with the COM port, baudrate, and a settings file
            for communication with the driver.
        """
        
        # Logging
        logfile = __name__.rsplit('.', 1)[-1] + '.log'
        self.logger = logging.getLogger(logfile)
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        if log:
            file_handler = logging.FileHandler(logfile)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        self.comm = Communication(
            self, COM_port, baudrate, self.logger,
            connection_type=connection_type, tcp_host=tcp_host, tcp_port=tcp_port
        )  # Startup communication
        self.axis_list = []
        self.axis_letter_list = []
        self.master_settings = {}
        self.settings_filename = settings_filename

    def is_single_axis_system(self):
        """
        :return: Returns True if it's a single axis system, False if its a multiple axis system.
        """
        return len(self.get_all_axis()) <= 1

    def start(self, external_communication_thread=False, do_reset=True, auto_send_settings=AUTO_SEND_SETTINGS):
        """
        :return: Nothing.
        This functions NEEDS to be ran before any commands are executed.
        This function starts the serial communication and configures the settings
        with the controller.


        NOTE: (KPIC MOD) we added the do_reset flag so that we can disconnect and reconnect
              to the stage without doing a reset. This allows us to reconnect without having
              to re-reference the stage.
        """
        if len(self.get_all_axis()) <= 0:
            raise Exception(
                "Cannot start the system without stages. The stages don't have to be connnected, "
                "only initialized in the software.")

        comm = self.get_communication().start(
            external_communication_thread)  # Start communication

        if do_reset:
            for axis in self.get_all_axis():
                axis.reset()
            time.sleep(0.2)

        self.read_settings()  # Read settings file
        if auto_send_settings:
            self.send_master_settings()
            for axis in self.get_all_axis():  # Loop trough each axis:
                axis.send_settings()  # Send the settings
        # ask for LLIM & HLIM value's
        for axis in self.get_all_axis():
            axis.send_command("HLIM=?")
            axis.send_command("LLIM=?")
            axis.send_command("SSPD=?")
            axis.send_command("PTO2=?")
            axis.send_command("PTOL=?")

        if external_communication_thread:
            return comm
        return None

    def stop(self, is_print_end=True):
        """
        :return: None
        This function sends STOP to the controller and closes the communication.

        NOTE: (KPIC MOD) we added the is_print_end flag to avoid unnecessary prints that
        may confuse users
        """
        for axis in self.get_all_axis():  # Send STOP to each axis.
            axis.send_command("ZERO=0")
            axis.send_command("STOP=0")
            axis.was_valid_DPOS = False
        self.get_communication().close_communication()  # Close communication
        if is_print_end:
            self.logger.info("Program stopped running.")

    def stop_movements(self):
        """
        Just stop moving.
        """
        for axis in self.get_all_axis():
            axis.send_command("STOP=0")
            axis.was_valid_DPOS = False

    def reset(self):
        """
        :return: None
        This function sends RESET to the controller, and resends all settings.
        """
        for axis in self.get_all_axis():
            axis.reset()
        time.sleep(0.2)

        self.read_settings()  # Read settings file again

        if AUTO_SEND_SETTINGS:
            for axis in self.get_all_axis():
                axis.send_settings()  # Update settings

    def get_all_axis(self):
        """
        :return: A list containing all axis objects belonging to this controller.
        """
        return self.axis_list

    def add_axis(self, stage, axis_letter):
        """
        :param stage: Specify the type of stage that is connected.
        :type stage: Stage
        :return: Returns an Axis object
        """
        new_axis = Axis(self, axis_letter, stage, self.logger)
        self.axis_list.append(new_axis)  # Add axis to axis list.
        self.axis_letter_list.append(axis_letter)
        return new_axis

    # End User Commands
    def get_communication(self):
        """
        :return: The communication class.
        """
        return self.comm

    def get_axis(self, letter):
        """
        :param letter: Specify the axis letter
        :return: Returns the correct axis object. Or None if the axis does not exist.
        """
        if self.axis_letter_list.count(letter) == 1:  # Axis letter found
            indx = self.axis_letter_list.index(letter)
            if len(self.get_all_axis()) > indx:
                return self.get_all_axis()[indx]  # Return axis
        return None

    def read_settings(self, settings_file: str = None):
        """
        :param settings_file: Optional path to a settings file. If not provided,
        uses self.settings_filename.
        :return: None
        This function reads the settings.txt file and processes each line.
        It first determines for what axis the setting is, then it reads the setting and saves it.
        If there are commands for axis that don't exist, it just ignores them.
        """
        filepath = settings_file if settings_file is not None else self.settings_filename
        
        print(filepath)

        try:
            with open(filepath, "r") as file:
                for line in file.readlines():  # For each line:
                    # Check if it's a command and not a comment or blank line.
                    if "=" in line and line.find("%") != 0:

                        # Strip spaces and newlines.
                        line = line.strip("\n\r").replace(" ", "")
                        # Default select the first axis.
                        axis = self.get_all_axis()[0]
                        if ":" in line:  # Check if axis is specified
                            axis = self.get_axis(line.split(":")[0])
                            if axis is None:  # Check if specified axis exists
                                # No valid axis? ==> IGNORE and loop further.
                                continue
                            line = line.split(":")[1]  # Strip "X:" from command
                        elif not self.is_single_axis_system():
                            # This line doesn't contain ":", so it doesn't specify an axis.
                            # BUT It's a multi-axis system ==> so these settings are for the master.
                            if "%" in line:  # Ignore comments
                                line = line.split("%")[0]
                            self.set_master_setting(line.split(
                                "=")[0], line.split("=")[1], True)
                            continue

                        if "%" in line:  # Ignore comments
                            line = line.split("%")[0]

                        tag = line.split("=")[0]
                        value = line.split("=")[1]

                        # Update settings for specified axis.
                        axis.set_setting(tag, value, True, doNotSendThrough=True)

        except FileNotFoundError as ex:
            print("Trying to open:", os.path.abspath(filepath))
            self.logger.info("No settings_default.txt found.")
            # self.stop()  # Make sure the thread also stops.
            # raise Exception(
            # "ERROR: settings_default.txt file not found. Place it in the same folder
            # as Xeryon.py. \n "
            # "The settings_default.txt is delivered in the same folder as the
            # Windows Interface. \n " + str(e))
        except Exception as ex:
            raise ex

    def set_master_setting(self, tag, value, from_settings_file=False):
        """
            In multi-axis systems, commands without an axis specified are for the master.
            This function adds a setting (tag, value) to the list of settings for the master.
        """
        self.master_settings.update({tag: value})
        if not from_settings_file:
            self.comm.send_command(str(tag)+"="+str(value))
        if "COM" in tag:
            self.set_com_port(str(value))

    def send_master_settings(self, axis=False):
        """
         In multi-axis systems, commands without an axis specified are for the master.
         This function sends the stored settings to the controller;
        """
        prefix = ""
        if axis is not False:
            prefix = str(self.get_all_axis()[0].get_letter()) + ":"

        for tag, value in self.master_settings.items():
            self.comm.send_command(str(prefix) + str(tag) + "="+str(value))

    def save_master_settings(self, axis=False):
        """
         In multi-axis systems, commands without an axis specified are for the master.
         This function saves the master settings on the controller.
        """
        if axis is None:
            self.comm.send_command("SAVE=0")
        else:
            self.comm.send_command(
                str(self.get_all_axis()[0].get_letter()) + ":SAVE=0")

    def set_com_port(self, com_port):
        """
        :param com_port: Specify the COM port used.
        """
        self.get_communication().set_COM_port(com_port)

    def find_com_port(self):
        """
        This function loops through every available COM-port.
        It check's if it contains any signature of Xeryon.
        :return:
        """
        self.logger.info("Automatically searching for COM-Port. If you want to speed things up "
                         "you should manually provide it inside the controller object.")
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            if "04D8" in str(port.hwid):
                self.set_com_port(str(port.device))
                break

    def is_communication_thread_alive(self):
        """
        Check if the communication thread is still running.

        :return: True if thread is alive, False otherwise
        """
        return self.comm.is_thread_alive()

    def get_communication_health_status(self):
        """
        Get detailed health status of the communication thread.

        :return: Dictionary with thread health information including:
                 - thread_alive: bool
                 - last_heartbeat: timestamp or None
                 - time_since_heartbeat: float (seconds) or None
                 - heartbeat_stale: bool
        """
        return self.comm.get_thread_health_status()

    def check_communication_health(self, raise_on_dead=False):
        """
        Check if communication thread is healthy and optionally raise exception if not.

        :param raise_on_dead: If True, raise an exception when thread is dead
        :return: True if healthy, False otherwise
        :raises Exception: If raise_on_dead=True and thread is not healthy
        """
        return self.comm.check_thread_health(raise_on_dead=raise_on_dead)
