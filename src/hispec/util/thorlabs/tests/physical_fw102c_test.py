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
from fw102c import FilterWheelController


##########################
## CONFIG
## connection and Disconnection in all test
##########################
class Physical_Test(unittest.TestCase):

    #Instances for Test management
    def setUp(self):
        self.dev = FilterWheelController()
        self.success = True
        self.ip = '192.168.29.100'
        self.port = 10010
        self.log = False
        self.error_tolerance = 0.1

    ##########################
    ## Test Connection
    ##########################
    def test_connection(self):
        time.sleep(.2)
        # Open connection     
        self.dev = FilterWheelController(log = self.log)
        self.dev.set_connection(ip=self.ip, port=self.port)
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
    ## Inicialize test
    ##########################
    def inicialize(self):
        self.dev = FilterWheelController(log = self.log)
        self.dev.set_connection(ip=self.ip, port=self.port)
        self.dev.connect()
        time.sleep(.25)
        self.dev.initialize()
        time.sleep(.25)
        assert self.dev.initialized
        assert self.dev.revision is not None
        self.dev.disconnect()
        time.sleep(.25)

    ##########################
    ## Position Query and Movement
    ##########################
    def test_position_query_and_movement(self):
        self.dev = FilterWheelController(log = self.log)
        self.dev.set_connection(ip=self.ip, port=self.port)
        self.dev.connect()
        time.sleep(.25)
        self.dev.initialize()
        # Set position and assert
        self.dev.move(target=1)
        time.sleep(.25)
        ret = int(self.dev.get_position())
        assert ret == 1
        self.dev.move(target=2)
        time.sleep(.25)
        ret = int(self.dev.get_position())
        assert ret == 2
        self.dev.move(target=5)
        time.sleep(.25)
        ret = int(self.dev.get_position())
        assert ret == 5
        self.dev.move(target=1)
        time.sleep(.25)
        ret = int(self.dev.get_position())
        assert ret == 1
        #Close connection
        self.dev.disconnect()
        time.sleep(.25)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Robust_Test)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())
