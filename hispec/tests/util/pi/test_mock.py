import json
from unittest.mock import MagicMock, patch
from hispec.util import PIControllerBase


@patch('hispec.util.pi.base_controller.GCSDevice')
def test_connect_tcpip_daisy_chain(mock_gcs_device_cls):
    mock_device = MagicMock()
    mock_device.OpenTCPIPDaisyChain.return_value = [
        "PI Device 1", "PI Device 2", "<device 3 not connected>"
    ]
    mock_device.dcid = 1
    mock_gcs_device_cls.return_value = mock_device

    controller = PIControllerBase(quiet=True)
    controller.connect_tcpip_daisy_chain("192.168.29.100", 10003)

    mock_device.OpenTCPIPDaisyChain.assert_called_once_with("192.168.29.100", 10003)
    mock_device.ConnectDaisyChainDevice.assert_called_once_with(1, 1)

    assert controller.connected
    assert controller.daisy_chains[("192.168.29.100", 10003)] == [
        (1, "PI Device 1"), (2, "PI Device 2")
    ]
    assert controller.current_connection == ("192.168.29.100", 10003, 1)


@patch('hispec.util.pi.base_controller.GCSDevice')
def test_select_device_on_chain(mock_gcs_device_cls):
    mock_device = MagicMock()
    mock_device.dcid = 1
    mock_gcs_device_cls.return_value = mock_device

    controller = PIControllerBase(quiet=True)
    controller.connected = True
    controller.device = mock_device
    controller.daisy_chains[("192.168.29.100", 10003)] = [
        (1, "PI Device 1"), (2, "PI Device 2")
    ]

    controller.select_device_on_chain("192.168.29.100", 10003, 2)

    mock_device.ConnectDaisyChainDevice.assert_called_once_with(2, 1)
    assert controller.current_connection == ("192.168.29.100", 10003, 2)


@patch('hispec.util.pi.base_controller.GCSDevice')
def test_list_devices_on_chain(mock_gcs_device_cls):
    controller = PIControllerBase(quiet=True)
    ip_port = ("192.168.29.100", 10003)
    controller.daisy_chains[ip_port] = [(1, "PI Device 1"), (2, "PI Device 2")]

    devices = controller.list_devices_on_chain(*ip_port)

    assert devices == [(1, "PI Device 1"), (2, "PI Device 2")]


@patch('hispec.util.pi.base_controller.GCSDevice')
def test_connect_disconnect(mock_gcs_device_cls):
    mock_device = MagicMock()
    mock_gcs_device_cls.return_value = mock_device

    controller = PIControllerBase(quiet=True)
    controller.connect_tcp("127.0.0.1", 50000)

    mock_device.ConnectTCPIP.assert_called_once_with("127.0.0.1", 50000)
    assert controller.connected

    controller.disconnect()
    mock_device.CloseConnection.assert_called_once()
    assert not controller.connected


@patch('hispec.util.pi.base_controller.GCSDevice')
def test_get_serial_number(mock_gcs_device_cls):
    controller = PIControllerBase(quiet=True)
    controller.connected = True
    controller.device.qIDN.return_value = "PI,Model,123456,1.0.0"

    serial = controller.get_serial_number()
    assert serial == "123456"


@patch('hispec.util.pi.base_controller.GCSDevice')
def test_get_position(mock_gcs_device_cls):
    mock_device = MagicMock()
    mock_gcs_device_cls.return_value = mock_device

    controller = PIControllerBase(quiet=True)
    controller.connected = True
    controller.device.axes = ['1', '2']
    controller.device.qPOS.return_value = {'1': 42.0}

    pos = controller.get_position(0)
    assert pos == 42.0
    controller.device.qPOS.assert_called_once_with('1')


def test_set_and_go_to_named_position(tmp_path):
    controller = PIControllerBase(quiet=True)
    controller.named_position_file = tmp_path / "positions.json"
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
