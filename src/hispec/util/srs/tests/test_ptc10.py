"""
Unit tests for the PTC10 class in the srs.ptc10 module.
"""
# pylint: disable=import-error
from ptc10 import PTC10

def test_not_connected():
    """Test not connected."""
    controller = PTC10()
    assert not controller.connected

def test_connection_fail():
    """Test connection failure."""
    controller = PTC10()
    controller.connect("127.0.0.1", 50000)
    assert not controller.connected
