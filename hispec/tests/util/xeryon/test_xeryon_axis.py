import unittest
from unittest.mock import MagicMock
from hispec.util.xeryon.axis import Axis


class MockStage:
    isLineair = True
    encoderResolutionCommand = "XLS1=312"
    encoderResolution = 312.5
    speedMultiplier = 1000
    amplitudeMultiplier = 1456.0
    phaseMultiplier = 182


class MockXeryonController:
    def is_single_axis_system(self):
        return True

    def get_communication(self):
        return MagicMock(send_command=MagicMock())

class MockLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg, *args, **kwargs):
        self.messages.append(('info', msg))

    def debug(self, msg, *args, **kwargs):
        self.messages.append(('debug', msg))

    def warning(self, msg, *args, **kwargs):
        self.messages.append(('warning', msg))

    def error(self, msg, *args, **kwargs):
        self.messages.append(('error', msg))

    def critical(self, msg, *args, **kwargs):
        self.messages.append(('critical', msg))

class TestAxis(unittest.TestCase):

    def setUp(self):
        self.stage = MockStage()
        self.xeryon = MockXeryonController()
        self.axis = Axis(self.xeryon, "X", self.stage, MockLogger())

    def test_set_setting_stores_value(self):
        """Test that set_setting correctly stores a setting in the internal dictionary."""
        self.axis.set_setting("VEL", "500")
        self.assertEqual(self.axis.settings["VEL"], "500")

    def test_get_setting_returns_value(self):
        """Test that get_setting returns the correct value for a known tag."""
        self.axis.settings["ACC"] = "100"
        self.assertEqual(self.axis.get_setting("ACC"), "100")

    def test_send_command_stores_in_settings(self):
        """Test that send_command routes to set_setting for supported tags."""
        self.axis.set_setting = MagicMock()
        self.axis.send_command("VEL=200")
        self.axis.set_setting.assert_called_with("VEL", "200")

    def test_reset_clears_flag_and_sends(self):
        """Test that reset sends the correct command and clears the was_valid_DPOS flag."""
        self.axis.send_command = MagicMock()
        self.axis.was_valid_DPOS = True
        self.axis.reset()
        self.axis.send_command.assert_called_with("RSET=0")
        self.assertFalse(self.axis.was_valid_DPOS)

    def test_get_letter_returns_axis_letter(self):
        """Test that get_letter returns the correct axis letter."""
        self.assertEqual(self.axis.get_letter(), "X")

    def test_convert_units_to_encoder_mm(self):
        """Test conversion from millimeters to encoder units."""
        enc = self.axis.convert_units_to_encoder(1, self.axis.units)
        expected = round(1 * 1e6 / self.stage.encoderResolution)
        self.assertEqual(enc, expected)

    def test_convert_encoder_to_units_mm(self):
        """Test conversion from encoder units to millimeters."""
        val = self.axis.convert_encoder_units_to_units(312500, self.axis.units)
        expected = 312500 / (1e6 / self.stage.encoderResolution)
        self.assertAlmostEqual(val, expected, places=2)


if __name__ == '__main__':
    unittest.main()
