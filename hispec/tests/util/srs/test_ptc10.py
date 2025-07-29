"""
Unit tests for the PTC10 class in the hispec.util.srs.ptc10 module.
"""
import unittest
from unittest.mock import MagicMock
# pylint: disable=import-error,no-name-in-module
from hispec.util.srs.ptc10_connection import PTC10Connection
from hispec.util.srs.ptc10 import PTC10


class TestPTC10(unittest.TestCase):
    """Unit tests for the PTC10 class."""
    def setUp(self):
        """Set up the test case with a mock connection."""
        self.mock_conn = MagicMock(spec=PTC10Connection)
        self.ptc = PTC10(self.mock_conn)

    def test_identify(self):
        """Test the identify method."""
        self.mock_conn.query.return_value = (
            "Stanford Research Systems, PTC10, version 4.63"
        )
        result = self.ptc.identify()
        self.assertEqual(result, "Stanford Research Systems, PTC10, version 4.63")
        self.mock_conn.query.assert_called_with("*IDN?")

    def test_get_channel_value(self):
        """Test getting a channel value."""
        self.mock_conn.query.return_value = "25.6"
        result = self.ptc.get_channel_value("3A")
        self.assertEqual(result, 25.6)
        self.mock_conn.query.assert_called_with("3A?")

    def test_get_all_values(self):
        """Test getting all channel values."""
        self.mock_conn.query.return_value = "1.0,2.0,NaN,4.0"
        result = self.ptc.get_all_values()
        self.assertEqual(result[0:2], [1.0, 2.0])
        self.assertTrue(result[2] != result[2])  # NaN check
        self.assertEqual(result[3], 4.0)

    def test_get_channel_names(self):
        """Test getting channel names."""
        self.mock_conn.query.return_value = "Out1,Out2,3A,3B"
        result = self.ptc.get_channel_names()
        self.assertEqual(result, ["Out1", "Out2", "3A", "3B"])
        self.mock_conn.query.assert_called_with("getOutputNames?")

    def test_get_named_output_dict(self):
        """Test getting named output dictionary."""
        self.mock_conn.query.side_effect = ["Out1,Out2,3A,3B", "1.0,2.0,3.0,4.0"]
        result = self.ptc.get_named_output_dict()
        expected = {"Out1": 1.0, "Out2": 2.0, "3A": 3.0, "3B": 4.0}
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
