import unittest
import os
import tempfile
from unittest.mock import patch, mock_open
from hispec.util import XeryonController
from hispec.util.xeryon.stage import Stage
from hispec.util.xeryon.units import Units


class MockAxis:
    def __init__(self):
        self.commands = []
        self.settings = {}
        self.was_valid_DPOS = False

    def send_command(self, cmd):
        self.commands.append(cmd)

    def set_setting(self, tag, value, *_, **__):
        self.settings[tag] = value

    def reset(self):
        self.commands.append("RSET=0")

    def send_settings(self):
        self.commands.append("send_settings")

    def get_letter(self):
        return "X"


class MockComm:
    def __init__(self):
        self.sent_commands = []

    def send_command(self, cmd):
        self.sent_commands.append(cmd)

    def close_communication(self):
        self.sent_commands.append("CLOSE")

    def set_COM_port(self, port):
        self.port = port

    def start(self, *_):
        return self


class MockStage:
    isLineair = True
    encoderResolutionCommand = "XLS1=312"
    encoderResolution = 312.5
    speedMultiplier = 1000
    amplitudeMultiplier = 1456.0
    phaseMultiplier = 182


class TestXeryonController(unittest.TestCase):

    def setUp(self):
        self.controller = XeryonController()
        self.controller.comm = MockComm()
        self.axis = MockAxis()
        self.controller.axis_list = [self.axis]
        self.controller.axis_letter_list = ["X"]

    def test_add_axis(self):
        result = self.controller.add_axis(MockStage(), "Y")
        self.assertEqual(len(self.controller.axis_list), 2)
        self.assertEqual(result.axis_letter, "Y")

    def test_is_single_axis(self):
        self.assertTrue(self.controller.is_single_axis_system())

    def test_stop_sends_commands(self):
        self.controller.stop()
        self.assertIn("ZERO=0", self.axis.commands)
        self.assertIn("STOP=0", self.axis.commands)
        self.assertIn("CLOSE", self.controller.comm.sent_commands)

    def test_set_master_setting(self):
        self.controller.set_master_setting("VEL", "100")
        self.assertEqual(self.controller.master_settings["VEL"], "100")
        self.assertIn("VEL=100", self.controller.comm.sent_commands)

    def test_send_master_settings(self):
        self.controller.master_settings = {"VEL": "100", "ACC": "10"}
        self.controller.send_master_settings()
        self.assertIn("VEL=100", self.controller.comm.sent_commands)
        self.assertIn("ACC=10", self.controller.comm.sent_commands)

    @patch("builtins.open", new_callable=mock_open, read_data="X:VEL=100\nACC=10\n")
    def test_read_settings(self, mock_file):
        self.controller.read_settings()
        self.assertEqual(self.axis.settings["VEL"], "100")

    def test_read_settings_applies_axis_values_correctly(self):
        settings_content = """
        X:LLIM=10
        X:HLIM=200
        X:SSPD=5000
        X:POLI=7
        """
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
            tmp.write(settings_content)
            tmp_path = tmp.name

        try:
            with patch("hsfei.xeryon.controller.SETTINGS_FILENAME", new=tmp_path):
                controller = XeryonController()
                axis = controller.add_axis(Stage.XLS_312, "X")
                controller.read_settings()

                expected_llim = str(
                    axis.convert_units_to_encoder(10, Units.mm))
                self.assertEqual(axis.get_setting("LLIM"), expected_llim)

                expected_hlim = str(
                    axis.convert_units_to_encoder(200, Units.mm))
                self.assertEqual(axis.get_setting("HLIM"), expected_hlim)

                expected_sspd = str(int(5000 * axis.stage.speedMultiplier))
                self.assertEqual(axis.get_setting("SSPD"), expected_sspd)

                self.assertEqual(axis.get_setting("POLI"), "7")
        finally:
            os.remove(tmp_path)

    @patch("serial.tools.list_ports.comports")
    def test_find_COM_port(self, mock_comports):
        class Port:
            def __init__(self, device, hwid):
                self.device = device
                self.hwid = hwid
        mock_comports.return_value = [Port("COM3", "USB VID:PID=04D8")]
        self.controller.find_COM_port()
        self.assertEqual(self.controller.comm.port, "COM3")


if __name__ == "__main__":
    unittest.main()
