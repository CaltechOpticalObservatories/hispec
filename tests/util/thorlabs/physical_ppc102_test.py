#################
#Outline Robust and Communication Tests (Integeration Tests)
#################

import pytest
pytestmark = pytest.mark.integration
import sys
import os
import unittest
import time 
from ppc102 import PPC102_Coms

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
    ## Servos / Loops [ Not really applicable]
    ##########################
    def test_loop(self):
        time.sleep(.2)
        # Open connection     
        self.dev = PPC102_Coms(IP=self.IP, port = self.port,log = self.log)
        time.sleep(.2)
        self.dev.open()
        time.sleep(.25)
        for ch in [1,2]:#Check for channels that are applicable
            #Close Loop assert Loop states
            ret = self.dev.get_loop(channel=ch)
            assert ret == self.dev.OPEN_LOOP or ret == self.dev.CLOSED_LOOP
            assert self.dev.set_loop(channel=ch, loop=2)
            ret = self.dev.get_loop(channel=ch)
            assert ret == self.dev.CLOSED_LOOP
            #Open Loops and assert the states
            assert self.dev.set_loop(channel=ch, loop=1)
            ret = self.dev.get_loop(channel=ch)
            assert ret == self.dev.OPEN_LOOP
        self.assertFalse(self.dev.set_loop(channel=5))
        self.assertFalse(self.dev.set_loop(channel=-1))
        self.assertTrue(self.dev.set_loop(loop = 4))
        ret = self.dev.get_loop(channel = 0)
        assert ret[0] == self.dev.CLOSED_LOOP
        assert ret[1] == self.dev.CLOSED_LOOP
        self.assertTrue(self.dev.set_loop(loop = 1))
        ret = self.dev.get_loop(channel = 0)
        assert ret[0] == self.dev.OPEN_LOOP
        assert ret[1] == self.dev.OPEN_LOOP
        self.dev.close()
        time.sleep(.25)
        with self.assertRaises(Exception):
            self.dev.get_loop()
            self.dev.set_loop()
        time.sleep(.25)
        #Close connection
        self.dev.close()
        time.sleep(.25)


    ##########################
    ## Limit Check
    ##########################
    def test_limit(self):
         # Open connection     
        self.dev = PPC102_Coms(IP=self.IP, port = self.port,log = self.log)
        time.sleep(.2)
        self.dev.open()
        time.sleep(.25)
        for ch in [1,2]:  # Check for channels that are applicable
            # Check limit states and save to variable
            original_limit = self.dev.get_max_output_voltage(channel=ch)
            print(f"Channel {ch} Max output Voltage: {original_limit}")
            # Set limit states and assert
            assert self.dev.set_max_output_voltage(channel=ch, limit=75)
            ret = self.dev.get_max_output_voltage(channel=ch)
            print(f"New Channel {ch} Max output Voltage: {ret}")
            # set limits back to default
            assert self.dev.set_max_output_voltage(channel=ch, limit=original_limit)
            ret = self.dev.get_max_output_voltage(channel=ch)
            print(f"Back to Original Channel {ch} Max output Voltage: {ret}")

        #Close connection
        self.dev.close()
        time.sleep(.25)

    ##########################
    ## Position Query and Movement
    ##########################
    def test_position_query_and_movement(self):
        self.dev = PPC102_Coms(IP=self.IP, port = self.port,log = self.log)
        self.dev.open()
        time.sleep(.25)
        for ch in [1,2]:  # Check for channels that are applicable
            # Close loops and assert
            ret = self.dev.get_loop(channel=ch)
            assert ret == self.dev.OPEN_LOOP or ret == self.dev.CLOSED_LOOP
            assert self.dev.set_loop(channel=ch, loop=self.dev.CLOSED_LOOP)
            ret = self.dev.get_loop(channel=ch)
            assert ret == self.dev.CLOSED_LOOP
            # Set position and assert
            assert self.dev.set_position(channel=ch, pos=0)
            time.sleep(.2)
            # Get position and assert
            ret = self.dev.get_position(channel=ch)
            assert abs(ret - 0) < self.error_tolerance*2
            original_position = ret
            print(f"Channel {ch} Original Position: {original_position}")
            # Set position and assert with Error Tolerance x2
            assert self.dev.set_position(channel=ch, pos=5.0)
            time.sleep(.2)
            ret = self.dev.get_position(channel=ch)
            assert abs(ret - 5.0) < self.error_tolerance*2
            print(f"Channel {ch} New Position: {ret}")
            # Set position back to default
            assert self.dev.set_position(channel=ch, pos=original_position)
            time.sleep(.2)
            ret = self.dev.get_position(channel=ch)
            assert abs(ret - original_position) < self.error_tolerance*2
            print(f"Channel {ch} Back to Original Position: {ret}")
            #open loops and assert
            assert self.dev.set_loop(channel=ch, loop=self.dev.OPEN_LOOP)
            ret = self.dev.get_loop(channel=ch)
            assert ret == self.dev.OPEN_LOOP

        #Close connection
        self.dev.close()
        time.sleep(.25)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Robust_Test)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())