import unittest
from unittest.mock import MagicMock
from ..axis import Axis

class MockStage:
    isLineair = True
    encoderResolutionCommand = "XLS1=312"
    encoderResolution = 312.5
    speedMultiplier = 1000
    amplitudeMultiplier = 1456.0
    phaseMultiplier = 182

class MockXeryonController:
    def isSingleAxisSystem(self):
        return True

    def getCommunication(self):
        return MagicMock(sendCommand=MagicMock())

class TestAxis(unittest.TestCase):

    def setUp(self):
        self.stage = MockStage()
        self.xeryon = MockXeryonController()
        self.axis = Axis(self.xeryon, "X", self.stage)

    def test_set_setting_stores_value(self):
        """Test that setSetting correctly stores a setting in the internal dictionary."""
        self.axis.setSetting("VEL", "500")
        self.assertEqual(self.axis.settings["VEL"], "500")

    def test_get_setting_returns_value(self):
        """Test that getSetting returns the correct value for a known tag."""
        self.axis.settings["ACC"] = "100"
        self.assertEqual(self.axis.getSetting("ACC"), "100")

    def test_send_command_stores_in_settings(self):
        """Test that sendCommand routes to setSetting for supported tags."""
        self.axis.setSetting = MagicMock()
        self.axis.sendCommand("VEL=200")
        self.axis.setSetting.assert_called_with("VEL", "200")

    def test_reset_clears_flag_and_sends(self):
        """Test that reset sends the correct command and clears the was_valid_DPOS flag."""
        self.axis.sendCommand = MagicMock()
        self.axis.was_valid_DPOS = True
        self.axis.reset()
        self.axis.sendCommand.assert_called_with("RSET=0")
        self.assertFalse(self.axis.was_valid_DPOS)

    def test_get_letter_returns_axis_letter(self):
        """Test that getLetter returns the correct axis letter."""
        self.assertEqual(self.axis.getLetter(), "X")

    def test_convert_units_to_encoder_mm(self):
        """Test conversion from millimeters to encoder units."""
        enc = self.axis.convertUnitsToEncoder(1, self.axis.units)
        expected = round(1 * 1e6 / self.stage.encoderResolution)
        self.assertEqual(enc, expected)

    def test_convert_encoder_to_units_mm(self):
        """Test conversion from encoder units to millimeters."""
        val = self.axis.convertEncoderUnitsToUnits(312500, self.axis.units)
        expected = 312500 / (1e6 / self.stage.encoderResolution)
        self.assertAlmostEqual(val, expected, places=2)

if __name__ == '__main__':
    unittest.main()
