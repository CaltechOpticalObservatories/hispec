"""Driver adapters for the PDU daemon, one per PDU family.

The daemon drives an adapter from here, never a vendor driver directly, so
adding a PDU means adding an adapter and a pdu_models/ capability file
rather than editing the daemon script. Each adapter's docstring lists the
quirks of the driver it wraps.

Readers raise instead of returning a sentinel, and writers raise when the
driver refuses, because each backs a keyword whose failure the daemon
reports to its caller.
"""

# A PDU has many small, independent things to read and write, so these
# classes run past the default cap.
# pylint: disable=too-many-public-methods

import pathlib
import sys
from typing import Dict, Optional, Type

import hispec.driver.pdu  # pylint: disable=E0611

# dli_dc3.py imports its sibling as a top-level module ("from emat08_10
# import trailing_int"), which only resolves with the driver's own src/ on
# sys.path, and pdu/src/__init__.py imports dli_dc3. Without this every
# import from that package fails, the Eaton's included. Drop it once
# COO-Utilities/pdu makes that import relative.
_DRIVER_SRC = str(pathlib.Path(next(iter(hispec.driver.pdu.__path__))) / "src")
if _DRIVER_SRC not in sys.path:
    sys.path.insert(0, _DRIVER_SRC)

# pylint: disable=wrong-import-position
from hispec.driver.pdu.src.dli_dc3 import Dlidc3  # noqa: E402  pylint: disable=E0611
from hispec.driver.pdu.src.emat08_10 import EatonEMAT  # noqa: E402  pylint: disable=E0611

# Calls an adapter may leave out, and the capability each serves. An adapter
# supports a capability when it defines every call listed for it. A
# capability missing here can never be registered: add its calls and its
# daemon keyword together.
OPTIONAL_CALLS = {
    "get_outlet_current": "outlet_amps",
    "get_outlet_power": "outlet_draw",
    "get_outlet_autorestart": "outlet_pos",
    "set_outlet_autorestart": "outlet_pos",
    "get_outlet_energy": "outlet_wh",
    "reset_outlet_statistics": "outlet_wh",
    "manufacturer": "manufacturer",
    "serial_number": "serial",
}

FEATURES = frozenset(OPTIONAL_CALLS.values())


class UnsupportedFeature(RuntimeError):
    """Raised when a call reaches an adapter that does not implement it."""


class PduDriver:
    """The interface the PDU daemon drives, implemented once per PDU family.

    The methods here are mandatory. Anything in OPTIONAL_CALLS is left out
    unless the model's driver can do it.
    """

    #: The vendor driver this adapter wraps; each subclass sets its own.
    dev = None

    def supports(self, feature: str) -> bool:
        """True when this adapter defines every call the capability needs."""
        calls = [call for call, served in OPTIONAL_CALLS.items() if served == feature]
        return bool(calls) and all(hasattr(type(self), call) for call in calls)

    def __getattr__(self, name):
        """Name the adapter when an optional call it lacks is reached.

        Capability filtering should keep this unreachable; it is a backstop.
        """
        if name in OPTIONAL_CALLS:
            raise UnsupportedFeature(f"{type(self).__name__} does not implement {name}()")
        raise AttributeError(f"{type(self).__name__} has no attribute '{name}'")

    @staticmethod
    def _confirm(ok, action: str) -> None:
        """Raise when a driver call reports that it refused to act."""
        if not ok:
            raise RuntimeError(f"driver refused to {action}")

    def connect(self, host: str, port: int, username: str, password: str) -> bool:
        """Open a session to the PDU. True when the session is up."""
        raise NotImplementedError

    def disconnect(self) -> None:
        """Close the session, tolerating one that was never opened."""
        raise NotImplementedError

    def is_connected(self) -> bool:
        """True while a session to the PDU is open."""
        raise NotImplementedError

    def initialize(self) -> bool:
        """Populate the driver's cached device properties after connect()."""
        raise NotImplementedError

    def outlet_count(self) -> Optional[int]:
        """Outlet count as the driver knows it, or None when it cannot say."""
        raise NotImplementedError

    def model(self) -> str:
        """PDU model, as reported by the hardware."""
        raise NotImplementedError

    def firmware(self) -> str:
        """PDU firmware revision, as reported by the hardware."""
        raise NotImplementedError

    def get_outlet_state(self, n: int) -> bool:
        """True when outlet ``n`` is powered."""
        raise NotImplementedError

    def set_outlet_state(self, n: int, on: bool) -> None:
        """Switch outlet ``n`` on or off."""
        raise NotImplementedError

    def get_outlet_name(self, n: int) -> str:
        """Name configured on the PDU for outlet ``n``."""
        raise NotImplementedError

    def set_outlet_name(self, n: int, name: str) -> None:
        """Rename outlet ``n`` on the PDU."""
        raise NotImplementedError

    def get_outlet_switchable(self, n: int) -> bool:
        """True when outlet ``n`` may be switched, False when it is locked."""
        raise NotImplementedError

    def set_outlet_switchable(self, n: int, switchable: bool) -> None:
        """Unlock outlet ``n`` for switching, or lock it where it is."""
        raise NotImplementedError


