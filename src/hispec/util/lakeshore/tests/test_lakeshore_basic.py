"""Perform basic tests."""
from lakeshore import LakeshoreController

def test_not_connected():
    """Test not connected."""
    controller = LakeshoreController()
    assert not controller.connected

def test_not_initialized():
    """Test isn't initialized."""
    controller = LakeshoreController()
    assert not controller.initialized

def test_connection_fail():
    """Test connection failure."""
    controller = LakeshoreController()
    controller.set_connection(ip="127.0.0.1", port=50000)
    controller.connect()
    assert not controller.connected
