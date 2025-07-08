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
        - step_size:float = 0.0025 Conversion Coefficient, Example  for
            converting steps to mm used in API, adjust as needed
    '''

    def __init__(self, ip: str, port: int, step_size:float = 0.0025, log: bool = True):
        '''
            Inicializes the device
            parameters: ip string, port integer, logging bool
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
        self.ip = ip
        self.port = port
        self.step_size_coeff = step_size  # Example conversion coefficient, adjust as needed(mm)
        self.dev_open = False
        self.axis = ximc.Axis(self.ip, self.port)

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
            #get and save engine settings
            self.engine_settings = self.axis.get_engine_settings()
            #Set calb for user units TODO:: Check if this is correct(SPECIFICALLY THE MICROSTEP MODE)
            self.axis.set_calb(self.step_size_coeff, self.axis.engine_settings.MicrosetpMode)
            #Set limits TODO: Check if this is correct when having the device
            self.limits = self.engine_settings.Limits
            self.min_limit = self.limits.MinLimit
            self.max_limit = self.limits.MaxLimit

            if self.logger:#Log that device is open
                self.logger.info("Device opened successfully.")

            #return true if successful
            self.dev_open = True
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
            if self.logger:
                self.logger.error("Device not open, cannot get info.")
            return False

        #Try to get info
        try:
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
            #log error and return None
            if self.logger:
                self.logger.error("Error getting device information: %s", str(e))
            return False

    def reference(self):
        '''
            References stage so internal firmware can recalibrate its position
            -Will Reference and move to the last valid position.
            return: bool on successful ref
            libximc::

            TODO:: Determine if this is needed, as it is not in the libximc docs
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
        try:
            self.axis.command_homezero()
            self.axis.command_wait_for_stop(100)
            #Check position after homing
            position = self.axis.get_position()
            if self.logger:
                self.logger.info("Stage homed to position: %s", position.Position)   
            #return true if succesful
            return True
        #catch error  
        except Exception as e:
            #log error
            if self.logger:
                self.logger.error("Error homing stage: %s", str(e))
            #return false if unsuccessful
            return False

    def move_abs(self, position):
        '''
            Move the stage to a ABSOLUTE position. Send stage to any specific
                location within the device limits.
            - Check min_limit and max_limit for valid inputs
            parameters: min_limit < int:"position" < max_limit
            return: bool on successful or unsuccessful absolute move
            libximc:: command_move_calb()
        '''
        #Check if connection not open
        if not self.dev_open:
            #log closed connection
            if self.logger:
                self.logger.error("Device not open, cannot move stage.")
            return False

        #Try move absolute
        try:
            #check limits/valid inputs
            if position < self.min_limit or position > self.max_limit:
                if self.logger:
                    self.logger.error("Position out of limits: %s", position)
                return False
            #move absolute
            self.axis.command_move_calb(position)
            self.axis.command_wait_for_stop(100)

            #after move is done, check position
            position = self.axis.get_position_calb()
            if position.Error != 0:
                if self.logger:
                    self.logger.error("Error moving stage: %s", position.Error)
                return False
            else: 
                if self.logger:
                    self.logger.info("Stage moved to position: %s", position.Position)
                #return true if succesful
                return True
        #catch error
        except Exception as e:
            #log error and return false
            if self.logger:
                self.logger.error("Error moving stage: %s", str(e))
            return False

    def move_rel(self, position:float):
        '''
            Move the stage to a RELATIVE position. Send stage to a position
                relative to its current position.
            - Check min_limit and max_limit for range of device
            parameters: min_limit < (current_position+int:"position") < max_limit
            return: bool on successful or unsuccessful relative move
            libximc:: command_movr_calb()
        '''
        #Check if connection not open
        if not self.dev_open:
            #log closed connection
            if self.logger:
                self.logger.error("Device not open, cannot move stage.")
            return False

        #Try move relative
        try:
            #check limits/valid inputs
            #get current position
            current_position = self.axis.get_position_calb().Position
            #calculate new position
            position = current_position + position
            #check if new position is within limits
            if position < self.min_limit or position > self.max_limit:
                if self.logger:
                    self.logger.error("Position out of limits: %s", position)
                return False
            #move relative
            self.axis.command_movr_calb(position)
            self.axis.command_wait_for_stop(100)

            #after move is done, check position
            position = self.axis.get_position_calb()
            if position.Error != 0:
                if self.logger:
                    self.logger.error("Error moving stage: %s", position.Error)
                return False
            else: 
                if self.logger:
                    self.logger.info("Stage moved to position: %s", position.Position)
                #return true if succesful
                return True
        #catch error
        except Exception as e:
            #log error and return false
            if self.logger:
                self.logger.error("Error moving stage: %s", str(e))
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
            if self.logger:
                self.logger.error("Device not open, cannot get position.")
            return False

        #Try get_position
        try:
            #get position
            position = self.axis.get_position_calb()
            #return aspects of the position object
            position_string = f"Position: {position.Position}, " \
                              f"Error: {position.Error}, " \
                              f"Moving: {position.Moving}"
            if self.logger:
                self.logger.info(position_string)
            return position.Position, position_string
        #catch error
        except Exception as e:
            #log error and return None
            if self.logger:
                self.logger.error("Error getting position: %s", str(e))
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
            if self.logger:
                self.logger.error("Device not open, cannot get status.")
            return False

        #Try status function    
        try:
            #get status
            status = self.axis.get_status_calb()
            #parse results
            status_string = f"Status: {status.Status}, Position: {status.Position}, " \
                            f"Error: {status.Error}, Moving: {status.Moving}"
            #return status in user friendly way
            if self.logger:
                self.logger.info(status_string)
            return status_string
        #catch error
        except Exception as e:
            #log error and return false
            if self.logger:
                self.logger.error("Error getting status: %s", str(e))
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
            if self.logger:
                self.logger.error("Device not open, cannot halt stage.")
            return False

        #Try imidiate stop of stage
        try:
            self.axis.command_stop()
            #Check status after halting
            status = self.axis.get_status_calb()
            #TODO:: Finish the halt check
            #status.Moving
            if self.logger:
                self.logger.info("Stage halted successfully.")
            #return true if succesful
            return True
        #catch error
        except Exception as e:
            #log error and return false
            if self.logger:
                self.logger.error("Error halting stage: %s", str(e))
            return False