class EatonEmatDriver(PduDriver):
    """Adapter for the Eaton EMAT-08/10 PDU over Telnet.

    Quirks of pdu/src/emat08_10.py that shape this adapter:
      * set calls swallow their own exceptions and return a bool, so every
        one is checked for a falsy return.
      * get_atomic_value() takes a device item ("model") or an outlet item
        with the 1-based number appended ("current3"), None on failure.
      * initialize() must follow connect(), and gates per-outlet reads.

    The EMAT's strip-wide readings and hardware revision have no driver
    accessor, so they are absent from OPTIONAL_CALLS and only warn.
    """

    def __init__(self, log: bool = True):
        self.dev = EatonEMAT(log=log)

    def connect(self, host, port, username, password) -> bool:
        return bool(self.dev.connect(host, port, username=username, password=password))

    def disconnect(self) -> None:
        self.dev.disconnect()

    def is_connected(self) -> bool:
        return bool(self.dev.is_connected())

    def initialize(self) -> bool:
        return bool(self.dev.initialize())

    def outlet_count(self) -> Optional[int]:
        return self.dev.outlet_count or None

    def model(self) -> str:
        return self._device("model")

    def firmware(self) -> str:
        return self._device("version")

    def manufacturer(self) -> str:
        """PDU manufacturer, as reported by the hardware."""
        return self._device("manufacturer")

    def serial_number(self) -> str:
        """PDU serial number, as reported by the hardware."""
        return self._device("serial_number")

    def get_outlet_state(self, n: int) -> bool:
        return bool(self._outlet(n, "outlet_status"))

    def set_outlet_state(self, n: int, on: bool) -> None:
        self._confirm(self.dev.outlet_on(n) if on else self.dev.outlet_off(n),
                      f"switch outlet {n} {'on' if on else 'off'}")

    def get_outlet_name(self, n: int) -> str:
        return str(self._outlet(n, "name"))

    def set_outlet_name(self, n: int, name: str) -> None:
        self._confirm(self.dev.set_outlet_name(n, name), f"rename outlet {n}")

    def get_outlet_switchable(self, n: int) -> bool:
        return bool(self._outlet(n, "switchable"))

    def set_outlet_switchable(self, n: int, switchable: bool) -> None:
        # The driver has no setter for Switchable, so build one from its GET
        # template rather than repeating the OID here.
        path = self.dev.get_outlet_commands["switchable"][0].format(n=n)
        cmd = f"set {path} {1 if switchable else 0}"
        self._confirm(self.dev._send_command(cmd),  # pylint: disable=protected-access
                      f"set outlet {n} switchable state")

    def get_outlet_current(self, n: int) -> float:
        """Outlet ``n`` instantaneous current draw, in amps."""
        return float(self._outlet(n, "current"))

    def get_outlet_power(self, n: int) -> float:
        """Outlet ``n`` instantaneous active power draw, in watts."""
        return float(self._outlet(n, "active_power"))

    def get_outlet_autorestart(self, n: int) -> int:
        """Outlet ``n`` power-up behavior: 0 off, 1 on, 2 last state."""
        return int(self._outlet(n, "auto_restart"))

    def set_outlet_autorestart(self, n: int, value: int) -> None:
        """Set outlet ``n`` power-up behavior; the daemon validates the range."""
        self._confirm(self.dev.set_autostart(n, int(value)),
                      f"set outlet {n} auto-restart")

    def get_outlet_energy(self, n: int) -> int:
        """Outlet ``n`` energy since its last reset, in watt-hours."""
        return int(self._outlet(n, "energy"))

    def reset_outlet_statistics(self, n: int) -> None:
        """Zero outlet ``n`` energy statistics on the PDU."""
        self._confirm(self.dev.reset_statistics(n), f"reset outlet {n} statistics")

    def _device(self, item: str) -> str:
        """Read a device item, which the driver names without an outlet."""
        value = self.dev.get_atomic_value(item)
        if value is None:
            raise RuntimeError(f"failed to read '{item}' from PDU")
        return str(value)

    def _outlet(self, n: int, item: str):
        """Read an outlet item, which the driver names item + outlet number."""
        value = self.dev.get_atomic_value(f"{item}{n}")
        if value is None:
            raise RuntimeError(f"failed to read outlet {n} {item}")
        return value


