"""Serve a Lightel DI-2000 as a libby peer, for a daemon on another machine.

The DI-2000 is a USB camera, so it can only be opened on the machine it is
plugged into. Run one camera peer per camera there:

    python camserver.py --device 0 --peer-id fiberswitchbluecam

and point the fiber switch daemon at it with
``camera.remote: hsfibers.fiberswitchbluecam``. The daemon then uses
RemoteDi2000, which has the methods of di2000.Di2000 that the daemon and
lightel's inspection pipeline call, as libby RPCs through the broker:

    cam.status          {connected, device_index}
    cam.connect         open the camera (on its --device)
    cam.disconnect      release it
    cam.frame           grab a frame and return its first chunk; {id, offset}
                        for the rest (see below)
    cam.getproperty     {id} -> {value}
    cam.setproperty     {id, value} -> {applied}
    cam.autofocus       trigger the vendor autofocus
    cam.autofocusstatus -> {status}

libby limits a message to 512 KB and a frame is about 900 KB, so a frame is
sent as a zlib-compressed .npy (lossless) in base64 chunks of FRAME_CHUNK
bytes: the first cam.frame call grabs the frame and returns its id, total
size and first chunk; later calls with that id and an offset return the rest.

This file needs only libby, numpy and lightel's di2000 module, not the hispec
package, so it can be copied to the camera machine on its own. Broker
credentials come from HISPEC_RABBITMQ_USER and HISPEC_RABBITMQ_PASSWORD,
as for the HISPEC daemons; keep them in an environment file, not on the
command line.
"""

from __future__ import annotations

import argparse
import base64
import io
import logging
import os
import threading
import time
import zlib
from typing import Any, Callable, Dict, Optional
from urllib.parse import quote

import numpy as np

# Raw bytes per frame chunk: base64 makes it 4/3 larger, which leaves room
# for the envelope inside libby's 512 KB message limit
FRAME_CHUNK = 256 * 1024

# The DI-2000 drops the odd control request (EPROTO) while its autofocus
# finishes; retry an autofocus status read this many times, this far apart
STATUS_RETRIES = 3
STATUS_RETRY_S = 0.3

# Mirrors hispec.daemon.broker_url, which this file cannot import
BROKER_HOST = "hispec.caltech.edu"

logger = logging.getLogger(__name__)


def broker_url() -> str:
    """The shared broker URL, with credentials from the environment."""
    user = os.environ.get("HISPEC_RABBITMQ_USER")
    password = os.environ.get("HISPEC_RABBITMQ_PASSWORD")
    host = os.environ.get("HISPEC_BROKER_HOST") or BROKER_HOST
    if not (user and password):
        return f"amqp://{host}"
    return f"amqp://{quote(user, safe='')}:{quote(password, safe='')}@{host}"


def encode_frame(frame) -> bytes:
    """A frame as a zlib-compressed .npy."""
    buffer = io.BytesIO()
    np.save(buffer, np.asarray(frame), allow_pickle=False)
    return zlib.compress(buffer.getvalue(), 1)


def decode_frame(data: bytes) -> np.ndarray:
    """The inverse of encode_frame."""
    return np.load(io.BytesIO(zlib.decompress(data)), allow_pickle=False)


