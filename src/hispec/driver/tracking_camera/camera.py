"""Typed access to the HISPEC tracking camera's instrument commands.

`pycamerad.Camerad` covers everything on camerad's `Camera::Interface`, which
is the same for every instrument. This adds only what the HISPEC tracking
camera itself provides, so callers do not build `instrument_cmd` argument
strings by hand.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..pycamerad import Camerad

INSTRUMENT = "hispec_tracking_camera"


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


class TrackingCamera(Camerad):
    """The HISPEC tracking camera, adding its instrument commands."""

    ### lifecycle

    def initialize(self) -> None:
        """Connect, load firmware, power on, then reset the H2RG.

        The H2RG main reset only fires on a 0 to 1 transition of Start, which
        the ACF has already set at load time, so h2rg_init has to run after
        power on for autofetch to stream at all.
        """
        super().initialize()
        self.instrument_cmd("h2rg_init")

    ### readout mode

    def set_readmode(self, mode: ReadMode) -> None:
        """Select the detector readout mode."""
        self.instrument_cmd("exposure", ReadMode(mode).value)

    def readmode(self) -> ReadMode | None:
        """Return the readout mode last selected with this command, or None."""
        current = self.instrument_cmd("exposure").strip()
        return ReadMode(current) if current else None

    ### camera mode and geometry

    def set_camera_mode(self, name: str) -> None:
        """Select an ACF mode section by name."""
        self.instrument_cmd("mode", name)

    def set_guiding_roi(self, y0: int, y1: int, x0: int, x1: int) -> None:
        """Set the windowed guiding region from inclusive detector bounds."""
        self.instrument_cmd("roi", f"{y0} {y1} {x0} {x1}")

    def set_centred_roi(self, height: int, width: int) -> None:
        """Set a region of interest centred on the detector."""
        self.instrument_cmd("roi", f"{height} {width}")

    def geometry(self) -> Geometry:
        """Return the region of interest bounds the instrument is tracking."""
        y0, y1, x0, x1 = (int(value) for value in
                          self.instrument_cmd("roi").split())
        return Geometry(y0=y0, y1=y1, x0=x0, x1=x1)

    def set_window(self, enabled: bool) -> None:
        """Put the detector into or out of window mode."""
        self.instrument_cmd("window_mode", "1" if enabled else "0")

    ### acquisition

    def set_autofetch(self, enabled: bool) -> None:
        """Switch the continuous autofetch pipeline on or off."""
        self.instrument_cmd("autofetch_mode", "1" if enabled else "0")

    def set_freerun(self, enabled: bool) -> None:
        """Arm or disarm the ACF freerun sequencer parameter."""
        self.instrument_cmd("freerun", "1" if enabled else "0")

    ### diagnostics

    def set_debug(self, enabled: bool) -> None:
        """Enable or disable per-frame debug logging."""
        self.instrument_cmd("debug", "true" if enabled else "false")

    def set_take_stats(self, enabled: bool) -> None:
        """Enable or disable per-frame timing statistics."""
        self.instrument_cmd("take_stats", "true" if enabled else "false")
