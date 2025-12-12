"""Perform basic tests."""
from dd100mc import OZController

def test_initialization():
    """Test initialization."""
    controller = OZController()
    assert not controller.connected

def test_connection_fail():
    """Test connection failure."""
    controller = OZController()
    controller.connect("127.0.0.1", 50000)
    assert not controller.connected
