"""Fiber-end inspection camera (MechanicalSwitchCamera).

Wraps a connected di2000.Di2000 and the lightel inspection pipeline
(lightel's inspection module), and archives every capture with its metadata.
The pipeline is passed in rather than imported so this module, and its
tests, need neither OpenCV nor a camera.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Mapping, Optional

from hispec.fiberswitch.jobs import JobAborted

# Camera settings by short name, as get_setting/set_setting and a connection
# policy's `camera` field name them
SETTING_NAMES = ("exposure", "gain", "brightness", "focus", "autoexposure", "autofocus")


def summarize(result) -> Dict[str, Any]:
    """The JSON-safe parts of an inspection.InspectionResult."""
    region = result.region
    illumination = result.illumination
    autoexpose = result.autoexpose
    return {
        "kind": "inspection",
        "passed": bool(result.passed),
        "dirt": float(result.defect_area_fraction),
        # OpenCV hands back numpy scalars, which json cannot encode
        "defects": [{"cx": float(d.cx), "cy": float(d.cy), "area": float(d.area),
                     "bbox": [int(v) for v in d.bbox]}
                    for d in result.defects],
        "region": _region(region),
        "illumination": None if illumination is None else illumination.mode,
        "focus": {
            "score": float(result.autofocus.score),
            "converged": bool(result.autofocus.converged),
            "method": result.autofocus.method,
        },
        "exposure": (None if autoexpose is None else {
            "value": (None if autoexpose.exposure_value is None
                      else float(autoexpose.exposure_value)),
            "converged": bool(autoexpose.converged),
            "mean": float(autoexpose.quality.mean),
        }),
    }


class InspectionCamera:
    """Refocus, capture and inspect with a DI-2000, archiving each image."""

    def __init__(self, camera, archive, pipeline,  # pylint: disable=too-many-arguments
                 properties: Mapping[str, int],
                 max_defect_area_fraction: float = 0.01) -> None:
        self.camera = camera
        self.archive = archive
        self.pipeline = pipeline
        self.properties = dict(properties)
        self.max_defect_area_fraction = max_defect_area_fraction
        self.last_focus: Optional[Dict[str, Any]] = None
        self.last_record: Optional[Dict[str, Any]] = None

    def refocus(self, cancel: Optional[threading.Event] = None) -> Dict[str, Any]:
        """Bring the fiber end into focus (vendor autofocus, else a sweep)."""
        _check(cancel, "refocus")
        result = self.pipeline.autofocus(self.camera)
        self.last_focus = {"score": float(result.score), "converged": bool(result.converged),
                           "method": result.method, "value": result.focus_value}
        return self.last_focus

    def capture(self, tag: str, cancel: Optional[threading.Event] = None) -> Dict[str, Any]:
        """Grab one frame as-is and archive it with its focus score."""
        _check(cancel, "capture")
        frame = self.camera.read_frame()
        gray = self.pipeline.to_gray(frame)
        region = self.pipeline.locate_fiber_end(gray)
        metadata = {
            "kind": "capture",
            "focus": {"score": float(self.pipeline.focus_score(gray, region))},
            "region": _region(region),
            "settings": self.settings(),
        }
        return self._archive(tag, frame, metadata)

    def inspect(self, tag: str, cancel: Optional[threading.Event] = None,
                max_defect_area_fraction: Optional[float] = None) -> Dict[str, Any]:
        """Focus, expose, look for dirt, and archive the frame and its annotation.

        max_defect_area_fraction sets the pass threshold; the camera's own
        default when None.
        """
        _check(cancel, "inspect")
        max_dirt = (self.max_defect_area_fraction if max_defect_area_fraction is None
                    else max_defect_area_fraction)
        result = self.pipeline.inspect(self.camera, max_defect_area_fraction=max_dirt)
        metadata = summarize(result)
        metadata["max_dirt"] = max_dirt
        metadata["settings"] = self.settings()
        annotated = self.pipeline.draw_result(result.frame, result)
        return self._archive(tag, result.frame, metadata, annotated)

    def get_setting(self, name: str) -> float:
        """Read one camera property by its short name."""
        return float(self.camera.get_property(self._property(name)))

    def set_setting(self, name: str, value: float) -> None:
        """Write one camera property; raise if the camera rejects it."""
        if not self.camera.set_property(self._property(name), float(value)):
            raise RuntimeError(f"camera rejected {name}={value}")

    def settings(self) -> Dict[str, Optional[float]]:
        """Every known camera property, None where the camera does not report it."""
        values: Dict[str, Optional[float]] = {}
        for name in self.properties:
            try:
                values[name] = self.get_setting(name)
            except Exception:  # pylint: disable=broad-exception-caught
                values[name] = None
        return values

    def _property(self, name: str) -> int:
        try:
            return self.properties[name]
        except KeyError as e:
            raise ValueError(f"unknown camera setting {name!r}; "
                             f"known: {sorted(self.properties)}") from e

    def _archive(self, tag: str, frame, metadata: Dict[str, Any],
                 annotated=None) -> Dict[str, Any]:
        path = self.archive.save(tag, frame, metadata, annotated=annotated)
        record = {"tag": tag, "image": str(path), **metadata}
        self.last_record = record
        return record


def _region(region) -> Optional[Dict[str, float]]:
    if region is None:
        return None
    return {"cx": float(region.cx), "cy": float(region.cy), "r": float(region.r)}


def _check(cancel: Optional[threading.Event], what: str) -> None:
    if cancel is not None and cancel.is_set():
        raise JobAborted(f"{what} aborted before it started")
