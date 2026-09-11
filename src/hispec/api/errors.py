"""Exceptions raised by the HISPEC subsystem API layer.

A failing driver call is reported however that driver reports it — a False
return, its own exception, its own error register. These cover the failures
that only exist once driver calls are composed into a procedure.
"""


class ApiError(Exception):
    """Base class for errors raised by hispec.api."""


class ConfigError(ApiError):
    """A subsystem's config directory or device config file is missing or bad."""


class DeviceError(ApiError):
    """A driver refused a command, or a device is not usable."""


class ProcedureTimeout(ApiError):
    """A procedure gave up waiting on a physical condition."""
