

import pytest
pytestmark = pytest.mark.integration
import sys
import os
import unittest
import time 

##########################
## CONFIG
## connection and Disconnection in all test
##########################
class Physical_Test(unittest.TestCase):

    #Instances for Test management
    def setUp(self):
        self.dev = None
        self.success = True
        self.IP = '192.168.29.100'
        self.port = 10012
        self.log = False
        self.error_tolerance = 0.1


    ##########################
    ## TestConnection and failure connection
    ##########################
    def test_connection(self):
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

    ##########################
    ## Test Move and Home
    ##########################
    def test_home(self):
        # Open connection    
        self.dev = SMC(ip=self.IP, port = self.port,log = self.log)
        time.sleep(.2)
        self.dev.open()
        time.sleep(.25)
        assert self.dev.get_info()
        status = self.dev.status()
        assert status is not None
        assert self.dev.home()
        time.sleep(.25)
        pos, pos_str = self.dev.get_position()
        assert abs(pos - 0) < self.error_tolerance*2
        
        #Close connection
        self.dev.close()
        time.sleep(.25)

    def test_move(self):
        # Open connection    
        self.dev = SMC(ip=self.IP, port = self.port,log = self.log)
        time.sleep(.2)
        self.dev.open()
        time.sleep(.25)
        assert self.dev.get_info()
        status = self.dev.status()
        assert status is not None
        assert self.dev.home()
        time.sleep(.25)
        pos, pos_str = self.dev.get_position()
        assert abs(pos - 0) < self.error_tolerance*2
        assert self.dev.move_abs(position = 5)
        time.sleep(.25)
        pos, pos_str = self.dev.get_position()
        assert abs(pos - 5) < self.error_tolerance*2
        assert self.dev.move_rel(position = 5.0)
        time.sleep(.25)
        assert abs(pos - 10) < self.error_tolerance*2
        assert self.dev.home()
        time.sleep(.25)
        pos, pos_str = self.dev.get_position()
        assert abs(pos - 0) < self.error_tolerance*2
        #Close connection
        self.dev.close()
        time.sleep(.25)

    def test_halt():
        # Open connection    
        self.dev = SMC(ip=self.IP, port = self.port,log = self.log)
        time.sleep(.2)
        self.dev.open()
        time.sleep(.25)
        assert self.dev.get_info()
        status = self.dev.status()
        assert status is not None
        end = self.dev.max_limit - 1 
        assert self.dev.move_abs(position = end)
        time.sleep(.1)
        assert self.dev.home()
        time.sleep(.2)
        assert self.dev.halt()
        time.sleep(.25)
        pos, pos_str = self.dev.get_position()
        assert pos != 0
        #Close connection
        self.dev.close()
        time.sleep(.25)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Robust_Test)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())