class DliDc3Driver(PduDriver):
    """Adapter for the Digital Loggers DC3 power controller over SSH.

    Quirks of pdu/src/dli_dc3.py that shape this adapter:
      * connect(), disconnect(), initialize() and set_outlet_name() always
        return None, so each is confirmed by re-reading the hardware.
      * disconnect() dereferences its SSH client unconditionally.
      * initialize() appends to outlet_names and outlet_onoff, doubling them
        on a second call unless they are cleared first.
      * get_atomic_value() answers for outlet items only; identity lives on
        attributes initialize() fills in.
      * outlet_count is fixed at 8, not read from the hardware.
      * "locked" is the inverse of the Eaton's "switchable".

    The DC3 implements no optional call: no metering, no manufacturer, no
    serial number.
    """

    def __init__(self, log: bool = True):
        self.dev = Dlidc3(log=log)

    def connect(self, host, port, username, password) -> bool:
        # The driver never passes port to paramiko, so hardware.tcp_port has
        # no effect here and the session uses paramiko's default.
        self.dev.connect(host, port, username=username, password=password)
        return self.is_connected()

    def disconnect(self) -> None:
        if self.dev.ssh is not None:
            self.dev.disconnect()

    def is_connected(self) -> bool:
        return bool(self.dev.is_connected())

    def initialize(self) -> bool:
        self.dev.outlet_names = []
        self.dev.outlet_onoff = []
        self.dev.initialize()
        return bool(self.dev.initialized)

    def outlet_count(self) -> Optional[int]:
        return self.dev.outlet_count or None

    def model(self) -> str:
        return self._identity("model")

    def firmware(self) -> str:
        return self._identity("version")

    def get_outlet_state(self, n: int) -> bool:
        state = self.dev.outlet_status(n)
        if state is None:
            raise RuntimeError(f"failed to read outlet {n} state")
        return bool(state)

    def set_outlet_state(self, n: int, on: bool) -> None:
        self._confirm(self.dev.outlet_on(n) if on else self.dev.outlet_off(n),
                      f"switch outlet {n} {'on' if on else 'off'}")

    def get_outlet_name(self, n: int) -> str:
        name = self.dev.get_outlet_name(n)
        if name is None:
            raise RuntimeError(f"failed to read outlet {n} name")
        # The DC3 quotes string values both ways, so they are framing.
        return str(name).strip('"')

    def set_outlet_name(self, n: int, name: str) -> None:
        # The setter reports nothing either way, so read the name back.
        self.dev.set_outlet_name(n, name)
        self._confirm(self.get_outlet_name(n) == name, f"rename outlet {n}")

    def get_outlet_switchable(self, n: int) -> bool:
        locked = self.dev.lock_status(n)
        if locked is None:
            raise RuntimeError(f"failed to read outlet {n} lock state")
        return not locked

    def set_outlet_switchable(self, n: int, switchable: bool) -> None:
        self._confirm(self.dev.unlock_outlet(n) if switchable else self.dev.lock_outlet(n),
                      f"{'unlock' if switchable else 'lock'} outlet {n}")

    def _identity(self, attr: str) -> str:
        """Read a device property that initialize() cached on the driver."""
        value = getattr(self.dev, attr, "")
        if not value:
            raise RuntimeError(f"PDU reported no '{attr}'; is the daemon initialized?")
        return str(value)


# Driver key -> adapter, keyed by the `driver` field of a pdu_models file.
DRIVERS: Dict[str, Type[PduDriver]] = {
    "eaton_emat": EatonEmatDriver,
    "dli_dc3": DliDc3Driver,
}


def known_drivers():
    """List the driver keys a model file may name, sorted."""
    return sorted(DRIVERS)


def create(driver: str, log: bool = True) -> PduDriver:
    """Build the adapter a model file's `driver` field names.

    Raises a ValueError listing the known drivers on a typo, so a bad
    capability file fails at startup.
    """
    adapter = DRIVERS.get(str(driver))
    if adapter is None:
        raise ValueError(f"unknown PDU driver '{driver}'; known drivers: {known_drivers()}")
    return adapter(log=log)
