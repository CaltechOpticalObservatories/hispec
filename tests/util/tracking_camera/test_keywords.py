"""Unit tests for the tracking camera keywords, with no libby or camera build needed."""

import sys
import types
import unittest
from dataclasses import dataclass

# keywords.py imports these only for registration types and the compiled
# extension, neither of which the tests exercise
sys.modules.setdefault("camera_interface", types.ModuleType("camera_interface"))
if "libby" not in sys.modules:
    sys.modules["libby"] = types.SimpleNamespace(KeywordRegistry=object)

from hispec.driver.tracking_camera import ReadMode  # noqa: E402
from hispec.driver.tracking_camera.keywords import Instrument  # noqa: E402

SECTIONS = {"roi": "ROI", "guiding": "GUIDING", "fullframe": "FULLFRAME"}


@dataclass
class Output:
    """One frame output's counters, as pycamerad reports them."""

    frames_written: int


class FakeCamera:
    """Record the driver calls the keywords make."""

    def __init__(self, outputs=()):
        self.calls = []
        self.outputs = list(outputs)

    def __getattr__(self, name):
        def record(*args):
            self.calls.append((name, *args))
        return record

    def output_status(self):
        """Return the canned output counters."""
        return self.outputs


class FakeDaemon:
    """Supply the config and camera the instrument object reads."""

    def __init__(self, sections, camera=None):
        self.sections = sections
        self.camera = camera

    def get_config(self, key, default=None):
        """Return the subframe section map for its key."""
        return self.sections if key == "camera.subframe_sections" else default


class FakeRegistry:
    """Keep registered keywords so the tests can read and write them."""

    def __init__(self):
        self.registered = {}

    def _record(self, name, **kwargs):
        self.registered[name] = kwargs

    bool = int = float = string = trigger = _record

    def read(self, name):
        """Call a keyword's getter."""
        return self.registered[name]["getter"]()

    def write(self, name, value):
        """Validate and then set a keyword, as libby does."""
        validator = self.registered[name].get("validator")
        error = validator(value) if validator else None
        if error:
            raise ValueError(error)
        self.registered[name]["setter"](value)


def instrument(sections=None, outputs=()):
    """Return a camera and a registry with the instrument's keywords on it."""
    camera = FakeCamera(outputs)
    registry = FakeRegistry()
    Instrument(FakeDaemon(SECTIONS if sections is None else sections, camera)) \
        .register_keywords(registry)
    return camera, registry


class TestSubframeSections(unittest.TestCase):
    """Check that subframe modes select the ACF sections config names."""

    def test_each_mode_selects_its_configured_section_then_the_readmode(self):
        camera, registry = instrument()
        registry.write("subframemode", "fullframe")
        self.assertEqual(camera.calls, [("set_camera_mode", "FULLFRAME"),
                                        ("set_readmode", ReadMode.RX)])

    def test_guiding_applies_the_written_bounds_after_the_section(self):
        camera, registry = instrument()
        registry.write("subframemode", "guiding")
        registry.write("guidingroi", "51 60 20 29")
        self.assertEqual(camera.calls[-3][:2], ("set_camera_mode", "GUIDING"))
        self.assertEqual(camera.calls[-1], ("set_guiding_roi", 51, 60, 20, 29))

    def test_a_mode_missing_from_config_is_rejected(self):
        _, registry = instrument({"roi": "ROI"})
        with self.assertRaises(ValueError):
            registry.write("subframemode", "guiding")

    def test_the_first_configured_mode_is_the_startup_mode(self):
        _, registry = instrument({"guiding": "GUIDING", "roi": "ROI"})
        self.assertEqual(registry.read("subframemode"), "guiding")

    def test_missing_or_unknown_sections_stop_startup(self):
        for sections in ({}, {"roi": "ROI", "sideways": "X"}):
            with self.subTest(sections=sections), self.assertRaises(RuntimeError):
                Instrument(FakeDaemon(sections or None))


class TestAcquisitionKeywords(unittest.TestCase):
    """Check autofetch, freerun and the frame counter."""

    def test_autofetch_and_freerun_drive_the_camera_and_read_back(self):
        camera, registry = instrument()
        registry.write("autofetch", True)
        registry.write("freerun", True)
        self.assertEqual(camera.calls, [("set_autofetch", True), ("set_freerun", True)])
        self.assertTrue(registry.read("autofetch"))
        self.assertTrue(registry.read("freerun"))

    def test_frameswritten_is_the_busiest_output_not_the_sum(self):
        _, registry = instrument(outputs=[Output(5), Output(7)])
        self.assertEqual(registry.read("frameswritten"), 7)

    def test_frameswritten_is_zero_with_no_outputs(self):
        _, registry = instrument()
        self.assertEqual(registry.read("frameswritten"), 0)


if __name__ == "__main__":
    unittest.main()
