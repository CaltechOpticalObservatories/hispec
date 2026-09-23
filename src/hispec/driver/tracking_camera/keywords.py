"""Tracking camera keywords, for the generic camera daemon to register.

Kept apart from `camera.py` so the driver itself stays usable without libby.
"""

from __future__ import annotations

from typing import Any, Optional

from libby import KeywordRegistry

from .camera import ReadMode, TrackingCamera


class Instrument:
    """The tracking camera's own keywords, over the generic camera ones."""

    camera_class = TrackingCamera

    def __init__(self, daemon: Any) -> None:
        self.daemon = daemon

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
        self.camera.set_readmode(ReadMode(value))

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
