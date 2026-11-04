"""Queries common to every FIB PCB board profile."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import ClassVar, Final

import paho.mqtt.client as mqtt
from hardware_device_base import HardwareDeviceBase

from .transport import (DEFAULT_PORT, EventCallback, FibError, FibPcbClient, PendingQuery,
                        Reply)

DEFAULT_TIMEOUT_S: Final = 5.0
NO_SOURCE: Final = "no source"


@dataclass(frozen=True)
class LastCommand:
    """Most recent effect-capable command the board accepted."""

    name: str
    source: str
    time_ms: int


@dataclass(frozen=True)
class BoardStatus:  # pylint: disable=too-many-instance-attributes
    """Cached board state reported by the ``status`` query."""

    firmware: str
    boots: int
    board: str
    board_ok: bool
    mems_switches: int
    relay_errors: int
    ambient_c: float | None
    photodiode_on_s: int
    laser_bank_on_s: int
    last_command: LastCommand | None

    @classmethod
    def from_reply(cls, reply: Reply) -> BoardStatus:
        """Build from a ``status`` reply."""
        last = reply.get("lastcmd")
        return cls(
            firmware=reply["fw"],
            boots=reply["boots"],
            board=reply["board"],
            board_ok=reply["board_ok"],
            mems_switches=reply["mems_switches"],
            relay_errors=reply["relay_err"],
            ambient_c=reply["amb_c"],
            photodiode_on_s=reply["pd_on_s"],
            laser_bank_on_s=reply["laserbank_on_s"],
            last_command=LastCommand(last["name"], last["src"], last["t_ms"]) if last else None,
        )


@dataclass(frozen=True)
class BoardTime:
    """Board clock as reported by the ``time`` query."""

    utc_ms: int
    uptime_s: int


@dataclass(frozen=True)
class BoardOptions:
    """Static names for the board's profile, from ``help/options``."""

    board: str
    lasers: tuple[str, ...]
    route_inputs: tuple[str, ...]
    route_outputs: tuple[str, ...]
    routes: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class MemsSwitch:
    """Requested state of one MEMS switch."""

    state: str
    duty_cycle: float | None = None


@dataclass(frozen=True)
class Temperatures:
    """Board temperatures from the ``temps`` query; laser entries are TIB only."""

    ambient_c: float | None
    laser_bank_c: float | None
    lasers: Mapping[str, float | None]


class FibBoard(HardwareDeviceBase):
    """One FIB PCB, reached through the MQTT broker by its device name.

    Subclasses set ``BOARD`` to the firmware profile name; ``connect`` fails if
    the board at that device name reports a different profile.
    """

    BOARD: ClassVar[str]

    def __init__(self, timeout_s: float = DEFAULT_TIMEOUT_S,
                 client_factory: Callable[[], mqtt.Client] | None = None,
                 log: bool = True, logfile: str | None = None) -> None:
        super().__init__(log=log, logfile=logfile)
        self.timeout_s = timeout_s
        self.on_warning: EventCallback | None = None
        self.on_boot: EventCallback | None = None
        self._client_factory = client_factory
        self._transport: FibPcbClient | None = None
        self._pending: PendingQuery | None = None

    def connect(self, device: str, broker: str,  # pylint: disable=arguments-differ
                port: int = DEFAULT_PORT) -> None:
        """Connect through the broker and confirm the board profile."""
        transport = FibPcbClient(device, broker, port, self._client_factory, self.logger)
        transport.on_warning = self._handle_warning
        transport.on_boot = self._handle_boot
        transport.open()
        self._transport = transport
        try:
            board = self.board_status().board
        except FibError:
            self.disconnect()
            raise
        if board != self.BOARD:
            self.disconnect()
            raise FibError(f"{device} reports board {board!r}, expected {self.BOARD!r}")
        self._set_connected(True)
        self.report_info(f"Connected to {device} via {broker}:{port}")

    def disconnect(self) -> None:
        """Close the broker connection."""
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        self._set_connected(False)

    def is_connected(self) -> bool:
        """Return True while connected and the broker link is up."""
        return self.connected and self._transport is not None and self._transport.is_open

    def query(self, key: str, options: Mapping[str, bool] | None = None) -> Reply:
        """Return the board's reply to one allowlisted query."""
        with self.lock:
            self._send_command(key, options)
            return self._read_reply()

    def board_status(self) -> BoardStatus:
        """Return the board's cached status."""
        return BoardStatus.from_reply(self.query("status"))

    def time(self) -> BoardTime:
        """Return the board clock."""
        reply = self.query("time")
        return BoardTime(reply["utc"], reply["uptime_s"])

    def options(self) -> BoardOptions:
        """Return the laser, route input and route output names for this profile."""
        reply = self.query("help/options")
        return BoardOptions(
            board=reply["board"],
            lasers=tuple(reply["lasers"]),
            route_inputs=tuple(reply["route_inputs"]),
            route_outputs=tuple(reply["route_outputs"]),
            routes=tuple((source, output) for source, output in reply["routes"]),
        )

    def mems(self) -> dict[str, MemsSwitch]:
        """Return every MEMS switch's requested state, keyed by switch name."""
        return {name: MemsSwitch(entry["state"], entry.get("duty_cycle"))
                for name, entry in self.query("mems").items()}

    def active_routes(self) -> dict[str, tuple[str, ...]]:
        """Return the inputs currently routed to each output; empty when none."""
        routes = self.query("mems/route")["active_routes"]
        return {output: tuple(source for source in sources if source != NO_SOURCE)
                for output, sources in routes.items()}

    def temps(self) -> Temperatures:
        """Return ambient and, on the TIB, laser bank temperatures."""
        reply = self.query("temps")
        return Temperatures(reply["ambient_c"], reply.get("laserbank_c"),
                            reply.get("lasers", {}))

    def _send_command(self, key: str,  # pylint: disable=arguments-differ
                      options: Mapping[str, bool] | None = None) -> bool:
        if self._transport is None:
            raise FibError("not connected")
        self._pending = self._transport.send(key, options)
        return True

    def _read_reply(self) -> Reply:
        if self._transport is None or self._pending is None:
            raise FibError("no query in flight")
        pending, self._pending = self._pending, None
        return self._transport.result(pending, self.timeout_s)

    def _handle_warning(self, event: Reply) -> None:
        self.report_warning(f"{event.get('code')}: {event.get('msg')} "
                            f"({event.get('context')})")
        if self.on_warning is not None:
            self.on_warning(event)

    def _handle_boot(self, event: Reply) -> None:
        self.report_warning(f"Board rebooted, reset cause {event.get('reset_cause')}")
        if self.on_boot is not None:
            self.on_boot(event)
