"""The HSFEI devices, and how to bring up each one's driver.

Device names are the daemons' ``peer_id`` values, which are also the config
file names under ``config/hsfei/``. Everything hardware-specific — addresses,
axes, named positions, sensor channels — stays in those config files, so this
module holds only the mapping from a device to the driver class that speaks to
it.

Driver imports are deliberately inside the builders: the driver packages are
git submodules, so importing this module must not require every one of them to
be checked out.
"""
# pylint: disable=import-outside-toplevel
from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from ..base import DeviceSpec
from ..errors import ConfigError

ADC = "adc"
ATCCRYO = "atccryo"
ATCFW = "atcfw"
ATCL = "atcl"
ATCP = "atcp"
ATCPRESS = "atcpress"
ATCTHERM = "atctherm"
FEIPO = "feipo"
LSM = "lsm"
MS = "ms"
PIAAGIMB = "piaagimb"
PIAAGIMR = "piaagimr"

#: Devices driven by a PI controller (or daisy chain) through ``PIControllerBase``.
PI_DEVICES = (ATCL, ATCP, FEIPO, LSM, MS)

#: Thorlabs PPC102 piezo gimbal mounts.
PIAA_DEVICES = (PIAAGIMB, PIAAGIMR)


def _address(config: Dict[str, Any]) -> Tuple[str, int]:
    """Pull ``(ip_address, tcp_port)`` out of a device config."""
    hardware = config.get("hardware") or {}
    ip_address = hardware.get("ip_address")
    tcp_port = hardware.get("tcp_port")
    if not ip_address or not tcp_port:
        raise ConfigError("config has no hardware.ip_address / hardware.tcp_port")
    return str(ip_address), int(tcp_port)


def _connect(driver: Any, config: Dict[str, Any], logger: logging.Logger,
             *, initialize: bool = True) -> Any:
    """Connect a driver over TCP and initialize it, the way the daemons do."""
    ip_address, tcp_port = _address(config)
    driver.connect(host=ip_address, port=tcp_port)
    if initialize and driver.is_connected():
        driver.initialize()
    logger.debug("connected %s to %s:%s", type(driver).__name__,
                 ip_address, tcp_port)
    return driver


def build_pi(config: Dict[str, Any], logger: logging.Logger) -> Any:
    """Connect a PI controller, daisy-chaining when the config lists stages."""
    from hispec.driver.pi import PIControllerBase

    ip_address, tcp_port = _address(config)
    driver = PIControllerBase(log=True)
    if len(config.get("stages") or []) > 1:
        driver.connect_tcpip_daisy_chain(ip_address, tcp_port)
    else:
        driver.connect_tcp(ip_address, tcp_port)
    logger.debug("connected PI controller at %s:%s", ip_address, tcp_port)
    return driver


def build_adc(config: Dict[str, Any], logger: logging.Logger) -> Any:
    """Connect the two daisy-chained Newport SMC100PP prism rotators."""
    from hispec.driver.newport.smc100pp import StageController

    hardware = config.get("hardware") or {}
    stages = config.get("stages") or []
    driver = StageController(num_stages=len(stages) or 2, log=True)
    move_rate = hardware.get("move_rate")
    if move_rate:
        driver.move_rate = float(move_rate)
    ip_address, tcp_port = _address(config)
    driver.connect(host=ip_address, port=tcp_port)
    if driver.is_connected():
        driver.initialize()
    logger.debug("connected ADC rotators at %s:%s", ip_address, tcp_port)
    return driver


def build_piaa_gimbal(config: Dict[str, Any], logger: logging.Logger) -> Any:
    """Connect a Thorlabs PPC102 piezo gimbal mount controller."""
    from hispec.driver.thorlabs.ppc102 import Ppc102Controller

    return _connect(Ppc102Controller(log=True), config, logger, initialize=False)


def build_filter_wheel(config: Dict[str, Any], logger: logging.Logger) -> Any:
    """Connect the Thorlabs FW102C filter wheel."""
    from hispec.driver.thorlabs.fw102c import FilterWheelController

    return _connect(FilterWheelController(log=True), config, logger)


def build_lakeshore(config: Dict[str, Any], logger: logging.Logger) -> Any:
    """Connect the ATC dewar's Lakeshore temperature controller."""
    from hispec.driver.lakeshore.lakeshore import LakeshoreController

    hardware = config.get("hardware") or {}
    driver = LakeshoreController(
        log=True,
        model336=bool(hardware.get("model336", True)),
        opt3062=bool(hardware.get("opt3062", False)),
        celsius=bool(hardware.get("celsius", False)))
    return _connect(driver, config, logger)


def build_pressure(config: Dict[str, Any], logger: logging.Logger) -> Any:
    """Connect the ATC dewar's Inficon VGC502 pressure gauge controller."""
    from hispec.driver.inficon.inficonvgc502 import InficonVGC502

    return _connect(InficonVGC502(log=True), config, logger)


def build_cryocooler(config: Dict[str, Any], logger: logging.Logger) -> Any:
    """Connect the ATC dewar's Sunpower cryocooler."""
    from hispec.driver.sunpower.sunpower_cryocooler import SunpowerCryocooler

    return _connect(SunpowerCryocooler(log=True), config, logger)


#: Every HSFEI device, with the builder that brings its driver up.
DEVICE_SPECS: Dict[str, DeviceSpec] = {
    ADC: DeviceSpec(build_adc, description="ADC prism rotators"),
    ATCCRYO: DeviceSpec(build_cryocooler, description="ATC cryocooler"),
    ATCFW: DeviceSpec(build_filter_wheel, description="ATC filter wheel"),
    ATCL: DeviceSpec(build_pi, description="focal/pupil plane selector"),
    ATCP: DeviceSpec(build_pi, description="ATC pickoff dichroic selector"),
    ATCPRESS: DeviceSpec(build_pressure, description="ATC pressure gauges"),
    ATCTHERM: DeviceSpec(build_lakeshore, description="ATC temperature controller"),
    FEIPO: DeviceSpec(build_pi, description="FEI pickoff mirror"),
    LSM: DeviceSpec(build_pi, description="light source module"),
    MS: DeviceSpec(build_pi, description="mask selector"),
    PIAAGIMB: DeviceSpec(build_piaa_gimbal, description="PIAA blue gimbal mount"),
    PIAAGIMR: DeviceSpec(build_piaa_gimbal, description="PIAA red gimbal mount"),
}

#: Every device name, in config order.
DEVICES = tuple(DEVICE_SPECS)
