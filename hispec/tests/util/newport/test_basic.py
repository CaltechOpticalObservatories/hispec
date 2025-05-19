import pytest
from hispec.util.newport.smc100pp import StageController

def test_initialization():
    controller = StageController()
    assert not controller.connected

def test_connection_fail():
    with pytest.raises(Exception):
        controller = StageController()
        controller.connect(ip="127.0.0.1", port=50000)
        assert not controller.connected
