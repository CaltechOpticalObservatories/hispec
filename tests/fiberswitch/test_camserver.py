"""The camera peer and RemoteDi2000 over libby (ZMQ on loopback), with a fake camera."""

import socket

import numpy as np
import pytest
from libby import Libby

from hispec.fiberswitch.camserver import (FRAME_CHUNK, CameraService, RemoteCameraError,
                                          RemoteDi2000, decode_frame, encode_frame,
                                          make_daemon_class)

PEER = "hsfibers.testcam"


class FakeCamera:
    """Stands in for di2000.Di2000."""

    def __init__(self):
        self.connected = True
        self.device_index = 3
        self.props = {10: 2.5}
        # Noise does not compress, so the frame takes several chunks
        self.frame = np.random.default_rng(0).integers(0, 256, (480, 640, 3), dtype=np.uint8)
        self.triggered = 0
        self.reads = 0

    def is_connected(self):
        return self.connected

    def disconnect(self):
        self.connected = False

    def read_frame(self):
        if not self.connected:
            raise RuntimeError("camera not connected")
        self.reads += 1
        return self.frame

    def get_property(self, prop):
        return self.props.get(prop, 0.0)

    def set_property(self, prop, value):
        if prop == 99:
            return False
        self.props[prop] = value
        return True

    def trigger_autofocus(self):
        self.triggered += 1

    def get_autofocus_status(self):
        return 3


def _port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(name="served")
def fixture_served():
    camera = FakeCamera()
    peer_addr = f"tcp://127.0.0.1:{_port()}"
    client_addr = f"tcp://127.0.0.1:{_port()}"
    cls = type("ZmqPeer", (make_daemon_class(),), {"transport": "zmq"})
    peer = cls.from_config({"peer_id": "testcam", "group_id": "hsfibers", "bind": peer_addr,
                            "address_book": {}, "discovery_enabled": False})
    peer.driver = camera
    peer.open_camera = lambda: setattr(camera, "connected", True)
    peer.start()
    remote = RemoteDi2000(PEER, lambda: Libby.zmq(self_id="testclient", bind=client_addr,
                                                  address_book={PEER: peer_addr}),
                          timeout_s=3.0)
    yield camera, remote
    remote.close()
    peer.stop()


def test_frame_round_trips_losslessly_in_chunks(served):
    camera, remote = served
    assert len(encode_frame(camera.frame)) > 2 * FRAME_CHUNK
    frame = remote.read_frame()
    assert frame.dtype == np.uint8 and np.array_equal(frame, camera.frame)
    assert camera.reads == 1


def test_properties(served):
    camera, remote = served
    assert remote.get_property(10) == 2.5
    assert remote.set_property(11, 7) is True and camera.props[11] == 7.0
    assert remote.set_property(99, 1) is False


def test_connect_disconnect_and_status(served):
    camera, remote = served
    assert remote.is_connected() and remote.device_index == 3
    remote.disconnect()
    assert not camera.connected and not remote.is_connected()
    remote.connect(0, backend=None)
    assert camera.connected and remote.is_connected()


def test_autofocus(served):
    camera, remote = served
    remote.trigger_autofocus()
    assert camera.triggered == 1 and remote.get_autofocus_status() == 3


def test_peer_errors_are_raised(served):
    camera, remote = served
    camera.connected = False
    with pytest.raises(RemoteCameraError, match="camera not connected"):
        remote.read_frame()


def test_absent_peer():
    addr = f"tcp://127.0.0.1:{_port()}"
    remote = RemoteDi2000("hsfibers.nobody",
                          lambda: Libby.zmq(self_id="lonely", bind=addr, address_book={}),
                          timeout_s=0.3, status_timeout_s=0.3)
    try:
        assert not remote.is_connected()
        with pytest.raises(ConnectionError):
            remote.connect()
        remote.disconnect()  # quiet when the peer is down
    finally:
        remote.close()


def test_stale_frame_id_is_refused():
    camera = FakeCamera()
    service = CameraService(camera, lambda: None)
    first = service.frame({})
    service.frame({})
    with pytest.raises(RuntimeError, match="gone"):
        service.frame({"id": first["id"], "offset": FRAME_CHUNK})


def test_autofocus_status_retries_transient_errors(monkeypatch):
    monkeypatch.setattr("hispec.fiberswitch.camserver.STATUS_RETRY_S", 0.0)
    camera = FakeCamera()
    replies = [OSError(71, "Protocol error"), 2]

    def status():
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    camera.get_autofocus_status = status
    assert CameraService(camera, lambda: None).autofocus_status({})["status"] == 2

    camera.get_autofocus_status = lambda: (_ for _ in ()).throw(OSError(71, "Protocol error"))
    with pytest.raises(OSError):
        CameraService(camera, lambda: None).autofocus_status({})


def test_encode_decode():
    frame = np.arange(60, dtype=np.uint8).reshape(4, 5, 3)
    assert np.array_equal(decode_frame(encode_frame(frame)), frame)


def test_peer_name_must_be_group_dot_peer():
    with pytest.raises(ValueError):
        RemoteDi2000("131.215.200.211:8762", lambda: None)
