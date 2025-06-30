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
            Inicializes the device and gathers general information to store
            in local variables.
            parameters: IP string, port integer, logging bool
            - full device capabilities will be under "self.device.<functions()>"
        '''

    def open(self):
        '''
            Opens communication to the Device
            return: Bool for successful or unsuccessful connection
        '''

    def close(self):
        '''
            Closes communication to the Device
            return: Bool for successful or unsuccessful termination
        '''

    def reference(self):
        '''
            References stage so internal firmware can recalibrate its position
            -Will Reference and move to the last valid position.
            return: bool on successful ref
        '''

    def home(self):
        '''
            Homes stage into "parked" positon
            -Will Home and stay at homed position.
            return: bool on successful home
        '''

    def move_abs(self, position):
        '''
            Move the stage to a ABSOLUTE position. Send stage to any specific
                location within the device limits.
            - Check min_limit and max_limit for valid inputs
            parameters: min_limit < int:"position" < max_limit
            return: bool on successful or unsuccessful absolute move
        '''

    def move_rel(self, position):
        '''
            Move the stage to a RELATIVE position. Send stage to a position
                relative to its current position.
            - Check min_limit and max_limit for range of device
            parameters: min_limit < (current_position+int:"position") < max_limit
            return: bool on successful or unsuccessful relative move
        '''

    def get_position(self):
        '''
            Gets Position of stage
            return: position in stage specific units
        '''

    def status(self):
        '''
            Gathers status and formats it in a usable and readable format.
                mostly for logging
            return: status string and variables nessesary
        '''

    def halt(self):
        '''
            IMMITATELY halts the stage, no matter the status or if moving, stage
                stops(for safety purposes)
            return: status of the stage(log and/or print hald command called)
        '''