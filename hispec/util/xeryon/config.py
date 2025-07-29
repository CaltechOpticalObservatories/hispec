# pylint: skip-file
# Configuration constants for the Xeryon controller library

SETTINGS_FILENAME = "util/config/xeryon_default_settings.txt"
LIBRARY_VERSION = "v1.64"

# DEBUG MODE
# This variable is set to True if you are in debug mode.
# It ignores some checks, e.g., when sending DPOS without checking EPOS range.
DEBUG_MODE = False

# OUTPUT TO CONSOLE
# If set to True, debug output will be printed to the console.
OUTPUT_TO_CONSOLE = True

# DISABLE WAITING
# If set to True, the library won't wait until positions are reached.
DISABLE_WAITING = False  # Important: set to False in production!

# AUTO SEND SETTINGS
# Automatically send settings from the config file to the controller on startup.
AUTO_SEND_SETTINGS = True

# AUTO SEND ENBL
# Automatically send ENBL=1 when specific errors occur to bypass protection.
AUTO_SEND_ENBL = False

# Commands whose values are not stored in the library
NOT_SETTING_COMMANDS = [
    "DPOS", "EPOS", "HOME", "ZERO", "RSET", "INDX", "STEP", "MOVE", "STOP", "CONT",
    "SAVE", "STAT", "TIME", "SRNO", "SOFT", "XLA3", "XLA1", "XRT1", "XRT3", "XLS1",
    "XLS3", "SFRQ", "SYNC"
]

# Default values for motion calculations
DEFAULT_POLI_VALUE = 200
AMPLITUDE_MULTIPLIER = 1456.0
PHASE_MULTIPLIER = 182
