"""Reach a DI-2000 served by daemons/hsfibers/fiberswitchcamserver on another machine.

Used by daemons/hsfibers/fiberswitchcam; it lives beside the daemons rather
than in hispec.fiberswitch because it talks libby.

The DI-2000 is a USB camera, so it opens only on the machine it is plugged
into. When that is not the camera daemon's host, a fiberswitchcamserver runs
there and the camera daemon (daemons/hsfibers/fiberswitchcam) uses
RemoteDi2000 in place of di2000.Di2000, with the same methods, as libby RPCs
(cam.*) through the broker.

libby limits a message to 512 KB and a frame is about 900 KB, so the server
sends a frame as a zlib-compressed .npy in base64 chunks, and decode_frame
here is the inverse of its encode_frame.
"""

from __future__ import annotations

import base64
import io
import logging
import threading
import zlib
from typing import Any, Callable, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


def decode_frame(data: bytes) -> np.ndarray:
    """A frame from the camera server's zlib-compressed .npy encoding."""
    return np.load(io.BytesIO(zlib.decompress(data)), allow_pickle=False)


class RemoteCameraError(RuntimeError):
    """The camera peer answered with an error, or did not answer."""


class RemoteDi2000:
    """A DI-2000 served by a fiberswitchcamserver on another machine.

    Has the di2000.Di2000 methods the fiber switch camera daemon and lightel's
    inspection pipeline use. It makes its calls on its own libby connection,
    built by make_libby on first use: the daemon's own connection runs keyword
    handlers on one thread, so a handler waiting there for the camera's reply
    would never see it.
    """

    def __init__(self, peer: str, make_libby: Callable[[], Any], timeout_s: float = 10.0,
                 status_timeout_s: float = 2.0) -> None:
        if peer.count(".") != 1:
            raise ValueError(f"camera.remote must be <group>.<peer>, got {peer!r}")
        self.peer = peer.lower()
        self.timeout_s = timeout_s
        self.status_timeout_s = status_timeout_s
        self.device_index: Optional[int] = None
        self._make_libby = make_libby
        self._libby = None
        self._lock = threading.Lock()

    def is_connected(self) -> bool:
        """The camera peer answers and its camera is open."""
        try:
            status = self._call("cam.status", timeout=self.status_timeout_s)
        except RemoteCameraError:
            return False
        self.device_index = status.get("device_index")
        return bool(status.get("connected"))

    def connect(self, *_args, **_kwargs) -> None:
        """Ask the peer to open its camera; device arguments are the peer's."""
        try:
            self._call("cam.connect")
        except RemoteCameraError as e:
            raise ConnectionError(f"camera peer {self.peer}: {e}") from e

    def disconnect(self) -> None:
        """Ask the peer to release its camera; quiet if the peer is down."""
        try:
            self._call("cam.disconnect", timeout=self.status_timeout_s)
        except RemoteCameraError as e:
            logger.warning("camera peer %s: disconnect failed: %s", self.peer, e)

    def close(self) -> None:
        """Close this client's own libby connection."""
        with self._lock:
            libby, self._libby = self._libby, None
        if libby is not None:
            libby.stop()

    def read_frame(self) -> np.ndarray:
        """One frame from the camera."""
        reply = self._call("cam.frame")
        frame_id, size = reply["id"], int(reply["size"])
        data = bytearray(base64.b64decode(reply["data"]))
        while len(data) < size:
            reply = self._call("cam.frame", {"id": frame_id, "offset": len(data)})
            chunk = base64.b64decode(reply["data"])
            if not chunk:
                raise RemoteCameraError(f"frame {frame_id} ended at {len(data)} of {size} bytes")
            data += chunk
        return decode_frame(bytes(data))

    def get_property(self, property_id: int) -> float:
        """Read an OpenCV/UVC property."""
        return float(self._call("cam.getproperty", {"id": int(property_id)})["value"])

    def set_property(self, property_id: int, value: float) -> bool:
        """Set an OpenCV/UVC property; False if the camera refused it."""
        return bool(self._call("cam.setproperty",
                               {"id": int(property_id), "value": float(value)})["applied"])

    def trigger_autofocus(self) -> None:
        """Start the probe's onboard autofocus (Linux only, on the peer)."""
        self._call("cam.autofocus")

    def get_autofocus_status(self) -> int:
        """Onboard autofocus progress, as di2000.AutofocusStatus values."""
        return int(self._call("cam.autofocusstatus")["status"])

    def _connection(self):
        with self._lock:
            if self._libby is None:
                try:
                    self._libby = self._make_libby()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    raise RemoteCameraError(f"cannot reach the broker: {e}") from e
            return self._libby

    def _call(self, key: str, payload: Optional[dict] = None,
              timeout: Optional[float] = None) -> Dict[str, Any]:
        timeout = timeout or self.timeout_s
        # libby waits the whole ttl for the request's ACK, then half of it for
        # the reply, so double it to give the reply the full timeout
        envelope = self._connection().rpc(self.peer, key, payload or {},
                                          ttl_ms=int(timeout * 2000))
        status = envelope.get("status") if isinstance(envelope, dict) else None
        if status == "timeout":
            raise RemoteCameraError(f"{self.peer} did not answer {key}")
        if status == "too_large":
            raise RemoteCameraError(f"{key} request too large")
        resp = envelope.get("resp") if isinstance(envelope, dict) else None
        if not isinstance(resp, dict):
            raise RemoteCameraError(f"no reply from {self.peer} to {key}")
        if not resp.get("ok"):
            raise RemoteCameraError(resp.get("error", f"{key} failed"))
        return resp
