import pytest
from hsfei import NewportController

def test_initialization():
    controller = NewportController()
    assert not controller.connected

def test_connection_fail():
    with pytest.raises(Exception):
        controller = NewportController()
        controller.connect(ip="10.0.0.1", port=50000)
