"""
Unit tests for the XeryonController class in the hispec.util.xeryon module.
"""
import unittest
import os
import tempfile
from unittest.mock import patch, mock_open
from dataclasses import dataclass
# pylint: disable=no-name-in-module,import-error
from xeryon.xeryon_controller import XeryonController
from xeryon.stage import Stage
from xeryon.units import Units


def get_letter():
    """
    Return the letter associated with this axis.
    """
    return "X"


class MockAxis:
    """
    Mock class to simulate an axis in the XeryonController.
    """
    def __init__(self):
        """
        Initialize the mock axis with default values.
        """
        self.commands = []
        self.settings = {}

        # pylint: disable=invalid-name
        self.was_valid_DPOS = False

    def send_command(self, cmd):
        """
        Simulate sending a command to the axis.
        """
        self.commands.append(cmd)

    def set_setting(self, tag, value, *_, **__):
        """
        Simulate setting a configuration value for the axis.
        """
        self.settings[tag] = value

    def reset(self):
        """
        Simulate resetting the axis.
        """
        self.commands.append("RSET=0")

    def send_settings(self):
        """
        Simulate sending the current settings of the axis.
        """
        self.commands.append("send_settings")


class MockComm:
    """
    Mock class to simulate communication with the Xeryon controller.
    """
    def __init__(self):
        """
        Initialize the mock communication with an empty command list.
        """
        self.port = None
        self.sent_commands = []

    def send_command(self, cmd):
        """
        Simulate sending a command through the communication interface.
        """
        self.sent_commands.append(cmd)

    def close_communication(self):
        """
        Simulate closing the communication interface.
        """
        self.sent_commands.append("CLOSE")

    # pylint: disable=invalid-name
    def set_COM_port(self, port):
        """
        Simulate setting the communication port.
        """
        self.port = port

    def start(self, *_):
        """
        Simulate starting the communication interface.
        """
        return self

@dataclass()
class MockStage:
    """
    Mock class to simulate a stage in the XeryonController.
    """
    # pylint: disable=invalid-name
    isLineair = True
    # pylint: disable=invalid-name
    encoderResolutionCommand = "XLS1=312"
    # pylint: disable=invalid-name
    encoderResolution = 312.5
    # pylint: disable=invalid-name
    speedMultiplier = 1000
    # pylint: disable=invalid-name
    amplitudeMultiplier = 1456.0
    # pylint: disable=invalid-name
    phaseMultiplier = 182


class TestXeryonController(unittest.TestCase):
    """
    Unit tests for the XeryonController class.
    """

    def setUp(self):
        """
        Set up the test environment by initializing a XeryonController instance
        """
        self.controller = XeryonController()
        self.controller.comm = MockComm()
        self.axis = MockAxis()
        self.controller.axis_list = [self.axis]
        self.controller.axis_letter_list = ["X"]

    def test_add_axis(self):
        """
        Test adding a new axis to the controller.
        """
        result = self.controller.add_axis(MockStage(), "Y")
        self.assertEqual(len(self.controller.axis_list), 2)
        self.assertEqual(result.axis_letter, "Y")

    def test_is_single_axis(self):
        """
        Test if the controller recognizes a single-axis system.
        """
        self.assertTrue(self.controller.is_single_axis_system())

    def test_stop_sends_commands(self):
        """
        Test that the stop method sends the correct commands to the axis and communication
        interface.
        """
        self.controller.stop()
        self.assertIn("ZERO=0", self.axis.commands)
        self.assertIn("STOP=0", self.axis.commands)
        self.assertIn("CLOSE", self.controller.comm.sent_commands)

    def test_set_master_setting(self):
        """
        Test setting a master setting in the controller and ensuring it is sent correctly.
        """
        self.controller.set_master_setting("VEL", "100")
        self.assertEqual(self.controller.master_settings["VEL"], "100")
        self.assertIn("VEL=100", self.controller.comm.sent_commands)

    def test_send_master_settings(self):
        """
        Test sending master settings to the communication interface.
        """
        self.controller.master_settings = {"VEL": "100", "ACC": "10"}
        self.controller.send_master_settings()
        self.assertIn("VEL=100", self.controller.comm.sent_commands)
        self.assertIn("ACC=10", self.controller.comm.sent_commands)

    @patch("builtins.open", new_callable=mock_open, read_data="X:VEL=100\nACC=10\n")
    # pylint: disable=unused-argument
    def test_read_settings(self, mock_file):
        """
        Test reading settings from a file and applying them to the axis.
        """
        self.controller.read_settings()
        self.assertEqual(self.axis.settings["VEL"], "100")

    def test_read_settings_applies_axis_values_correctly(self):
        """
        Test that reading settings applies axis values correctly.
        """
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
            controller = XeryonController()
            
            axis = controller.add_axis(Stage.XLS_312, "X")
            controller.read_settings(tmp_path)

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
    # pylint: disable=invalid-name
    def test_find_COM_port(self, mock_comports):
        """
        Test finding the COM port for the Xeryon controller.
        """
        @dataclass
        class Port:
            """
            Mock class to simulate a serial port.
            """
            def __init__(self, device, hwid):
                """
                Initialize the mock port with device and hardware ID.
                """
                self.device = device
                self.hwid = hwid

        mock_comports.return_value = [Port("COM3", "USB VID:PID=04D8")]
        self.controller.find_com_port()
        self.assertEqual(self.controller.comm.port, "COM3")


if __name__ == "__main__":
    unittest.main()
