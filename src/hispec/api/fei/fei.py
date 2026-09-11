"""High-level API for the HISPEC Front End Instrument (FEI).

The drivers do the moving and the reading. :class:`FEI` is where the functions
that *call* them live: move two axes together and wait for both, home the whole
subsystem and report what failed, start a cooldown and watch it, snapshot every
device at once. Those are the functions that keep getting rewritten per script;
this is their home.

Axis addressing comes out of ``config/hsfei/*.yaml`` — the same files the
daemons read — so a controller's address, axis and named positions have exactly
one definition.

Example::

    from hispec.api.fei import FEI

    with FEI() as fei:
        print(fei.status())                 # one snapshot of the subsystem
        fei.select_mask("slot_1")           # both mask axes, then wait for both
        fei.move_adc(10.0, -10.0)           # both prisms, then wait for both

Driver calls stay available for anything not worth a method here::

    axis = fei.pi_axis("ms_h")
    axis.driver.set_pos(1.0, axis.device_key, axis.axis, blocking=True)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from ..base import SubsystemAPI
from ..errors import DeviceError
from . import devices

#: Default ceiling, in seconds, on one axis's move or reference move.
DEFAULT_MOVE_TIMEOUT_S = 120.0

#: Default ceiling, in seconds, on a cooldown.
DEFAULT_COOLDOWN_TIMEOUT_S = 6 * 3600.0


@dataclass(frozen=True)
class PiAxis:
    """One PI axis, resolved from its daemon config.

    Holds what every PI driver call needs — the controller, the
    ``(ip, port, device_id)`` device key and the axis string — so no procedure
    or script has to assemble them from config by hand.
    """

    name: str
    device: str
    driver: Any
    device_key: Tuple[str, int, int]
    axis: str
    units: Optional[str] = None
    named_positions: Dict[str, float] = field(default_factory=dict)

    def named_target(self, name: str) -> float:
        """Return the position configured for a named position."""
        try:
            return float(self.named_positions[name])
        except KeyError:
            raise KeyError(
                f"{self.name}: unknown named position '{name}'; "
                f"available: {sorted(self.named_positions)}") from None


class FEI(SubsystemAPI):
    """The FEI subsystem: its device drivers, and the procedures over them."""

    group_id = "hsfei"
    DEVICE_SPECS = devices.DEVICE_SPECS

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._axis_specs: Optional[Dict[str, Dict[str, Any]]] = None

    # -- driver handles -------------------------------------------------------

    @property
    def adc(self) -> Any:
        """The Newport controller driving both ADC prism rotators."""
        return self.driver(devices.ADC)

    @property
    def cryo(self) -> Any:
        """The ATC Sunpower cryocooler."""
        return self.driver(devices.ATCCRYO)

    @property
    def thermal(self) -> Any:
        """The ATC Lakeshore temperature controller."""
        return self.driver(devices.ATCTHERM)

    @property
    def pressure(self) -> Any:
        """The ATC Inficon pressure gauge controller."""
        return self.driver(devices.ATCPRESS)

    @property
    def filter_wheel(self) -> Any:
        """The ATC Thorlabs filter wheel."""
        return self.driver(devices.ATCFW)

    def piaa_gimbal(self, device: str = devices.PIAAGIMB) -> Any:
        """The PPC102 controller for one PIAA gimbal mount."""
        return self.driver(device)

    # -- axis addressing ------------------------------------------------------

    def axis_names(self) -> List[str]:
        """Return every PI axis name, e.g. ``["atcl", "ms_h", "ms_v", ...]``.

        Single-axis devices are named after the device (``feipo``); a
        daisy-chained device's axes take the stage name from its config
        (``ms_h``, ``lsm_v``).
        """
        return list(self._resolve_axis_specs())

    def pi_axis(self, name: str) -> PiAxis:
        """Resolve one PI axis, connecting its controller if needed."""
        specs = self._resolve_axis_specs()
        try:
            spec = specs[name]
        except KeyError:
            raise KeyError(f"unknown FEI axis '{name}'; "
                           f"available: {sorted(specs)}") from None
        device = spec["device"]
        ip_address = self.config_value(device, "hardware.ip_address")
        tcp_port = self.config_value(device, "hardware.tcp_port")
        return PiAxis(
            name=name,
            device=device,
            driver=self.driver(device),
            device_key=(ip_address, int(tcp_port), int(spec["device_id"])),
            axis=str(spec["axis"]),
            units=spec.get("units"),
            named_positions=spec.get("named_positions") or {},
        )

    def device_axes(self, device: str) -> List[PiAxis]:
        """Resolve every PI axis belonging to one device, in config order."""
        return [self.pi_axis(name)
                for name, spec in self._resolve_axis_specs().items()
                if spec["device"] == device]

    # -- motion procedures ----------------------------------------------------

    def move_axes(self, targets: Dict[str, float], *, wait: bool = True,
                  timeout_s: float = DEFAULT_MOVE_TIMEOUT_S) -> Dict[str, Any]:
        """Command several PI axes at once, then wait for all of them.

        Every axis is commanded before any wait begins, so axes on the same
        controller move together instead of in series. That is the difference
        from calling ``set_pos(blocking=True)`` per axis.

        Returns the position read back from each axis.

        Raises:
            DeviceError: a controller refused a move command.
            ProcedureTimeout: an axis was still moving at ``timeout_s``.
        """
        axes = {name: self.pi_axis(name) for name in targets}
        for name, axis in axes.items():
            target = float(targets[name])
            self.logger.info("%s: moving to %s %s", name, target,
                             axis.units or "")
            if not axis.driver.set_pos(target, axis.device_key, axis.axis,
                                       blocking=False):
                raise DeviceError(f"{name}: controller refused move to {target}")
        if wait:
            self.wait_for_axes(axes.values(), timeout_s=timeout_s)
        return {name: axis.driver.get_pos(axis.device_key, axis.axis)
                for name, axis in axes.items()}

    def wait_for_axes(self, axes: Iterable[PiAxis], *,
                      timeout_s: float = DEFAULT_MOVE_TIMEOUT_S) -> float:
        """Wait until none of the given axes is moving; return seconds waited."""
        axes = list(axes)
        names = ", ".join(axis.name for axis in axes)
        return self.wait_until(
            lambda: not any(axis.driver.is_moving(axis.device_key, axis.axis)
                            for axis in axes),
            timeout_s, description=f"axes stopped ({names})")

    def move_to_named(self, device: str, position: str, *,
                      timeout_s: float = DEFAULT_MOVE_TIMEOUT_S) -> Dict[str, Any]:
        """Send every axis of one device to a named position from its config.

        The named positions live in ``config/hsfei/hsfei_<device>.yaml``, which
        is also where the daemon reads them, so the two cannot drift.
        """
        targets = {axis.name: axis.named_target(position)
                   for axis in self.device_axes(device)}
        self.logger.info("%s: selecting %s", device, position)
        return self.move_axes(targets, timeout_s=timeout_s)

    def select_mask(self, slot: str, **kwargs: Any) -> Dict[str, Any]:
        """Move the mask selector's two axes to a named slot together."""
        return self.move_to_named(devices.MS, slot, **kwargs)

    def position_lsm(self, position: str, **kwargs: Any) -> Dict[str, Any]:
        """Move the light source module's two axes to a named position."""
        return self.move_to_named(devices.LSM, position, **kwargs)

    def move_adc(self, angle1: float, angle2: float, *, wait: bool = True,
                 timeout_s: float = DEFAULT_MOVE_TIMEOUT_S) -> Dict[int, Any]:
        """Send both ADC prisms to absolute angles, then wait for both.

        The Newport driver's own blocking move handles one stage at a time;
        this commands both first so the prisms move together.
        """
        driver = self.adc
        for stage_id, angle in ((1, angle1), (2, angle2)):
            self.logger.info("adc prism %d: moving to %s deg", stage_id, angle)
            if not driver.move_abs(position=float(angle), stage_id=stage_id,
                                   blocking=False):
                raise DeviceError(
                    f"adc prism {stage_id}: controller refused move to {angle}")
        if wait:
            self.wait_until(
                lambda: not any("MOVING" in driver.get_state(stage_id)
                                for stage_id in (1, 2)),
                timeout_s, description="ADC prisms stopped")
        return {stage_id: driver.get_pos(stage_id) for stage_id in (1, 2)}

    def home_all(self, axes: Optional[Iterable[str]] = None, *,
                 skip_homed: bool = True,
                 timeout_s: float = DEFAULT_MOVE_TIMEOUT_S,
                 include_adc: bool = True) -> Dict[str, Optional[str]]:
        """Reference every FEI motion axis, one at a time.

        A failure is recorded and homing continues, so one dead controller does
        not leave the rest of the subsystem un-referenced.

        Returns:
            ``{axis: None}`` where the axis is referenced (or already was), and
            ``{axis: error}`` where it is not.
        """
        results: Dict[str, Optional[str]] = {}
        for name in (self.axis_names() if axes is None else list(axes)):
            results[name] = self._home_pi_axis(name, skip_homed, timeout_s)
        if include_adc and axes is None:
            results.update(self._home_adc(skip_homed))
        return results

    def halt_all(self) -> None:
        """Halt motion on every FEI motion controller that is connected.

        Only devices already brought up are touched: halting is what you reach
        for when something is wrong, and it should not start opening sockets.
        """
        for device in devices.PI_DEVICES:
            if not self.is_connected(device):
                continue
            axes = self.device_axes(device)
            if not axes:
                continue
            try:
                axes[0].driver.halt_motion(axes[0].device_key)
            except Exception as err:  # pylint: disable=broad-except
                self.logger.error("%s: halt failed: %s", device, err)
        if self.is_connected(devices.ADC):
            # The SMC100PP driver has no halt command; the daemon reports the
            # same gap. Left explicit so it is not mistaken for coverage.
            self.logger.warning("adc: no halt command in the SMC100PP driver")

    # -- reads ----------------------------------------------------------------

    def positions(self) -> Dict[str, Any]:
        """Read every FEI axis position, tolerating devices that are down."""
        reads: Dict[str, Callable[[], Any]] = {}
        for name in self.axis_names():
            reads[name] = self._pi_position_reader(name)
        for stage_id in (1, 2):
            reads[f"adc{stage_id}"] = self._adc_position_reader(stage_id)
        for device in devices.PIAA_DEVICES:
            for channel in (1, 2):
                reads[f"{device}_ch{channel}"] = self._piaa_position_reader(
                    device, channel)
        reads["atcfw"] = lambda: self.filter_wheel.get_pos()
        return self.collect(reads)

    def temperatures(self) -> Dict[str, Any]:
        """Read every ATC dewar sensor listed in the Lakeshore config."""
        sensors = self.config_value(devices.ATCTHERM, "sensors") or []
        return self.collect({
            entry.get("keyword", entry.get("channel")):
                self._temperature_reader(entry.get("channel"))
            for entry in sensors if entry.get("channel")})

    def heater_setpoints(self) -> Dict[str, Any]:
        """Read each configured Lakeshore heater's setpoint and output."""
        heaters = self.config_value(devices.ATCTHERM, "heaters") or []
        reads: Dict[str, Callable[[], Any]] = {}
        for entry in heaters:
            output = entry.get("id")
            if output is None:
                continue
            label = entry.get("keyword", output)
            reads[f"{label}_setpoint"] = self._heater_setpoint_reader(output)
            reads[f"{label}_output"] = self._heater_output_reader(output)
        return self.collect(reads)

    def pressures(self) -> Dict[str, Any]:
        """Read both ATC pressure gauges and the controller's temperature."""
        return self.collect({
            "gauge1": lambda: self.pressure.read_pressure(1),
            "gauge2": lambda: self.pressure.read_pressure(2),
            "controller_temp": lambda: self.pressure.read_temperature(),
        })

    def cryo_status(self) -> Dict[str, Any]:
        """Read the cryocooler's temperatures, power and error state."""
        return self.collect({
            "cold_head_temp": lambda: self.cryo.get_cold_head_temp(),
            "reject_temp": lambda: self.cryo.get_reject_temp(),
            "target_temp": lambda: self.cryo.get_target_temp(),
            "measured_power": lambda: self.cryo.get_measured_power(),
            "commanded_power": lambda: self.cryo.get_commanded_power(),
            "control_mode": lambda: self.cryo.get_control_mode(),
            "error": lambda: self.cryo.get_error(),
        })

    def status(self) -> Dict[str, Any]:
        """Collect one snapshot of the whole subsystem.

        Never raises: anything unreadable comes back as ``None``, so this is
        safe for logging the conditions a measurement started under.
        """
        return {
            "timestamp": time.time(),
            "positions": self.positions(),
            "temperatures": self.temperatures(),
            "heaters": self.heater_setpoints(),
            "pressures": self.pressures(),
            "cryo": self.cryo_status(),
        }

    # -- cryostat procedures --------------------------------------------------

    def cooldown(self, target_k: float, *, tolerance_k: float = 1.0,
                 timeout_s: float = DEFAULT_COOLDOWN_TIMEOUT_S,
                 poll_s: float = 30.0,
                 on_sample: Optional[Callable[[Dict[str, Any]], None]] = None,
                 ) -> List[Dict[str, Any]]:
        """Start the cryocooler and watch the ATC dewar down to ``target_k``.

        Sets the target temperature, turns the cooler on, then samples the cold
        head, the dewar sensors and the gauges every ``poll_s`` until the cold
        head is within ``tolerance_k`` of target. ``on_sample`` is called with
        each sample, for logging or plotting as it goes.

        Returns:
            Every sample taken, oldest first.

        Raises:
            ProcedureTimeout: the cold head had not reached target by
                ``timeout_s``. The cooler is left running.
        """
        self.logger.info("cooldown: target %s K (tolerance %s K)",
                         target_k, tolerance_k)
        self.cryo.set_target_temp(float(target_k))
        self.cryo.turn_on_cooler()

        started = time.monotonic()
        samples: List[Dict[str, Any]] = []

        def at_target() -> bool:
            sample = {
                "elapsed_s": time.monotonic() - started,
                "cryo": self.cryo_status(),
                "temperatures": self.temperatures(),
                "pressures": self.pressures(),
            }
            samples.append(sample)
            if on_sample is not None:
                on_sample(sample)
            cold_head = sample["cryo"].get("cold_head_temp")
            self.logger.info("cooldown: cold head %s K after %.0f s",
                             cold_head, sample["elapsed_s"])
            return cold_head is not None and cold_head <= target_k + tolerance_k

        self.wait_until(at_target, timeout_s, poll_s=poll_s,
                        description=f"cold head at {target_k} K")
        return samples

    # -- internals ------------------------------------------------------------

    def _resolve_axis_specs(self) -> Dict[str, Dict[str, Any]]:
        """Build the axis table from the PI device configs, once.

        Mirrors how the PI daemon reads its own config: a ``stages`` list
        describes a daisy chain, and its absence means one axis described by
        the ``hardware`` block.
        """
        if self._axis_specs is not None:
            return self._axis_specs

        specs: Dict[str, Dict[str, Any]] = {}
        for device in devices.PI_DEVICES:
            stages = self.config_value(device, "stages") or []
            if stages:
                for stage in stages:
                    name = f"{device}_{stage.get('name', '')}".rstrip("_")
                    specs[name] = {
                        "device": device,
                        "device_id": stage.get("device_id", 1),
                        "axis": stage.get("axis", "1"),
                        "units": stage.get("units"),
                        "named_positions": stage.get("named_positions") or {},
                    }
            else:
                specs[device] = {
                    "device": device,
                    "device_id": 1,
                    "axis": self.config_value(device, "hardware.axis", "1"),
                    "units": self.config_value(device, "hardware.units"),
                    "named_positions": self.config_value(
                        device, "named_positions") or {},
                }
        self._axis_specs = specs
        return specs

    def _home_pi_axis(self, name: str, skip_homed: bool,
                      timeout_s: float) -> Optional[str]:
        """Home one PI axis; return None on success or a message on failure."""
        try:
            axis = self.pi_axis(name)
            if skip_homed and axis.driver.is_homed(axis.device_key, axis.axis):
                self.logger.info("%s: already referenced, skipping", name)
                return None
            self.logger.info("%s: homing", name)
            if not axis.driver.home(axis.device_key, axis.axis,
                                    blocking=True, timeout=timeout_s):
                return "controller reported the reference move failed"
            return None
        except Exception as err:  # pylint: disable=broad-except
            self.logger.error("%s: homing failed: %s", name, err)
            return str(err)

    def _home_adc(self, skip_homed: bool) -> Dict[str, Optional[str]]:
        """Home both ADC prisms; the driver's home() polls to completion."""
        results: Dict[str, Optional[str]] = {}
        for stage_id in (1, 2):
            label = f"adc{stage_id}"
            try:
                driver = self.adc
                if skip_homed and driver.is_homed(stage_id):
                    self.logger.info("%s: already referenced, skipping", label)
                    results[label] = None
                    continue
                self.logger.info("%s: homing", label)
                results[label] = None if driver.home(stage_id) else (
                    "controller reported the reference move failed")
            except Exception as err:  # pylint: disable=broad-except
                self.logger.error("%s: homing failed: %s", label, err)
                results[label] = str(err)
        return results

    def _pi_position_reader(self, name: str) -> Callable[[], Any]:
        def read() -> Any:
            axis = self.pi_axis(name)
            return axis.driver.get_pos(axis.device_key, axis.axis)
        return read

    def _adc_position_reader(self, stage_id: int) -> Callable[[], Any]:
        return lambda: self.adc.get_pos(stage_id)

    def _piaa_position_reader(self, device: str, channel: int) -> Callable[[], Any]:
        return lambda: self.piaa_gimbal(device).get_pos(channel)

    def _temperature_reader(self, channel: str) -> Callable[[], Any]:
        return lambda: self.thermal.get_temperature(channel)

    def _heater_setpoint_reader(self, output: Any) -> Callable[[], Any]:
        return lambda: self.thermal.get_heater_setpoint(output)

    def _heater_output_reader(self, output: Any) -> Callable[[], Any]:
        return lambda: self.thermal.get_heater_output(output)
