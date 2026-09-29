"""Tracking camera keywords, for the generic camera daemon to register.

Kept apart from `camera.py` so the driver itself stays usable without libby.
"""

from __future__ import annotations

import threading
from typing import Any, Optional, Tuple

from libby import KeywordRegistry

from .camera import ReadMode, TrackingCamera

ROI = "roi"
GUIDING = "guiding"
SUBFRAME_MODES = (ROI, GUIDING)

# The centred-ROI command caps width at half the detector: the horizontal
# argument is a per-tap pixel count, not a detector-wide one
MAX_ROI_HEIGHT = 2048
MAX_ROI_WIDTH = 1024


class Instrument:
    """The tracking camera's own keywords, over the generic camera ones."""

    camera_class = TrackingCamera

    def __init__(self, daemon: Any) -> None:
        self.daemon = daemon
        self._subframemode = ROI
        self._readmode = ReadMode.RX
        self._size: Optional[Tuple[int, int]] = None
        self._bounds: Optional[Tuple[int, int, int, int]] = None
        # subframemode and readmode both re-derive the ACF mode, so the whole
        # sequence is applied under one lock rather than interleaved
        self._apply_lock = threading.Lock()

    @property
    def camera(self) -> TrackingCamera:
        """Return the daemon's camera, or explain that there is not one."""
        if self.daemon.camera is None:
            raise RuntimeError("no camera; check camera.config_file and the installed module")
        return self.daemon.camera

    def register_keywords(self, registry: KeywordRegistry) -> None:
        """Add the tracking camera's keywords to the given registry."""
        registry.string("readmode",
                        getter=self._get_readmode,
                        setter=self._set_readmode,
                        validator=self._check_readmode,
                        description="Detector readout mode: "
                                    f"{', '.join(m.value for m in ReadMode)}.")
        registry.string("subframemode",
                        getter=lambda: self._subframemode,
                        setter=self._set_subframemode,
                        validator=self._check_subframemode,
                        description=f"Subframe mode: {' or '.join(SUBFRAME_MODES)}.")
        for name in ("y0", "y1", "x0", "x1"):
            registry.int(name,
                         getter=self._bound_getter(name),
                         setter=self._bound_setter(name),
                         units="pixel",
                         description=f"Guiding ROI {name}, inclusive; "
                                     f"writable in {GUIDING} mode.")
        registry.int("subframeheight",
                     getter=lambda: self._geometry().height,
                     setter=self._size_setter("height"),
                     units="pixel",
                     description=f"Centred ROI height; writable in {ROI} mode.")
        registry.int("subframewidth",
                     getter=lambda: self._geometry().width,
                     setter=self._size_setter("width"),
                     units="pixel",
                     description=f"Centred ROI width; writable in {ROI} mode.")
        registry.string("geometrystatus",
                        getter=self._geometry_status,
                        description="How the geometry in force was derived.")
        registry.bool("debug",
                      setter=self._set_debug,
                      description="Per-frame debug logging.")
        registry.bool("takestats",
                      setter=self._set_take_stats,
                      description="Per-frame timing statistics.")

    def _get_readmode(self) -> str:
        mode = self.camera.readmode()
        return mode.value if mode else ""

    def _set_readmode(self, value: str) -> None:
        self._readmode = ReadMode(value)
        self._apply()

    ### subframe mode and geometry

    def _apply(self) -> None:
        """Re-derive the ACF mode and apply the whole sequence.

        The camera mode goes first: it reloads the mode's parameters from the
        ACF, which would otherwise undo the readout mode and the ROI.
        """
        camera = self.camera
        with self._apply_lock:
            if self._subframemode == GUIDING:
                camera.set_camera_mode("GUIDING")
                camera.set_readmode(self._readmode)
                camera.set_window(True)
                if self._bounds is not None:
                    camera.set_guiding_roi(*self._bounds)
            else:
                camera.set_camera_mode(self._readmode.value.upper())
                camera.set_window(False)
                if self._size is not None:
                    camera.set_centred_roi(*self._size)

    def _check_subframemode(self, value: Any) -> Optional[str]:
        if str(value) not in SUBFRAME_MODES:
            return f"subframemode must be one of {', '.join(SUBFRAME_MODES)}"
        return None

    def _set_subframemode(self, value: str) -> None:
        self._subframemode = str(value)
        self._apply()

    def _geometry(self):
        return self.camera.geometry()

    def _geometry_status(self) -> str:
        if self._subframemode == GUIDING:
            return "windowed bounds as written" if self._bounds else "windowed, bounds not set"
        return "centred on the detector from the size" if self._size else "mode default"

    def _bound_getter(self, name: str):
        return lambda: getattr(self._geometry(), name)

    def _bound_setter(self, name: str):
        def setter(value: int) -> None:
            if self._subframemode != GUIDING:
                raise RuntimeError(
                    f"{name} is writable in {GUIDING} mode only; "
                    f"in {self._subframemode} mode set subframeheight and subframewidth")
            geometry = self._geometry()
            bounds = {axis: getattr(geometry, axis) for axis in ("y0", "y1", "x0", "x1")}
            bounds[name] = int(value)
            self._bounds = (bounds["y0"], bounds["y1"], bounds["x0"], bounds["x1"])
            self._apply()
        return setter

    def _size_setter(self, name: str):
        def setter(value: int) -> None:
            if self._subframemode != ROI:
                raise RuntimeError(
                    f"subframe{name} is writable in {ROI} mode only; "
                    f"in {self._subframemode} mode set y0, y1, x0 and x1")
            # The unwritten dimension comes from the last request, not from
            # geometry(), whose width is detector-wide and so out of range here
            height, width = self._size or (MAX_ROI_HEIGHT, MAX_ROI_WIDTH)
            size = {"height": height, "width": width}
            size[name] = int(value)
            self._size = (size["height"], size["width"])
            self._apply()
        return setter

    ### diagnostics

    def _set_debug(self, value: bool) -> None:
        self.camera.set_debug(value)

    def _set_take_stats(self, value: bool) -> None:
        self.camera.set_take_stats(value)

    def _check_readmode(self, value: Any) -> Optional[str]:
        try:
            ReadMode(value)
        except ValueError:
            return f"readmode must be one of {', '.join(m.value for m in ReadMode)}"
        return None
