#################
#Outline Robust and Communication Tests
#################

import pytest
pytestmark = pytest.mark.default
import sys
import os
import unittest
import time

##########################
## CONFIG
## connection and Disconnection in all test
##########################

class Comms_Test(unittest.TestCase):

    #Instances for Test management
    #def setUp(self):
    dev = None
    success = True
    IP = '192.168.29.1'
    port = 10012
    log = False
    error_tolerance = 0.1

    ##########################
    ## Test Connection and Negative connection
    ##########################
    def test_connection(self):
        time.sleep(.2)
        # Open connection     
        self.dev = SMC(ip=self.IP, port = self.port,log = self.log)
        time.sleep(.2)
        self.dev.open()
        time.sleep(.25)
        assert self.dev.get_info()
        assert self.dev.serial_number is not None
        assert self.dev.power_setting is not None
        assert self.dev.command_read_setting is not None
        assert self.dev.device_information is not None
        #Close connection
        self.dev.close()
        time.sleep(.25)
    
    def test_connection_failure(self):
        # Use an unreachable IP (TEST-NET-1 range, reserved for docs/testing)
        bad_ip = "123.456.789.101"
        bad_port = 1234  # usually blocked/unusable
        self.dev = SMC(ip=bad_ip, port=bad_port, log=self.log)
        success = self.dev.open()
        self.assertFalse(success, "Expected connection failure with invalid IP/port")
        self.dev.close()

    ##########################
    ## Status Communication
    ##########################
    def status_communication(self):
        time.sleep(.2)
        # Open connection     
        self.dev = SMC(ip=self.IP, port = self.port,log = self.log)
        time.sleep(.2)
        self.dev.open()
        time.sleep(.25)
        self.dev.get_info()
        status = self.dev.status()
        assert status is not None

        self.dev.close()
        time.sleep(.25)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Comms_Test)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())
