import pytest
from pi_controller.controller import PIControllerBase

def test_connection_fail():
    with pytest.raises(Exception):
        controller = PIControllerBase()
        controller.connect_tcp(ip="10.0.0.1", port=50000)

# def test_tcp_success():
#     controller = PIControllerBase()
#     try:
#         controller.connect_tcp("192.168.1.100", 10003)
#         assert controller.is_connected()
#     finally:
#         controller.disconnect()
