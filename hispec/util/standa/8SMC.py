#NOTE:: Pip install of libximc is needed to use the library imported
#       These are not standard python librarys but are on PyPI
#                       -Elijah Anakalea-Buckley

import libximc.highlevel as ximc



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
        #Check for valid inputs

        #Start Logger

        #Inicialize variables and objects


    def open(self):
        '''
            Opens communication to the Device, gathers general information to 
            store in local variables.
            return: Bool for successful or unsuccessful connection
            libximc:: open_device(), get_serial_number(), get_power_setting()
                      command_read_settings(),  get_device_information()
        '''
        #Check if already open
        
        #try to open
            #return true if successful
        #catch error
            #log error and return false

    def close(self):
        '''
            Closes communication to the Device
            return: Bool for successful or unsuccessful termination
            libximc:: close_device(), get_position()
        '''
        #Check if device is open

        #Try to close
            #double check that connection is terminated
            #return true if succesful
        #catch error
            #log error and return false

    def reference(self):
        '''
            References stage so internal firmware can recalibrate its position
            -Will Reference and move to the last valid position.
            return: bool on successful ref
            libximc::
        '''
        #Check if device is open

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
        #Check if device is open

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
        #Check if device is open

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
        #Check if device is open

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
        #Check if device is open

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
        #Check if device is open

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
        #Check if device is open

        #Try imidiate stop of stage
            #return true if succesful
        #catch error
            #log error and return false