class CameraService:
    """The cam.* RPC handlers around one camera driver (di2000.Di2000 or a stand-in).

    libby runs a peer's handlers one at a time, so the camera is never used
    by two requests at once.
    """

    def __init__(self, driver, open_camera: Callable[[], None]) -> None:
        """open_camera opens driver on its configured device."""
        self.driver = driver
        self.open_camera = open_camera
        self._frame_id = 0
        self._frame = b""

    def handlers(self) -> Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]]:
        """Service key -> handler, for LibbyDaemon.add_services."""
        return {
            "cam.status": self.status,
            "cam.connect": self.connect,
            "cam.disconnect": self.disconnect,
            "cam.frame": self.frame,
            "cam.getproperty": self.get_property,
            "cam.setproperty": self.set_property,
            "cam.autofocus": self.autofocus,
            "cam.autofocusstatus": self.autofocus_status,
        }

    def status(self, _payload):
        """Whether the camera is open, and which device."""
        return {"ok": True, "connected": bool(self.driver.is_connected()),
                "device_index": getattr(self.driver, "device_index", None)}

    def connect(self, _payload):
        """Open the camera if it is not open."""
        if not self.driver.is_connected():
            self.open_camera()
        return {"ok": True}

    def disconnect(self, _payload):
        """Release the camera."""
        self.driver.disconnect()
        return {"ok": True}

    def frame(self, payload):
        """Grab a frame (no id) or continue sending one (id and offset)."""
        if payload.get("id") is None:
            self._frame = encode_frame(self.driver.read_frame())
            self._frame_id += 1
            offset = 0
        else:
            if int(payload["id"]) != self._frame_id:
                raise RuntimeError(f"frame {payload['id']} is gone; the latest is "
                                   f"{self._frame_id}")
            offset = int(payload.get("offset", 0))
        chunk = self._frame[offset:offset + FRAME_CHUNK]
        return {"ok": True, "id": self._frame_id, "size": len(self._frame),
                "offset": offset, "data": base64.b64encode(chunk).decode("ascii")}

    def get_property(self, payload):
        """Read an OpenCV/UVC property."""
        return {"ok": True, "value": float(self.driver.get_property(int(payload["id"])))}

    def set_property(self, payload):
        """Set an OpenCV/UVC property; applied is False if the camera refused."""
        applied = bool(self.driver.set_property(int(payload["id"]), float(payload["value"])))
        return {"ok": True, "applied": applied}

    def autofocus(self, _payload):
        """Start the probe's onboard autofocus (Linux only)."""
        self.driver.trigger_autofocus()
        return {"ok": True}

    def autofocus_status(self, _payload):
        """Onboard autofocus progress, as di2000.AutofocusStatus values.

        Retries a failed read: the camera does not answer the odd one while
        it finishes focusing, and lightel's autofocus gives up on the first
        error.
        """
        for attempt in range(STATUS_RETRIES):
            try:
                return {"ok": True, "status": int(self.driver.get_autofocus_status())}
            except OSError as e:
                if attempt == STATUS_RETRIES - 1:
                    raise
                logger.info("autofocus status read failed (%s); retrying", e)
                time.sleep(STATUS_RETRY_S)
        raise AssertionError("unreachable")


class RemoteCameraError(RuntimeError):
    """The camera peer answered with an error, or did not answer."""


class RemoteDi2000:
    """A DI-2000 served by a camera peer on another machine.

    Has the di2000.Di2000 methods the fiber switch daemon and lightel's
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


def make_daemon_class():
    """The camera peer's LibbyDaemon subclass (imports libby only when run)."""
    from libby.daemon import LibbyDaemon  # pylint: disable=import-outside-toplevel

    class CameraPeer(LibbyDaemon):
        """Serves one DI-2000's cam.* RPCs."""

        transport = "rabbitmq"
        discovery_enabled = False

        def __init__(self) -> None:
            super().__init__()
            self.driver = None
            self.open_camera = None

        def config_rabbitmq_url(self) -> str:
            return self.rabbitmq_url or broker_url()

        def on_start(self) -> None:
            service = CameraService(self.driver, self.open_camera)
            self.add_services(service.handlers())
            try:
                self.open_camera()
            except ConnectionError as e:
                self.logger.error("%s; serving anyway, cam.connect retries", e)

        def on_stop(self) -> None:
            self.driver.disconnect()

    return CameraPeer


def main(argv=None) -> None:
    """Serve one DI-2000 until interrupted."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--peer-id", required=True,
                        help="libby peer id, e.g. fiberswitchbluecam")
    parser.add_argument("--group", default="hsfibers", help="libby group id")
    parser.add_argument("--device", type=int, default=0, help="camera index (/dev/videoN)")
    parser.add_argument("--backend", default="V4L2",
                        help="OpenCV backend name (V4L2, DSHOW, ...); 'any' for the default")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")

    import cv2  # pylint: disable=import-outside-toplevel
    from di2000 import Di2000  # pylint: disable=import-outside-toplevel

    backend = None if args.backend.lower() == "any" else getattr(
        cv2, f"CAP_{args.backend.upper()}")
    peer = make_daemon_class().from_config({"peer_id": args.peer_id, "group_id": args.group})
    peer.driver = Di2000(log=True)
    peer.open_camera = lambda: peer.driver.connect(args.device, backend=backend,
                                                   width=args.width, height=args.height)
    logger.info("Serving DI-2000 %d as %s.%s", args.device, args.group, args.peer_id)
    peer.serve()


if __name__ == "__main__":
    main()
