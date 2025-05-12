import unittest
from unittest.mock import patch, mock_open
from ..controller import XeryonController

class MockAxis:
    def __init__(self):
        self.commands = []
        self.settings = {}
        self.was_valid_DPOS = False

    def sendCommand(self, cmd):
        self.commands.append(cmd)

    def setSetting(self, tag, value, *_, **__):
        self.settings[tag] = value

    def reset(self):
        self.commands.append("RSET=0")

    def sendSettings(self):
        self.commands.append("sendSettings")

    def getLetter(self):
        return "X"

class MockComm:
    def __init__(self):
        self.sent_commands = []

    def sendCommand(self, cmd):
        self.sent_commands.append(cmd)

    def closeCommunication(self):
        self.sent_commands.append("CLOSE")

    def setCOMPort(self, port):
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
        result = self.controller.addAxis(MockStage(), "Y")
        self.assertEqual(len(self.controller.axis_list), 2)
        self.assertEqual(result.axis_letter, "Y")

    def test_is_single_axis(self):
        self.assertTrue(self.controller.isSingleAxisSystem())

    def test_stop_sends_commands(self):
        self.controller.stop()
        self.assertIn("ZERO=0", self.axis.commands)
        self.assertIn("STOP=0", self.axis.commands)
        self.assertIn("CLOSE", self.controller.comm.sent_commands)

    def test_set_master_setting(self):
        self.controller.setMasterSetting("VEL", "100")
        self.assertEqual(self.controller.master_settings["VEL"], "100")
        self.assertIn("VEL=100", self.controller.comm.sent_commands)

    def test_send_master_settings(self):
        self.controller.master_settings = {"VEL": "100", "ACC": "10"}
        self.controller.sendMasterSettings()
        self.assertIn("VEL=100", self.controller.comm.sent_commands)
        self.assertIn("ACC=10", self.controller.comm.sent_commands)

    @patch("builtins.open", new_callable=mock_open, read_data="X:VEL=100\nACC=10\n")
    def test_read_settings(self, mock_file):
        self.controller.readSettings()
        self.assertEqual(self.axis.settings["VEL"], "100")

    @patch("serial.tools.list_ports.comports")
    def test_find_COM_port(self, mock_comports):
        class Port:
            def __init__(self, device, hwid):
                self.device = device
                self.hwid = hwid
        mock_comports.return_value = [Port("COM3", "USB VID:PID=04D8")]
        self.controller.findCOMPort()
        self.assertEqual(self.controller.comm.port, "COM3")

if __name__ == "__main__":
    unittest.main()
