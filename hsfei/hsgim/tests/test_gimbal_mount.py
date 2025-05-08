import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from PPC102_lib import PPC102_Coms, DATA_CODES
import time

class Test_GimbalMount(unittest.TestCase):

    def test_enable(self):
        '''
            Unit Test for Enable:   -Toggles and checks
                                    -Checks Error Handling
        '''
        # Checks "getter" function: gets state of enable
        self.dev = PPC102_Coms()
        self.dev.open()
        ret = self.dev.get_enable()
        assert ret == DATA_CODES.CHAN_ENABLED or ret == DATA_CODES.CHAN_DISABLED
        # Checks "setter" function; sets state of enable
        self.assertTrue(self.dev.set_enable(channel=1, enable=2))
        ret = self.dev.get_enable()
        assert ret == DATA_CODES.CHAN_DISABLED
        self.assertTrue(self.dev.set_enable(channel=2, enable=2))
        ret = self.dev.get_enable()
        assert ret == DATA_CODES.CHAN_DISABLED
        self.assertTrue(self.dev.set_enable(channel=1, enable=1))
        ret = self.dev.get_enable()
        assert ret == DATA_CODES.CHAN_ENABLED
        self.assertTrue(self.dev.set_enable(channel=2, enable=1))
        ret = self.dev.get_enable()
        assert ret == DATA_CODES.CHAN_ENABLED
        with self.assertRaises(ReferenceError):
            self.dev.get_enable(channel=-1)
            self.dev.get_enable(channel = 3)
        self.assertFalse(self.dev.set_enable(channel=3))
        self.assertFalse(self.dev.set_enable(channel=-1))
        self.assertFalse(self.dev.set_enable(enable=-1))
        self.assertFalse(self.dev.set_enable(enable=3))
        self.dev.close()
        with self.assertRaises(RuntimeError):
            self.dev.get_enable()
            self.dev.set_enable()
        time.sleep(.1)
    
    def test_loop(self):
        self.dev = PPC102_Coms()
        self.dev.open()
        ret = self.dev.get_loop()
        assert ret == DATA_CODES.OPEN_LOOP or ret == DATA_CODES.CLOSED_LOOP
        assert self.dev.set_loop(channel=1, loop=2)
        ret = self.dev.get_loop()
        assert ret == DATA_CODES.CLOSED_LOOP
        assert self.dev.set_loop(channel=2, loop=2)
        ret = self.dev.get_loop()
        assert ret == DATA_CODES.CLOSED_LOOP
        assert self.dev.set_loop(channel=1, loop=1)
        ret = self.dev.get_loop()
        assert ret == DATA_CODES.OPEN_LOOP
        assert self.dev.set_loop(channel=2, loop=1)
        ret = self.dev.get_loop()
        assert ret == DATA_CODES.OPEN_LOOP
        with self.assertRaises(ReferenceError):
            self.dev.get_loop(channel=-1)
            self.dev.get_loop(channel = 3)
        self.assertFalse(self.dev.set_loop(channel=3))
        self.assertFalse(self.dev.set_loop(channel=-1))
        self.assertFalse(self.dev.set_loop(loop=-1))
        self.assertFalse(self.dev.set_loop(loop=3))
        self.dev.close()
        with self.assertRaises(RuntimeError):
            self.dev.get_loop()
            self.dev.set_loop()
        time.sleep(.1)

    def test_max_voltages(self):
        return
    
    def test_positions(self):
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