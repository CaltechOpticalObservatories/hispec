#################
#Functionality test
#Description: Test connection, disconnection, confirming communication with stage,
#               inicialization(or something similar) and movement/position query
#               tests are successful and correct
#################

import pytest
pytestmark = pytest.mark.functional
import sys
import os
import unittest
import time 
from smc8 import SMC

##########################
## CONFIG
## connection and Disconnection in all test 
##########################
class Physical_Test(unittest.TestCase):

    #Instances for Test management
    def setUp(self):
        self.dev = None
        self.success = True
        self.device = ""
        self.log = False
        self.error_tolerance = 0.1
        self.device_connection = "192.168.29.123/9219"
        self.connection_type = "xinet"

    ##########################
    ## TestConnection and failure connection
    ##########################
    def test_connection(self):
        # Open connection     
        self.dev = SMC(device_connection = self.device_connection, connection_type = self.connection_type, log = self.log)
        time.sleep(.2)
        self.dev.open_connection()
        time.sleep(.25)
        assert self.dev.get_info()
        assert self.dev.serial_number is not None
        assert self.dev.power_setting is not None
        assert self.dev.device_information is not None
        #Close connection
        self.dev.close_connection()
        time.sleep(.25)
    
    def test_connection_failure(self):
        # Use an unreachable IP (TEST-NET-1 range, reserved for docs/testing)
        bad_connection = "dev/ximc/0000"
        self.dev = SMC(device_connection = bad_connection, connection_type = self.connection_type, log = self.log)
        success = self.dev.open_connection()
        self.assertFalse(success, "Expected connection failure with invalid IP/port")
        self.dev.close_connection()

    ##########################
    ## Status Communication
    ##########################
    def status_communication(self):
        # Open connection     
        self.dev = SMC(device_connection = self.device_connection, connection_type = self.connection_type, log = self.log)
        time.sleep(.2)
        self.dev.open_connection()
        time.sleep(.25)
        self.dev.get_info()
        status = self.dev.status()
        assert status is not None

        self.dev.close_connection()
        time.sleep(.25)

    ##########################
    ## Test Move and Home
    ##########################
    def test_home(self):
        # Open connection    
        self.dev = SMC(device_connection = self.device_connection, connection_type = self.connection_type, log = self.log)
        time.sleep(.2)
        self.dev.open_connection()
        time.sleep(.25)
        assert self.dev.get_info()
        status = self.dev.status()
        assert status is not None
        assert self.dev.home()
        time.sleep(.25)
        pos = self.dev.get_position()
        assert abs(pos - 0) < self.error_tolerance*2
        
        #Close connection
        self.dev.close_connection()
        time.sleep(.25)

    def test_move(self):
        # Open connection    
        self.dev = SMC(device_connection = self.device_connection, connection_type = self.connection_type, log = self.log)
        time.sleep(.2)
        self.dev.open_connection()
        time.sleep(.25)
        assert self.dev.get_info()
        status = self.dev.status()
        assert status is not None
        assert self.dev.home()
        time.sleep(.25)
        pos = self.dev.get_position()
        assert abs(pos - 0) < self.error_tolerance*2
        assert self.dev.move_abs(position = 5)
        time.sleep(.25)
        pos = self.dev.get_position()
        assert abs(pos - 5) < self.error_tolerance*2
        assert self.dev.move_rel(position = 5)
        time.sleep(.25)
        pos = self.dev.get_position()
        assert abs(pos - 10) < self.error_tolerance*2
        assert self.dev.home()
        time.sleep(.25)
        pos = self.dev.get_position()
        assert abs(pos - 0) < self.error_tolerance*2
        #Close connection
        self.dev.close_connection()
        time.sleep(.25)

    def test_halt(self):
        # Open connection    
        self.dev = SMC(device_connection = self.device_connection, connection_type = self.connection_type, log = self.log)
        time.sleep(.2)
        self.dev.open_connection()
        time.sleep(.25)
        assert self.dev.get_info()
        status = self.dev.status()
        assert status is not None
        end = self.dev.max_limit - 1 
        assert self.dev.move_abs(position = end)
        time.sleep(2)
        assert self.dev.move_abs(position = (self.dev.min_limit + 1))
        assert self.dev.halt()
        time.sleep(.25)
        pos = self.dev.get_position()
        assert pos != (self.dev.min_limit + 1)
        #Close connection
        self.dev.home()
        time.sleep(.25) 
        self.dev.close_connection()
        time.sleep(.25)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Robust_Test)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())