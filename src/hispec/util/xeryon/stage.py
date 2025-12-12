# pylint: skip-file
from enum import Enum
import math
from .config import AMPLITUDE_MULTIPLIER, PHASE_MULTIPLIER


class Stage(Enum):
    XLS_312 = (True,  # isLineair (True/False)
               # Encoder Resolution Command (XLS =|XRTU=|XRTA=|XLA =)
               "XLS1=312",
               312.5,  # Encoder Resolution always in nanometer/microrad
               1000)  # Speed multiplier

    XLS_1250 = (True,
                "XLS1=1251",
                1250,
                1000)
    XLS_1250_OLD = (True,
                    "XLS1=1250",
                    1250,
                    1000)

    XLS_1250_OLD_2 = (True,
                      "XLS1=1250",
                      312.5,
                      1000)

    XLS_78 = (True,
              "XLS1=78",
              78.125,
              1000)

    XLS_5 = (True,
             "XLS1=5",
             5,
             1000)

    XLS_1 = (True,
             "XLS1=1",
             1,
             1000)
    XLS_312_3N = (True,  # isLineair (True/False)
                  # Encoder Resolution Command (XLS =|XRTU=|XRTA=|XLA =)
                  "XLS3=312",
                  312.5,  # Encoder Resolution always in nanometer/microrad
                  1000)  # Speed multiplier

    XLS_1250_3N = (True,
                   "XLS3=1251",
                   1250,
                   1000)

    XLS_1250_3N_OLD = (True,
                       "XLS3=1250",
                       312.5,
                       1000)

    XLS_78_3N = (True,
                 "XLS3=78",
                 78.125,
                 1000)

    XLS_5_3N = (True,
                "XLS3=5",
                5,
                1000)

    XLS_1_3N = (True,
                "XLS3=1",
                1,
                1000)

    XLA_312 = (True,
               "XLA1=312",
               312.5,
               1000)

    XLA_1250 = (True,
                "XLA1=1250",
                1250,
                1000)

    XLA_78 = (True,
              "XLA1=78",
              78.125,
              1000)

    XLA_OL = (True,
              "XLA1=0",
              1,
              1000)

    XLA_OL_3N = (True,
                 "XLA3=0",
                 1,
                 1000)

    XLA_312_3N = (True,
                  "XLA3=312",
                  312.5,
                  1000)

    XLA_1250_3N = (True,
                   "XLA3=1250",
                   1250,
                   1000)

    XLA_78_3N = (True,
                 "XLA3=78",
                 78.125,
                 1000)

    XLA_312_OLD = (True,
                   "XLA=312",
                   312.5,
                   1000)

    XLA_1250_OLD = (True,
                    "XLA=1250",
                    1250,
                    1000)

    XLA_78_OLD = (True,
                  "XLA=78",
                  78.125,
                  1000)

    XRTA = (False,
            "XRTA=109",  # ?
            (2 * math.pi * 1e6) / 57600,
            100)

    # TODO: CHECK RES
    # XRTU's 1N VERSION
    XRTU_40_3 = (False,
                 "XRT1=2",
                 (2 * math.pi * 1e6) / 86400,
                 100)

    XRTU_40_19 = (False,
                  "XRT1=18",
                  (2 * math.pi * 1e6) / 86400,
                  100)
    XRTU_40_49 = (False,
                  "XRT1=47",
                  (2 * math.pi * 1e6) / 86400,
                  100)

    XRTU_40_73 = (False,
                  "XRT1=73",
                  (2 * math.pi * 1e6) / 86400,  # CORRECT ???
                  100)

    XRTU_30_3 = (False,
                 "XRT1=3",
                 (2 * math.pi * 1e6) / 1843200,
                 100)

    XRTU_30_19 = (False,
                  "XRT1=19",
                  (2 * math.pi * 1e6) / 360000,
                  100)

    XRTU_30_49 = (False,
                  "XRT1=49",
                  (2 * math.pi * 1e6) / 144000,
                  100)

    XRTU_30_109 = (False,
                   "XRT1=109",
                   (2 * math.pi * 1e6) / 57600,
                   100)

    XRTU_60_3 = (False,
                 "XRT3=3",
                 (2 * math.pi * 1e6) / 2073600,
                 100)
    XRTU_60_19 = (False,
                  "XRT3=19",
                  (2 * math.pi * 1e6) / 324000,
                  100)
    XRTU_60_49 = (False,
                  "XRT3=49",
                  (2 * math.pi * 1e6) / 129600,
                  100)
    XRTU_60_109 = (False,
                   "XRT3=109",
                   (2 * math.pi * 1e6) / 64800,
                   100)

    # For backwards compatibility

    XRTU_30_109_OLD = (False,
                       "XRTU=109",
                       (2 * math.pi * 1e6) / 57600,
                       100)
    XRTU_40_73_OLD = (False,
                      "XRTU=73",
                      (2 * math.pi * 1e6) / 86400,
                      100)
    XRTU_40_3_OLD = (False,
                     "XRTU=3",  # ?
                     (2 * math.pi * 1e6) / 1800000,
                     100)

    def __init__(self, isLineair, encoderResolutionCommand, encoderResolution,
                 speedMultiplier):

        self.isLineair = isLineair
        self.encoderResolutionCommand = encoderResolutionCommand
        # ALTIJD IN nm / nanorad !!! ==> Verschillend met windows interface.
        self.encoderResolution = encoderResolution
        self.speedMultiplier = speedMultiplier  # used.
        self.amplitudeMultiplier = AMPLITUDE_MULTIPLIER
        self.phaseMultiplier = PHASE_MULTIPLIER

    def get_stage(self, stage_command):
        """
        Get stagetype by specifying "stage_command".
        'stage_command' is how the stage is specified in the config file.
        e.g.: XLS=312 or XRTU=40, ....
        :param stage_command: String containing "XLS=.." or "XRTU=..." or ...
        :return: Stagetype, or none if invalid stage command.
        """
        for stage in Stage:
            if stage_command in str(stage.encoderResolutionCommand).replace(" ", ""):
                return stage
        return None
