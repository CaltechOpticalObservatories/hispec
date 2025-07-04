#NOTE:: Pip install of libximc is needed to use the library imported
#       These are not standard python librarys but are on PyPI
#                       -Elijah Anakalea-Buckley

import libximc.highlevel as ximc
from hispec.util.helper import logger_utils



class SMC(object):
    ''' 
        Class is for utilizing the libximc Library.
        All functions from lib.ximc library is incorperated and this library
        is meant to simplify commands for general use.
        - using the more recently developed libximc.highlevel API
    '''

    def __init__(self, IP: str, port: int, log: bool = True):
        '''
            Inicializes the device
            parameters: IP string, port integer, logging bool
            - full device capabilities will be under "self.device.<functions()>"
        '''
        #Start Logger
        if log:
            if logfile is None:
                logfile = __name__.rsplit(".", 1)[-1] + ".log"
            self.logger = logger_utils.setup_logger(__name__, log_file=logfile)
            if quiet:
                self.logger.setLevel(logging.INFO)
        else:
            self.logger = None

        #Inicialize variables and objects
        # get coms
        self.IP = IP
        self.port = port
        self.dev_open = False


    def open(self):
        '''
            Opens communication to the Device, gathers general information to 
            store in local variables.
            return: Bool for successful or unsuccessful connection
            libximc:: open_device(), get_serial_number(), get_power_setting()
                      command_read_settings(),  get_device_information()
        '''
        #Check if already open
        if self.dev_open:
            #log that device is already open
            if self.logger:
                self.logger.info("Device already open, skipping open command.")
            #return true if already open
            return True
        
        #try to open
        try:
            #open device
            self.device_open()
            #get serial number
            self.serial_number = self.axis.get_serial_number()
            #get power settings
            self.power_setting = self.axis.get_power_setting()
            #get command read settings
            self.command_read_setting = self.axis.command_read_settings()
            #get device information
            self.device_information = self.axis.get_device_information()

            if self.logger:#Log that device is open
                self.logger.info("Device opened successfully.")
                self.logger.info("Serial number: %s", self.serial_number)
                self.logger.info("Power setting: %s", self.power_setting)
                self.logger.info("Command read settings: %s", self.command_read_setting)
                #Log device information
                self.logger.info("Device information: %s", self.device_information)

            #return true if successful
            return True
        except Exception as e:
            #log error
            if self.logger:
                self.logger.error("Error opening device: %s", str(e))
            #return false if unsuccessful
            self.dev_open = False
            return False

    def close(self):
        '''
            Closes communication to the Device
            return: Bool for successful or unsuccessful termination
            libximc:: close_device(), get_position()
        '''
        #Check if already open
        if not self.dev_open:
            #log that de is closed
            if self.logger:
                self.logger.info("Device already closed, skipping close command.")
            return True

        #Try to close
        try:
            self.axis.close_device()
            self.dev_open = False
            if self.logger:
                self.logger.info("Device closed successfully.")
            #return true if succesful
            return True
        except Exception as e:
        #catch error
            #log error and return false
            if self.logger:
                self.logger.error("Error closing device: %s", str(e))
            self.dev_open = True
            return False

    def reference(self):
        '''
            References stage so internal firmware can recalibrate its position
            -Will Reference and move to the last valid position.
            return: bool on successful ref
            libximc::
        '''
        #Check if connection not open
        if not self.dev_open:
            #log closed connection
            if self.logger:
                self.logger.error("Device not open, cannot reference stage.")
            return False

        #try reference
            #get current position

            #start reference
                #provide feedback if reference went well

            #go back to priviouse position
            
            #return true if succesful
        #catch error
            #log error and return false

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
            if self.logger:
                self.logger.error("Device not open, cannot home stage.")
            return False

        #Try to home to zero or parked position
            #return true if succesful
        #catch error
            #log error and return false

    def move_abs(self, position):
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
            if self.logger:
                self.logger.error("Device not open, cannot move stage.")
            return False

        #Try move absolute
            #check limits/valid inputs

            #after move is done, check position with acceptable error
                #return true if succesful
        #catch error
            #log error and return false

    def move_rel(self, position):
        '''
            Move the stage to a RELATIVE position. Send stage to a position
                relative to its current position.
            - Check min_limit and max_limit for range of device
            parameters: min_limit < (current_position+int:"position") < max_limit
            return: bool on successful or unsuccessful relative move
            libximc:: command_movr()
        '''
        #Check if connection not open
        if not self.dev_open:
            #log closed connection
            if self.logger:
                self.logger.error("Device not open, cannot move stage.")
            return False

        #Try move relative
            #check limits/valid inputs

            #after move is done, check position with acceptable error
                #return true if succesful
        #catch error
            #log error and return false

    def get_position(self):
        '''
            Gets Position of stage
            return: position in stage specific units
            libximc::
        '''
        #Check if connection not open
        if not self.dev_open:
            #log closed connection
            if self.logger:
                self.logger.error("Device not open, cannot get position.")
            return False

        #Try get_position
            #return aspects of the position object
        #catch error
            #log error and return None

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
            if self.logger:
                self.logger.error("Device not open, cannot get status.")
            return False

        #Try status function    
            #parse results
            #return status in user friendly way
        #catch error
            #log error and return false

    def halt(self):
        '''
            IMMITATELY halts the stage, no matter the status or if moving, stage
                stops(for safety purposes)
            return: status of the stage(log and/or print hald command called)
            libximc::
        '''
        #Check if connection not open
        if not self.dev_open:
            #log closed connection
            if self.logger:
                self.logger.error("Device not open, cannot halt stage.")
            return False

        #Try imidiate stop of stage
            #return true if succesful
        #catch error
            #log error and return false