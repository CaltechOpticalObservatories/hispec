#################
#Default Communication test
#Description: Test connection, disconnection and confirming communication with stage
#################

import pytest
pytestmark = pytest.mark.default
import sys
import os
import unittest
import time
from smc8 import SMC

##########################
## CONFIG
## connection and Disconnection in all test
##########################

class Comms_Test(unittest.TestCase):

    #Instances for Test management
    #def setUp(self):
    dev = None
    success = True
    device = ""
    log = False
    error_tolerance = 0.1
    device_connection = "192.168.29.123/9219"
    connection_type = "xinet"

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
        time.sleep(.2)
        # Open connection     
        self.dev = SMC(device_connection = self.device_connection, connection_type = self.connection_type, log = self.log)
        time.sleep(.2)
        self.dev.open_connection()
        time.sleep(.25)
        assert self.dev.get_info()
        status = self.dev.status()
        assert status is not None

        self.dev.close_connection()
        time.sleep(.25)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Comms_Test)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())
