import json
from unittest.mock import MagicMock, patch
from hispec.util import PIControllerBase


@patch('hispec.util.pi.pi_controller.GCSDevice')
def test_connect_disconnect(mock_gcs_device_cls):
    mock_device = MagicMock()
    mock_gcs_device_cls.return_value = mock_device

    controller = PIControllerBase()
    
    controller.connect_tcp('127.0.0.1', 50000)
    mock_device.ConnectTCPIP.assert_called_once_with('127.0.0.1', 50000)
    assert controller.connected

    controller.disconnect()
    mock_device.CloseConnection.assert_called_once()
    assert not controller.connected


@patch('hispec.util.pi.pi_controller.GCSDevice')
def test_get_serial_number(m):
    controller = PIControllerBase()
    controller.connected = True
    controller.device.qIDN.return_value = "PI,Model,123456,1.0.0"
    
    serial = controller.get_serial_number()
    assert serial == "123456"


@patch('hispec.util.pi.pi_controller.GCSDevice')
def test_get_position(mock_gcs_device_cls):
    mock_device = MagicMock()
    mock_gcs_device_cls.return_value = mock_device

    controller = PIControllerBase()
    controller.connected = True
    controller.device.axes = ['1', '2']
    controller.device.qPOS.return_value = {'1': 42.0}

    pos = controller.get_position(0)
    assert pos == 42.0
    controller.device.qPOS.assert_called_once_with('1')


def test_set_and_go_to_named_position(tmp_path):
    controller = PIControllerBase()
    controller.named_position_file=tmp_path / "positions.json"
    controller.connected = True
    controller.device = MagicMock()
    controller.device.axes = ['1']
    controller.get_position = MagicMock(return_value=10.0)
    controller.get_serial_number = MagicMock(return_value="123456")

    controller.set_named_position('1', 'home')

    with open(controller.named_position_file) as f:
        data = json.load(f)

    assert "123456" in data
    assert "home" in data["123456"]
    assert data["123456"]["home"][1] == 10.0
