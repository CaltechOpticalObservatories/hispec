#NOTE:: Pip install of libximc is needed to use the library imported
#       These are not standard python librarys but are on PyPI
#                       -Elijah Anakalea-Buckley

import libximc.highlevel as ximc
import logging
import pathlib
import os
import time


class SMC(object):
    ''' 
        Class is for utilizing the libximc Library.
        Functions from lib.ximc is incorporated into this class
        to make it easier to use for common tasks.
        - using the more recently developed libximc.highlevel API
        - step_size:float = 0.0025 Conversion Coefficient, Example  for
            converting steps to mm used in API, adjust as needed
        - All functions log their actions and errors to a log file
        - Required Parameters:
            device_connection: str = Connection string for device
                - Ex: serial connection: '/COM3', '/dev/ximc/000746D30' or '192.123.123.92'
                - NOTE:: For Network you must provide IP/Name and device ID. Device ID is the 
                            serial number tranlslated to hex
                        EX: SMC(device_connection = "192.168.29.123/9219", connection_type="xinet")
            connection_type: str = Type of connection
                - Options: 'serial'=USB, 'tcp'=Raw TCP, 'xinet'=Network
            log: bool = Enable or disable logging to file
    '''

    def __init__(self, device_connection: str, connection_type: str,log: bool, step_size:float = 0.0025):
        '''
            Inicializes the device
            parameters: ip string, port integer, logging bool
            - full device capabilities will be under "self.device.<functions()>"
        '''
        # Logger setup
        logname = __name__.rsplit(".", 1)[-1]
        self.logger = logging.getLogger(logname)
        self.logger.setLevel(logging.DEBUG)
        if log:
            log_handler = logging.FileHandler(logname + ".log")
            formatter = logging.Formatter(
                "%(asctime)s--%(name)s--%(levelname)s--%(module)s--"
                "%(funcName)s--%(message)s")
            log_handler.setFormatter(formatter)
            self.logger.addHandler(log_handler)
        # Console handler for real-time output
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("%(asctime)s--%(message)s")
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        

        self.logger.info("Logger initialized for SMC8 Stage")

        #Inicialize variables and objects
        self._move_cmd_flags = ximc.MvcmdStatus  # Default move command flags
        self._state_flags = ximc.StateFlags
        self.serial_number = None
        self.power_setting = None
        self.device_information = None
        self._engine_settings = None
        self.min_limit = None
        self.max_limit = None
        self._homed_and_happy_bool = False
        self._uPOSITION = 0 #Constant is 0 for DC motors and avaries for stepper motors
                           #look into ximc library for details on uPOSITION 
        self.device_uri = None

        # Reference for connecting to device
        # device_uri = r"xi-emu:///ABS_PATH/virtual_controller.bin"  # Virtual device
        # device_uri = r"xi-com:\\.\COM111"                        # Serial port
        # device_uri = "xi-tcp://172.16.130.155:1820"              # Raw TCP connection
        # device_uri = "xi-net://192.168.1.120/abcd"               # XiNet connection
        connection_type = connection_type.lower().strip()
        if connection_type == "serial":
            self.device_uri = f"xi-com://{device_connection}"
        elif connection_type == "tcp":
            self.device_uri = f"xi-tcp://{device_connection}"
        elif connection_type == "xinet":
            self.device_uri = f"xi-net://{device_connection}"
        else:
            self.logger.error(f"Unknown connection type: {connection_type}")
            raise ValueError(f"Unknown connection type: {connection_type}")


        self.step_size_coeff = step_size  # Example conversion coefficient, adjust as needed(mm)
        self.dev_open = False   
        self._axis = ximc.Axis(self.device_uri)

    def open_connection(self):
        '''
            Opens communication to the Device, gathers general information to 
            store in local variables.
            return: Bool for successful or unsuccessful connection
            libximc:: open_device()
        '''
        #Check if already open
        if self.dev_open:
            #log that device is already open
            self.logger.info("Device already open, skipping open command.")
            #return true if already open
            return True
        
        #try to open
        try:
            #open device
            self._axis.open_device()
            #get and save engine settings
            self._engine_settings = self._axis.get_engine_settings()
            #Set calb for user units TODO:: Check if this is correct(SPECIFICALLY THE MICROSTEP MODE)
            self._axis.set_calb(self.step_size_coeff, self._engine_settings.MicrostepMode)
            #Set limits
            self.limits = self._axis.get_edges_settings()
            self.min_limit = self.limits.LeftBorder
            self.max_limit = self.limits.RightBorder

            self.logger.info("Device opened successfully.")

            #return true if successful
            self.dev_open = True
            return True
        except Exception as e:
            #log error
            self.logger.error(f"Error opening device: {e}")
            
            #return false if unsuccessful
            self.dev_open = False
            return False

    def close_connection(self):
        '''
            Closes communication to the Device
            return: Bool for successful or unsuccessful termination
            libximc:: close_device()
        '''
        #Check if already open
        if not self.dev_open:
            #log that de is closed
            self.logger.info("Device already closed, skipping close command.")
            
            #return true if already closed
            return True

        #Try to close
        try:
            self._axis.close_device()
            self.dev_open = False
            self.logger.info("Device closed successfully.")
            #return true if succesful
            return True
        except Exception as e:
        #catch error
            #log error and return false
            self.logger.error(f"Error closing device: {e}")
            
            #return false if unsuccessful
            self.dev_open = True
            return False
        
    def get_info(self):
        '''
            Gets information about the device, such as serial number, power setting,
            command read settings, and device information. That information is stored
            in local variables for later use.
            - This function is called after opening the device to gather information
            return: dict with device information
            libximc:: get_serial_number(), get_power_setting(), command_read_settings(),
                      get_device_information()
        '''
        #Check if connection not open
        if not self.dev_open:
            #log closed connection
            self.logger.error("Device not open, cannot get info.")
            return False

        #Try to get info
        try:
            #get serial number
            self.serial_number = self._axis.get_serial_number()
            #get power settings
            self.power_setting = self._axis.get_power_settings()
            #get device information
            self.device_information = self._axis.get_device_information()

            self.logger.info("Device opened successfully.")
            self.logger.info(f"Serial number: {self.serial_number}")
            self.logger.info(f"Power setting: {self.power_setting}")
            #Log device information
            self.logger.info(f"Device information: {self.device_information}")

            #return true if successful
            return True
        except Exception as e:
            #log error and return None
            self.logger.error(f"Error getting device information: {e}")
            return False


    def home(self):
        '''
            Homes stage into "parked" positon
            -Will Home and stay at homed position.
            return: bool on successful home
            libximc:: command_homezero()
        '''
        #Check if connection not open
        if not self.dev_open:
            #log closed connection
            self.logger.error("Device not open, cannot home stage.")
            return False

        #Try to home to zero or parked position
        try:
            self._axis.command_homezero()
            #Check position after homing
            self.logger.info("Stage sent to homed position which is 0")
            #return true if succesful
            self.status()
            return True
        #catch error  
        except Exception as e:
            #log error
            self.logger.error(f"Error homing stage: {e}")
            #return false if unsuccessful
            return False

    def move_abs(self, position:int):
        '''
            Move the stage to a ABSOLUTE position. Send stage to any specific
                location within the device limits.
            - Check min_limit and max_limit for valid inputs
            parameters: min_limit < int:"position" < max_limit
            return: bool on successful or unsuccessful absolute move
            libximc:: command_move()
        '''
        #Check if connection not open
        if not self.dev_open:
            #log closed connection
            self.logger.error("Device not open, cannot move stage.")
            return False

        #Try move absolute
        try:
            #check limits/valid inputs
            if position < self.min_limit or position > self.max_limit:
                self.logger.error(f"Position out of limits: {position}")
                return False
            #move absolute
            self._axis.command_move(position, self._uPOSITION)
            #return true if succesful
            return True
        #catch error
        except Exception as e:
            #log error and return false
            self.logger.error(f"Error moving stage: {e}")
            return False

    def move_rel(self, position:int):
        '''
            Move the stage to a RELATIVE position. Send stage to a position
                relative to its current position.
            - Check min_limit and max_limit for range of device
            parameters: min_limit < +- int for relative move < max_limit
            return: bool on successful or unsuccessful relative move
            libximc:: command_movr()
        '''
        #Check if connection not open
        if not self.dev_open:
            #log closed connection
            self.logger.error("Device not open, cannot move stage.")
            return False

        #Try move relative
        try:
            #check limits/valid inputs
            #get current position
            current_position = self.get_position()
            #calculate new position
            new_position = current_position + position
            #check if new position is within limits
            if new_position < self.min_limit or new_position > self.max_limit:
                self.logger.error(f"Position out of limits: {new_position}")
                return False
            #move relative
            self._axis.command_movr(position, self._uPOSITION)
            #return true if succesful
            return True
        #catch error
        except Exception as e:
            #log error and return false
            self.logger.error(f"Error moving stage: {e}")
            return False

    def get_position(self):
        '''
            Gets Position of stage
            return: position in stage specific units
            libximc::
        '''
        #Check if connection not open
        if not self.dev_open:
            #log closed connection
            self.logger.error("Device not open, cannot get position.")
            return False

        #Try get_position
        try:
            #get position
            pos = self._axis.get_position()
            #return aspects of the position object  
            return pos.Position
        #catch error
        except Exception as e:
            #log error and return None
            self.logger.error(f"Error getting position: {e}")
            return None

    def status(self):
        '''
            Gathers status and formats it in a usable and readable format.
                mostly for logging
            return: status string and variables nessesary
            libximc:: get_status()
        '''
        #Check if connection not open
        if not self.dev_open:
            #log closed connection
            self.logger.error("Device not open, cannot get status.")
            return False

        #Try status function    
        try:
            #get status
            status = self._axis.get_status()
            #parse results
            #return status in user friendly way
            self.logger.info(f"Position: {status.CurPosition}")
            self._homed_and_happy_bool = bool(status.Flags & self._state_flags.STATE_IS_HOMED |
                                                 self._state_flags.STATE_EEPROM_CONNECTED)
            return status
        #catch error
        except Exception as e:
            #log error and return false
            self.logger.error(f"Error getting status: {e}")
            return None

    def halt(self):
        '''
            IMMITATELY halts the stage, no matter the status or if moving, stage
                stops(for safety purposes)
            return: status of the stage(log and/or print hald command called)
            libximc:: command_stop()
        '''
        #Check if connection not open
        if not self.dev_open:
            #log closed connection
            self.logger.error("Device not open, cannot halt stage.")
            return False

        #Try imidiate stop of stage
        try:
            self._axis.command_stop()
            #Check status after halting
            status = self._axis.get_status()
            if status.MvCmdSts != self._move_cmd_flags.MVCMD_STOP:
                self.halt()  #Recursively call halt if not stopped

            #status.Moving
            self.logger.info("Stage halted successfully.")
            #return true if succesful
            return True
        #catch error
        except Exception as e:
            #log error and return false
            self.logger.error(f"Error halting stage: {e}")
            return False