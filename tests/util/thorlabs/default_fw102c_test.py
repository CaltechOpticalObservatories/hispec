#################
#Default Communication test
#################

import pytest
pytestmark = pytest.mark.default
import sys
import os
import unittest
import time
from fw102c import FilterWheelController

##########################
## CONFIG
## connection and Disconnection in all test
##########################

class Default_Test(unittest.TestCase):

    #Instances for Test management
    def setUp(self):
        self.dev = FilterWheelController()
        self.success = True
        self.IP = ''
        self.port = 1
        self.log = False
        self.error_tolerance = 0.1

    ##########################
    ## Test Connection
    ##########################
    def test_connection(self):
        time.sleep(.2)
        # Open connection     
        self.dev = FilterWheelController(log = self.log)
        self.dev.set_connection(ip=self.IP, port=self.port)
        assert self.dev.status is None
        self.dev.connect()
        time.sleep(.25)
        assert self.dev.connected
        assert self.dev.success
        assert self.dev.status == 'ready'
        self.dev.disconnect()
        time.sleep(.25)
        assert not self.dev.connected
        assert self.dev.status == 'disconnected'
        time.sleep(.25)


    ##########################
    ## Negative test: failed connect
    ##########################
    def failed_connect_test(self):
        # Use an unreachable IP (TEST-NET-1 range, reserved for docs/testing)
        bad_ip = "192.1.2.123"
        bad_port = 65535  # usually blocked/unusable

        self.dev = FilterWheelController(log=self.log)
        self.dev.set_connection(ip=bad_ip, port=bad_port)
        self.dev.connect()
        time.sleep(.25)
        assert self.dev.success is False, "Expected connection failure with invalid IP/port"
        assert self.dev.connected is False, "Expected not connected state with invalid IP/port"
        self.assertFalse(dev.connected, "Expected connection failure with invalid IP/port")
        self.dev.disconnect()
        time.sleep(.25)

    ##########################
    ## Inicialize test
    ##########################
    def inicialize(self):
        self.dev = FilterWheelController(log = self.log)
        self.dev.set_connection(ip=self.IP, port=self.port)
        self.dev.connect()
        time.sleep(.25)
        self.dev.initialize()
        time.sleep(.25)
        assert self.dev.initialized
        assert self.dev.revision is not None
        self.dev.disconnect()
        time.sleep(.25)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Default_Test)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())
