"""Unit tests for the tracking camera add-on, with no camera_interface build needed."""

import sys
import types
import unittest


class FakeCamera:
    """Records calls and replays canned replies, standing in for the extension."""

    def __init__(self, replies=None):
        self.calls = []
        self.replies = replies or {}

    def instrument_cmd(self, command, args=""):
        self.calls.append((command, args))
        return self.replies.get(command, "")

    def open(self):
        self.calls.append(("open", ""))

    def load(self, args=""):
        self.calls.append(("load", args))

    def power(self, args=""):
        self.calls.append(("power", args))
        return self.replies.get("power", "ON")

    def expose(self, args=""):
        self.calls.append(("expose", args))
        return ""


# pycamerad imports camera_interface at module scope, and it is a compiled
# extension that need not be present to test argument formatting
sys.modules.setdefault("camera_interface", types.ModuleType("camera_interface"))

from hispec.driver.tracking_camera import (  # noqa: E402
    Geometry, ReadMode, TrackingCamera,
)


class TestTrackingCamera(unittest.TestCase):
    """Check that instrument commands are formatted and replies parsed."""

    def test_initialize_adds_the_h2rg_reset_after_power_on(self):
        camera = FakeCamera()
        TrackingCamera(camera).initialize()
        self.assertEqual(
            camera.calls,
            [("open", ""), ("load", ""), ("power", "on"), ("h2rg_init", "")],
        )

    def test_guiding_roi_is_sent_as_vstart_vstop_hstart_hstop(self):
        camera = FakeCamera()
        TrackingCamera(camera).set_guiding_roi(51, 60, 20, 29)
        self.assertEqual(camera.calls, [("roi", "51 60 20 29")])

    def test_centred_roi_is_sent_as_height_width(self):
        camera = FakeCamera()
        TrackingCamera(camera).set_centred_roi(100, 200)
        self.assertEqual(camera.calls, [("roi", "100 200")])

    def test_geometry_parses_the_roi_query(self):
        camera = FakeCamera({"roi": "51 60 20 29"})
        geometry = TrackingCamera(camera).geometry()
        self.assertEqual(geometry, Geometry(y0=51, y1=60, x0=20, x1=29))
        self.assertEqual((geometry.height, geometry.width), (10, 10))

    def test_readmode_round_trips(self):
        camera = FakeCamera({"exposure": "utr_gr"})
        facade = TrackingCamera(camera)
        facade.set_readmode(ReadMode.UTR_GR)
        self.assertEqual(camera.calls, [("exposure", "utr_gr")])
        self.assertEqual(facade.readmode(), ReadMode.UTR_GR)

    def test_readmode_is_none_when_nothing_selected(self):
        self.assertIsNone(TrackingCamera(FakeCamera({"exposure": ""})).readmode())

    def test_invalid_readmode_is_rejected_before_it_reaches_the_camera(self):
        camera = FakeCamera()
        with self.assertRaises(ValueError):
            TrackingCamera(camera).set_readmode("sideways")
        self.assertEqual(camera.calls, [])

    def test_booleans_become_the_arguments_each_command_expects(self):
        camera = FakeCamera()
        facade = TrackingCamera(camera)
        facade.set_window(True)
        facade.set_autofetch(False)
        facade.set_debug(True)
        self.assertEqual(
            camera.calls,
            [("window_mode", "1"), ("autofetch_mode", "0"), ("debug", "true")],
        )

    def test_generic_commands_come_from_the_base_class(self):
        camera = FakeCamera()
        facade = TrackingCamera(camera)
        facade.expose(4)
        self.assertTrue(facade.power())
        self.assertEqual(camera.calls, [("expose", "4"), ("power", "")])


if __name__ == "__main__":
    unittest.main()
