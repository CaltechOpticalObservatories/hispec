"""Typed access to the HISPEC tracking camera through the camera_interface module.

The module exposes instrument commands as ``instrument_cmd(name, argument_string)``,
so every caller would otherwise build the same argument strings by hand. This
puts that formatting in one place and gives the commands real signatures.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import camera_interface


class ReadMode(str, Enum):
    """Detector readout mode, as named by the ACF's mode_* parameters."""

    RX = "rx"
    RXR = "rxr"
    UTR_RR = "utr_rr"
    UTR_GR = "utr_gr"


@dataclass(frozen=True)
class Geometry:
    """Inclusive bounds of the region of interest the instrument is tracking.

    Only the roi commands move these. Selecting an ACF mode changes the readout
    geometry without touching them, so they are not a reading of frame size.
    """

    y0: int
    y1: int
    x0: int
    x1: int

    @property
    def height(self) -> int:
        """Return the number of rows the bounds cover."""
        return self.y1 - self.y0 + 1

    @property
    def width(self) -> int:
        """Return the number of columns the bounds cover."""
        return self.x1 - self.x0 + 1


class TrackingCamera:
    """The HISPEC tracking camera, with instrument commands as typed methods.

    Anything not defined here is forwarded to the underlying
    ``camera_interface.Camera``, so base commands such as ``expose`` and
    ``power`` are reached directly.
    """

    def __init__(self, camera: Any) -> None:
        self._camera = camera

    @classmethod
    def from_config(cls, config_path: str,
                    log_to_stderr: Optional[bool] = None) -> "TrackingCamera":
        """Build a camera from a camerad .cfg file."""
        return cls(camera_interface.Camera(config_path, log_to_stderr=log_to_stderr))

    def __getattr__(self, name: str) -> Any:
        # Only called for names this class does not define
        return getattr(self._camera, name)

    ### lifecycle

    def initialize(self) -> None:
        """Connect, load firmware, power on, and reset the H2RG.

        The H2RG main reset only fires on a 0 to 1 transition of Start, which
        the ACF has already set at load time, so h2rg_init has to run after
        power on for autofetch to stream at all.
        """
        self._camera.open()
        self._camera.load()
        self._camera.power("on")
        self._camera.instrument_cmd("h2rg_init")

    ### readout mode

    def set_readmode(self, mode: ReadMode) -> None:
        """Select the detector readout mode."""
        self._camera.instrument_cmd("exposure", ReadMode(mode).value)

    def readmode(self) -> Optional[ReadMode]:
        """Return the readout mode last selected, or None if none was."""
        current = self._camera.instrument_cmd("exposure").strip()
        return ReadMode(current) if current else None

    ### camera mode and geometry

    def set_camera_mode(self, name: str) -> None:
        """Select an ACF mode section by name."""
        self._camera.instrument_cmd("mode", name)

    def set_guiding_roi(self, y0: int, y1: int, x0: int, x1: int) -> None:
        """Set the windowed guiding region from inclusive detector bounds."""
        self._camera.instrument_cmd("roi", f"{y0} {y1} {x0} {x1}")

    def set_centred_roi(self, height: int, width: int) -> None:
        """Set a region of interest centred on the detector."""
        self._camera.instrument_cmd("roi", f"{height} {width}")

    def geometry(self) -> Geometry:
        """Return the bounds currently being read out."""
        y0, y1, x0, x1 = (int(value) for value in
                          self._camera.instrument_cmd("roi").split())
        return Geometry(y0=y0, y1=y1, x0=x0, x1=x1)

    def set_window(self, enabled: bool) -> None:
        """Put the detector into or out of window mode."""
        self._camera.instrument_cmd("window_mode", "1" if enabled else "0")

    ### acquisition

    def set_autofetch(self, enabled: bool) -> None:
        """Switch the continuous autofetch pipeline on or off."""
        self._camera.instrument_cmd("autofetch_mode", "1" if enabled else "0")

    def set_freerun(self, enabled: bool) -> None:
        """Arm or disarm the ACF freerun sequencer parameter."""
        self._camera.instrument_cmd("freerun", "1" if enabled else "0")

    ### diagnostics

    def set_debug(self, enabled: bool) -> None:
        """Enable or disable per-frame debug logging."""
        self._camera.instrument_cmd("debug", "true" if enabled else "false")

    def set_take_stats(self, enabled: bool) -> None:
        """Enable or disable per-frame timing statistics."""
        self._camera.instrument_cmd("take_stats", "true" if enabled else "false")
