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
from ppc102 import PPC102_Coms

##########################
## CONFIG
## connection and Disconnection in all test
##########################

class Comms_Test(unittest.TestCase):

    #Instances for Test management
    #def setUp(self):
    dev = None
    success = True
    ip = '192.168.29.100'
    port = 10012
    log = False
    error_tolerance = 0.1

    ##########################
    ## Servos / Loops [ Not really applicable]
    ##########################
    def test_loop(self):
        time.sleep(.2)
        # Open connection     
        self.dev = PPC102_Coms(ip=self.ip, port = self.port,log = self.log)
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
    ## Negative test: failed connect
    ##########################
    def failed_connect_test(self):
        # Use an unreachable ip (TEST-NET-1 range, reserved for docs/testing)
        bad_ip = "192.1.2.123"
        bad_port = 65535  # usually blocked/unusable

        dev = PPC102_Coms(ip=bad_ip, port=bad_port, log=self.log)

        success = dev.open()
        self.assertFalse(success, "Expected connection failure with invalid ip/port")
        dev.close()

    ##########################
    ## Limit Check
    ##########################
    def test_limit(self):
         # Open connection     
        self.dev = PPC102_Coms(ip=self.ip, port = self.port,log = self.log)
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
    def test_position_query(self):
        self.dev = PPC102_Coms(ip=self.ip, port = self.port,log = self.log)
        self.dev.open()
        time.sleep(.25)
        for ch in [1,2]:  # Check for channels that are applicable
            # Close loops and assert
            assert self.dev.set_loop(channel=ch, loop=self.dev.CLOSED_LOOP)
            ret = self.dev.get_loop(channel=ch)
            assert ret == self.dev.CLOSED_LOOP
            
            # Get position and assert
            original_position = self.dev.get_position(channel=ch)
            #make sure that balue returned is a not none type
            assert original_position is not None
            #open loops and assert
            assert self.dev.set_loop(channel=ch, loop=self.dev.OPEN_LOOP)
            ret = self.dev.get_loop(channel=ch)
            assert ret == self.dev.OPEN_LOOP

        #Close connection
        self.dev.close()
        time.sleep(.25)

    ##########################
    ## Status Communication
    ##########################
    def status_communication(self):
        self.dev = PPC102_Coms(ip=self.ip, port = self.port,log = self.log)
        self.dev.open()
        time.sleep(.25)
        for ch in [1,2]:  # Check for channels that are applicable
            # Get status and assert
            ret = self.dev.get_status_update(channel=ch)
            assert ret is not None
            # Get status bits
            ret = self.dev.get_status_bits(channel=ch)
            assert ret is not None
        self.dev.close()
        time.sleep(.25)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Comms_Test)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())
