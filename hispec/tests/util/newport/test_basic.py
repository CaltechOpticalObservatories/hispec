import pytest
from hsfei.newport.controller import NewportController

def test_initialization():
    controller = NewportController()
    assert not controller.connected

def test_connection_fail():
    with pytest.raises(Exception):
        controller = NewportController()
        controller.connect(ip="127.0.0.1", port=50000)
        assert not controller.connected
