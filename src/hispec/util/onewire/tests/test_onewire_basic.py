"""Perform basic tests."""
import pytest

import onewire
from onewire import ONEWIRE

def test_not_connected():
    """Test not connected."""
    controller = ONEWIRE()
    assert not controller.connected

def test_connection_fail():
    """Test connection failure."""
    controller = ONEWIRE()
    with pytest.raises(onewire.DeviceConnectionError):
        controller.connect("127.0.0.1", 9999)
