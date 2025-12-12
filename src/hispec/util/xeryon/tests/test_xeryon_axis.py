"""Unit tests for the Axis class in the hispec.util.xeryon.axis module."""
import unittest
from unittest.mock import MagicMock
from dataclasses import dataclass
# pylint: disable=no-name-in-module,import-error
from ..axis import Axis
from .test_xeryon_controller import MockStage
from .test_xeryon_communication import MockLogger


@dataclass
class MockXeryonController:
    """A mock Xeryon controller for testing purposes."""

    # pylint: disable=no-self-use
    def is_single_axis_system(self):
        """Return True to indicate this is a single-axis system."""
        return True

    # pylint: disable=no-self-use
    def get_communication(self):
        """Return a mock communication object."""
        return MagicMock(send_command=MagicMock())


class TestAxis(unittest.TestCase):
    """Unit tests for the Axis class."""

    def setUp(self):
        """Set up a mock stage and xeryon controller for testing."""
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
