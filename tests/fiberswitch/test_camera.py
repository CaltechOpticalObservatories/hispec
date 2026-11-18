"""Tests for the inspection camera wrapper and the image archive, with fakes."""

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np
import pytest

from hispec.fiberswitch.archive import ImageArchive, safe_tag
from hispec.fiberswitch.camera import InspectionCamera

FIXED = datetime(2026, 11, 16, 12, 0, 0, 123456, tzinfo=timezone.utc)


def fake_writer(path, image):
    """Write the 'image' as text so the test can check it."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(image))
    return True


def archive(tmp_path):
    """An archive with a fixed clock and a text writer."""
    return ImageArchive(tmp_path, write_image=fake_writer, now=lambda: FIXED)


class FakeCam:
    """A Di2000 with settable properties and a fixed frame."""

    def __init__(self):
        self.props = {1: 10.0}

    def read_frame(self):
        """Return a stand-in frame."""
        return "frame"

    def get_property(self, prop):
        """Read a property."""
        return self.props[prop]

    def set_property(self, prop, value):
        """Write a property; prop 2 is rejected, as a camera may do."""
        if prop == 2:
            return False
        self.props[prop] = value
        return True


def fake_pipeline(dirt=0.02):
    """The parts of lightel's inspection module the wrapper calls."""
    region = SimpleNamespace(cx=5.0, cy=6.0, r=3.0)
    result = SimpleNamespace(
        frame="frame", region=region, passed=dirt <= 0.01, defect_area_fraction=dirt,
        # numpy scalars, as OpenCV returns them
        defects=[SimpleNamespace(cx=np.float64(1.0), cy=2.0, area=np.float32(4.0),
                                 bbox=tuple(np.int32(v) for v in (0, 1, 2, 2)))],
        illumination=SimpleNamespace(mode="front"),
        autofocus=SimpleNamespace(score=12.5, converged=True, method="vendor_trigger",
                                  focus_value=None),
        autoexpose=SimpleNamespace(exposure_value=-5.0, converged=True,
                                   quality=SimpleNamespace(mean=140.0)))
    return SimpleNamespace(
        inspect=lambda camera, max_defect_area_fraction: result,
        autofocus=lambda camera: result.autofocus,
        draw_result=lambda frame, res: "annotated",
        to_gray=lambda frame: frame,
        locate_fiber_end=lambda gray: region,
        focus_score=lambda gray, region: 7.0)


def test_safe_tag():
    """Tags are reduced to file-name-safe characters."""
    assert safe_tag("group 1/../x") == "group-1-..-x"
    assert safe_tag("") == "image"


def test_archive_writes_png_and_sidecar(tmp_path):
    """save writes the image, the annotated copy and a JSON sidecar under the date."""
    path = archive(tmp_path).save("group1", "img", {"dirt": 0.5}, annotated="ann")
    assert path.parent == tmp_path / "2026-11-16"
    assert path.name == "group1_20261116T120000_123456Z.png"
    sidecar = json.loads(path.with_suffix(".json").read_text())
    assert sidecar["dirt"] == 0.5 and sidecar["tag"] == "group1"
    assert sidecar["annotated"].endswith("_annotated.png")


def test_inspect_archives_and_summarizes(tmp_path):
    """inspect archives the frame with its result and keeps it as last_record."""
    camera = InspectionCamera(FakeCam(), archive(tmp_path), fake_pipeline(dirt=0.02),
                              {"exposure": 1})
    record = camera.inspect("group1")
    assert record["kind"] == "inspection" and record["passed"] is False
    assert record["dirt"] == 0.02 and record["defects"][0]["bbox"] == [0, 1, 2, 2]
    assert record["focus"]["method"] == "vendor_trigger"
    assert record["settings"] == {"exposure": 10.0}
    sidecar = json.loads((tmp_path / "2026-11-16" /
                          "group1_20261116T120000_123456Z.json").read_text())
    assert sidecar["dirt"] == 0.02
    assert camera.last_record is record
    json.dumps(record)  # lastresult publishes it as JSON


def test_capture_and_refocus(tmp_path):
    """capture archives the raw frame with a focus score; refocus records the result."""
    camera = InspectionCamera(FakeCam(), archive(tmp_path), fake_pipeline(), {})
    assert camera.capture("look")["focus"]["score"] == 7.0
    assert camera.refocus()["converged"] is True


def test_settings(tmp_path):
    """Settings are read and written by name; rejected writes and unknown names raise."""
    camera = InspectionCamera(FakeCam(), archive(tmp_path), fake_pipeline(),
                              {"exposure": 1, "gain": 2, "missing": 3})
    camera.set_setting("exposure", 4)
    assert camera.get_setting("exposure") == 4.0
    assert camera.settings()["missing"] is None
    with pytest.raises(RuntimeError, match="rejected"):
        camera.set_setting("gain", 1)
    with pytest.raises(ValueError, match="unknown camera setting"):
        camera.get_setting("zoom")
