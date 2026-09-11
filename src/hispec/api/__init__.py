"""Subsystem-level API for HISPEC, one subpackage per subsystem.

This layer sits on top of the device drivers in ``hispec.driver``. The drivers
move axes and read sensors; the functions here are the ones that *call* the
drivers — the multi-axis, multi-device, wait-for-a-condition procedures that
otherwise live in a one-off script and get copied with their bugs.

Only the FEI is covered so far; other subsystems get their own subpackage
alongside ``hispec.api.fei``.
"""

from .base import DeviceSpec, SubsystemAPI
from .errors import ApiError, ConfigError, DeviceError, ProcedureTimeout
from .fei import FEI

__all__ = [
    "SubsystemAPI",
    "DeviceSpec",
    "FEI",
    "ApiError",
    "ConfigError",
    "DeviceError",
    "ProcedureTimeout",
]
