import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from hispec.util.thorlabs.gimbal.PPC102_lib import PPC102_Coms, DATA_CODES
import time

inifile = "BlueGimbalMount.ini"

class Test_GimbalMount(unittest.TestCase):

    def test_enable(self):
        '''
            Unit Test for Enable:   -Toggles and checks
                                    -Checks Error Handling
        '''
        # Checks "getter" function: gets state of enable
        self.dev = PPC102_Coms(IP='192.168.29.100', port = 10013)
        self.dev.open()
        ret = self.dev.get_enable(channel = 1)
        assert ret == DATA_CODES.CHAN_ENABLED or ret == DATA_CODES.CHAN_DISABLED
        # Checks "setter" function; sets state of enable
        for ch in [1,2]:
            self.assertTrue(self.dev.set_enable(channel=ch, enable=2))
            ret = self.dev.get_enable(channel=ch)
            assert ret == DATA_CODES.CHAN_DISABLED
            self.assertTrue(self.dev.set_enable(channel=ch, enable=1))
            ret = self.dev.get_enable(channel = ch)
            assert ret == DATA_CODES.CHAN_ENABLED
        self.assertFalse(self.dev.set_enable(channel=3))
        self.assertFalse(self.dev.set_enable(channel=-1))
        self.assertFalse(self.dev.set_enable(enable=-1))
        self.assertFalse(self.dev.set_enable(enable=3))
        self.assertTrue(self.dev.set_enable(enable = 2))
        ret = self.dev.get_enable()
        assert ret[0] == DATA_CODES.CHAN_DISABLED
        assert ret[1] == DATA_CODES.CHAN_DISABLED
        self.assertTrue(self.dev.set_enable(enable = 1))
        ret = self.dev.get_enable()
        assert ret[0] == DATA_CODES.CHAN_ENABLED
        assert ret[1] == DATA_CODES.CHAN_ENABLED
        self.dev.close()
        time.sleep(.25)
        with self.assertRaises(Exception):
            self.dev.get_enable()
            self.dev.set_enable()
        time.sleep(.25)
    
    def test_loop(self):
        self.dev = PPC102_Coms(IP='192.168.29.100', port = 10013)
        time.sleep(.2)
        self.dev.open()
        time.sleep(.25)
        for ch in [1,2]:
            ret = self.dev.get_loop(channel=ch)
            assert ret == DATA_CODES.OPEN_LOOP or ret == DATA_CODES.CLOSED_LOOP
            assert self.dev.set_loop(channel=ch, loop=2)
            ret = self.dev.get_loop(channel=ch)
            assert ret == DATA_CODES.CLOSED_LOOP
            assert self.dev.set_loop(channel=ch, loop=1)
            ret = self.dev.get_loop(channel=ch)
            assert ret == DATA_CODES.OPEN_LOOP
        self.assertFalse(self.dev.set_loop(channel=3))
        self.assertFalse(self.dev.set_loop(channel=-1))
        self.assertFalse(self.dev.set_loop(loop=-1))
        self.assertFalse(self.dev.set_loop(loop=3))
        self.assertTrue(self.dev.set_loop(loop = 2))
        ret = self.dev.get_loop()
        assert ret[0] == DATA_CODES.CLOSED_LOOP
        assert ret[1] == DATA_CODES.CLOSED_LOOP
        self.assertTrue(self.dev.set_loop(loop = 1))
        ret = self.dev.get_loop()
        assert ret[0] == DATA_CODES.OPEN_LOOP
        assert ret[1] == DATA_CODES.OPEN_LOOP
        self.dev.close()
        time.sleep(.25)
        with self.assertRaises(Exception):
            self.dev.get_loop()
            self.dev.set_loop()
        time.sleep(.25)

    def test_max_voltages(self):
        #Max Voltage
        self.dev = PPC102_Coms(IP='192.168.29.100', port = 10013)
        self.dev.open()
        time.sleep(.25)
        for ch in [1,2]:
            ret = self.dev.get_max_output_voltage(channel=ch)
            assert self.dev.set_max_output_voltage(channel=ch, limit=100)
            ret = self.dev.get_max_output_voltage(channel=ch)
            assert ret == 100
            assert self.dev.set_max_output_voltage(channel=ch, limit=150)
            ret = self.dev.get_max_output_voltage(channel=ch)
            assert ret == 150
        self.assertFalse(self.dev.set_max_output_voltage(channel=3, limit=100))
        self.assertFalse(self.dev.set_max_output_voltage(channel=2, limit=250))
        self.assertFalse(self.dev.set_max_output_voltage(channel=0, limit=100))
        self.assertFalse(self.dev.set_max_output_voltage(channel=-1, limit=200))
        self.assertFalse(self.dev.set_max_output_voltage(channel=1, limit=-100))
        self.dev.close()
        time.sleep(0.1)
        with self.assertRaises(Exception):
            self.dev.get_max_output_voltage(channel=1)
            self.dev.set_max_output_voltage(channel=1,limit=50)
        time.sleep(.25)
        return
    
    def test_positions(self):
        #CLOSED LOOP CONTROL
        self.dev = PPC102_Coms(IP='192.168.29.100', port = 10013)
        time.sleep(.25)
        self.dev.open()
        time.sleep(.25)
        for ch in [1,2]:
            self.dev.set_loop(channel=ch,loop=2)
            self.dev.set_position(channel=ch,pos=100)
            res = self.dev.get_position(channel=ch)
            assert 90 < res < 110
            self.dev.set_position(channel=ch,pos=1000)
            res = self.dev.get_position(channel=ch)
            assert 990 < res < 1010
            self.dev.set_position(channel=ch,pos=31000)
            res = self.dev.get_position(channel=ch)
            assert 30995 < res < 31005
            self.dev.set_loop(channel=ch,loop=1)
            self.assertFalse(self.dev.set_position(channel=ch, pos=2000))
            self.assertFalse(self.dev.set_position(channel=ch,pos=100))
            self.assertFalse(self.dev.get_position(channel=ch))
            assert(self.dev.set_output_volts(channel=ch, volts=0))
        self.assertFalse(self.dev.set_position(channel=-1, pos=2000))
        self.assertFalse(self.dev.set_position(channel=3,pos=100))
        self.assertFalse(self.dev.get_position(channel=0))
        self.dev.close()
        time.sleep(.25)
        return

    def test_output_voltage(self):
        #OPEN LOOP CONTROL
        self.dev = PPC102_Coms(IP='192.168.29.100', port = 10013)
        self.dev.open()
        for ch in [1,2]:
            self.dev.set_loop(channel=ch,loop=2)
            self.assertFalse(self.dev.set_output_volts(channel=ch, volts=0))
            self.dev.set_loop(channel=ch,loop=1)
            self.dev.set_output_volts(channel=ch,volts=100)
            res = self.dev.get_output_volts(channel=ch)
            assert 95 < res < 105
            self.dev.set_output_volts(channel=ch,volts=1000)
            res = self.dev.get_output_volts(channel=ch)
            assert 995 < res < 1005
            self.dev.set_output_volts(channel=ch,volts=31000)
            res = self.dev.get_output_volts(channel=ch)
            assert 30980 < res < 31020
            assert(self.dev.set_output_volts(channel=ch, volts=0))
        self.assertFalse(self.dev.set_output_volts(channel=-1, volts=2000))
        self.assertFalse(self.dev.set_output_volts(channel=3,volts=100))
        self.assertFalse(self.dev.get_output_volts(channel=0))
        self.dev.close()
        time.sleep(.25)
        return

    def test_isupper(self):
        self.assertTrue('FOO'.isupper())
        self.assertFalse('Foo'.isupper())

    def test_split(self):
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # check that s.split fails when the separator is not a string
        #TODO:: implement these backward checks to make sure they raise the right errors
        with self.assertRaises(TypeError):
            s.split(2)

if __name__ == '__main__':
    unittest.main()