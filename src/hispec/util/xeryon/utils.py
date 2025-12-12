# pylint: skip-file
"""
Utility functions for time measurement and formatted position string generation.

This module includes:
- `get_actual_time()`: Returns the current time in milliseconds.
- `get_dpos_epos_string(dpos, epos, unit)`: Returns a formatted string
    of dpos and epos values with units.
"""
import time


def get_actual_time():
    """
    :return: Returns the actual time in ms.
    """
    return int(round(time.time() * 1000))


def get_dpos_epos_string(DPOS, EPOS, Unit):
    """
    :return: A string containting the EPOS & DPOS value's and the current units.
    """
    return str("DPOS: " + str(DPOS) + " " + str(Unit) + " and EPOS: " + str(EPOS) + " " + str(Unit))
