"""Perform basic tests."""
import pytest
from SPCe import SpceController

def test_initialization():
    """Test initialization."""
    controller = SpceController()
    assert not controller.connected

def test_connection_fail():
    """Test connection failure."""
    controller = SpceController()
    controller.connect(host="127.0.0.1", port=50000)
    assert not controller.connected
