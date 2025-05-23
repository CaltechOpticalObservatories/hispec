import pytest
from hispec.util import PIControllerBase

def test_initialization():
    controller = PIControllerBase()
    assert not controller.connected

def test_connection_fail():
    with pytest.raises(Exception):
        controller = PIControllerBase()
        controller.connect_tcp(ip="10.0.0.1", port=50000)
