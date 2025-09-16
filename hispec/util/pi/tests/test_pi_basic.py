"""
# Test for the PIControllerBase class from the hispec.util module
"""
import pytest
# pylint: disable=import-error, no-name-in-module
from pi import PIControllerBase

def test_initialization():
    """Test that the PIControllerBase initializes correctly."""
    controller = PIControllerBase()
    assert not controller.connected


def test_connection_fail():
    """Test that connecting to an invalid IP raises an exception."""
    with pytest.raises(Exception):
        controller = PIControllerBase()
        controller.connect_tcp(ip_address="10.0.0.1", port=50000)
