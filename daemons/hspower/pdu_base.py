"""Shared base class for the PDU daemons.

Each PDU family gets its own daemon script in this directory that
subclasses PduDaemon The base class does everything that is the same for every PDU: 
reading config, connecting, the keywords every PDU has, and the JSON status keyword. 
A subclass only says how to talk to its hardware.

The hardware methods raise an exception when something goes wrong rather
than returning a value that means failure, so the keyword that called them
reports the problem.
"""

import argparse
import json
import os
import pathlib
import sys
from typing import Any, Dict, Optional

import hispec.driver.pdu  # pylint: disable=E0611
from hispec.daemon import HispecDaemon  # pylint: disable=E0611

_DRIVER_SRC = str(pathlib.Path(next(iter(hispec.driver.pdu.__path__))) / "src")
if _DRIVER_SRC not in sys.path:
    sys.path.insert(0, _DRIVER_SRC)


class PduDaemon(HispecDaemon):  # pylint: disable=W0223,too-many-public-methods
    """Base class for a daemon that controls one networked PDU."""

    # Port used when the config leaves hardware.tcp_port out.
    default_port = 23

    def __init__(self):
        """Initialize the PDU daemon.

        A subclass calls this first, then sets self.dev to its vendor driver.
        """
        super().__init__()

        self.host = None
        self.port = self.default_port
        self.username = None
        self.password = None
        self.outlet_count = 0
        self.dev = None
        self.daemon_desc = "PDU Daemon"

        # Daemon state
        self.state = {
            'error': '',
        }

    def connect(self) -> bool:
        """Open a session to the PDU at self.host and self.port, logging in
        with self.username and self.password. True when the session is up."""
        raise NotImplementedError

    def disconnect(self) -> None:
        """Close the session, tolerating one that was never opened."""
        raise NotImplementedError

    def is_connected(self) -> bool:
        """True while a session to the PDU is open."""
        raise NotImplementedError

    def initialize(self) -> bool:
        """Read the PDU's device properties after connect(). True on success."""
        raise NotImplementedError

    def reported_outlet_count(self) -> Optional[int]:
        """Outlet count as the PDU reports it, or None when it cannot say."""
        raise NotImplementedError

    def get_model(self) -> str:
        """PDU model, as reported by the hardware."""
        raise NotImplementedError

    def get_firmware(self) -> str:
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

    def register_device_keywords(self) -> None:
        """Register the keywords that describe the whole PDU."""
        self.keyword_registry.string("model",
                        getter=self.when_connected(self.get_model),
                        description="PDU model number, as reported by the hardware.")
        self.keyword_registry.string("firmware",
                        getter=self.when_connected(self.get_firmware),
                        description="PDU firmware revision, as reported by the hardware.")

    def register_outlet_keywords(self, n: int) -> None:
        """Register the keywords for outlet ``n``."""
        self.keyword_registry.bool(f"outletstate{n}",
                      getter=self.when_connected(self.get_outlet_state, n),
                      setter=self.when_connected(self.set_outlet_state, n),
                      description=f"Outlet {n} power state; write true/false to switch on/off.")
        self.keyword_registry.string(f"outletname{n}",
                        getter=self.when_connected(self.get_outlet_name, n),
                        setter=self.when_connected(self.set_outlet_name, n),
                        description=f"Outlet {n} name, as configured on the PDU.")
        self.keyword_registry.bool(f"outletswitchable{n}",
                      getter=self.when_connected(self.get_outlet_switchable, n),
                      setter=self.when_connected(self.set_outlet_switchable, n),
                      description=f"Whether outlet {n} can be switched (True) or is locked "
                                  "in its current state (False); write to lock/unlock it.")

    def device_status(self) -> Dict[str, Any]:
        """The whole-PDU part of the status keyword."""
        return {
            "model": self.get_model(),
            "firmware": self.get_firmware(),
        }

    def outlet_status(self, n: int) -> Dict[str, Any]:
        """Outlet ``n``'s entry in the status keyword."""
        return {
            "number": n,
            "state": self.get_outlet_state(n),
            "name": self.get_outlet_name(n),
            "switchable": self.get_outlet_switchable(n),
        }

    def when_connected(self, func, *args):
        """Wrap a hardware call for a keyword so it fails cleanly while
        disconnected.
        """
        def call(*value):
            if not self._connected():
                raise RuntimeError("Not connected to hardware")
            return func(*args, *value)
        return call

    def on_start(self, libby): #pylint: disable=W0613
        """Starts up daemon and initializes the hardware device."""
        self.host = self.get_config("hardware.ip_address")
        self.port = self._opt_int(self.get_config("hardware.tcp_port")) or self.default_port
        self.username = self._credential("username")
        self.password = self._credential("password")
        self.daemon_desc = self.get_config("peer_id") or self.daemon_desc

        self.outlet_count = self._opt_int(self.get_config("hardware.outlet_count")) or 0
        if self.outlet_count < 1:
            self.logger.error("hardware.outlet_count must be a positive integer")
            self.state['error'] = 'hardware.outlet_count must be a positive integer'
            return

        # Keywords register regardless of hardware availability so the daemon
        # is usable (and inspectable) even while the PDU is unreachable.
        self._register_keywords()

        if not (self.host and self.username and self.password):
            self.logger.error(
                "hardware.ip_address, and a username and password (either "
                "hardware.<name> or hardware.<name>_env), are all required")
            self.state['error'] = 'missing PDU connection parameters'
            return

        if not self._set_connected(True).get("ok"):
            self.logger.warning("Daemon will start but hardware is not available")
            return
        self.logger.info("Daemon started successfully and connected to hardware")

        if not self._initialize().get("ok"):
            self.logger.warning("Daemon will start but hardware is not initialized")
            return
        self.logger.info("Initialized %s", self.daemon_desc)

    def on_stop(self, libby) -> None: #pylint: disable=W0222,W0613
        """Stops the daemon and disconnects from hardware device."""
        if self._set_connected(False).get("ok"):
            self.logger.info("Disconnected %s", self.daemon_desc)
        else:
            self.logger.error("Disconnect %s failed", self.daemon_desc)

    def _register_keywords(self):
        """Register keywords for the daemon."""
        self.keyword_registry.bool("isconnected",
                        getter=self._connected,
                        setter=self.keyword_wrapper(self._set_connected, key="isconnected"),
                        description="Check if daemon can talk to the PDU.")
        self.keyword_registry.string("error",
                        getter=lambda: self.state['error'],
                        description="Get the current error message.")
        self.keyword_registry.int("outletcount",
                        getter=lambda: self.outlet_count,
                        description="Number of outlets configured for this PDU.")
        self.keyword_registry.string("status",
                        getter=self.keyword_wrapper(self._status, key="status"),
                        description="JSON status summary of the PDU and all outlets.")
        self.keyword_registry.trigger("shutdown",
                        action=self._shutdown,
                        description="Shutdown the daemon now.")

        self.register_device_keywords()
        for n in range(1, self.outlet_count + 1):
            self.register_outlet_keywords(n)

    def _connected(self) -> bool:
        """True when the driver holds an open session to the PDU."""
        return self.dev is not None and bool(self.is_connected())

    def _set_connected(self, connect):
        """Handles connection."""
        connect = bool(connect)
        try:
            if connect:
                if not self.connect():
                    raise ConnectionError("Driver reported failure, see the driver log for details")
            else:
                self.disconnect()
            result = self._connected()
            if result != connect:
                raise ConnectionError("Failed to handle connection request")
            self.logger.info("isconnected: %s", result)
        except Exception as e: # pylint: disable=W0718
            self.logger.error("Failed to execute: %s", e)
            self.state['error'] = str(e)
            return {"ok": False, "error": str(e)}
        self.state['error'] = ''
        return {"ok": True, "isconnected": result}

    def _initialize(self):
        """Handles initialization."""
        if not self._connected():
            return {"ok": False, "error": "Not connected to hardware"}
        try:
            if not self.initialize():
                raise RuntimeError("Driver failed to initialize the PDU")
            reported = self.reported_outlet_count()
            if reported and reported != self.outlet_count:
                self.logger.warning(
                    "Configured hardware.outlet_count (%d) does not match hardware (%d)",
                    self.outlet_count, reported)
        except Exception as e: # pylint: disable=W0718
            return self._fail(str(e))
        return {"ok": True}

    def _status(self):
        """Handles status."""
        if not self._connected():
            return {"ok": False, "error": "Not connected to hardware"}
        try:
            status = {"connected": True}
            status.update(self.device_status())
            status["outlets"] = [self.outlet_status(n)
                                 for n in range(1, self.outlet_count + 1)]
            status["error"] = self.state['error']
            self.logger.debug("status: %s", status)
        except Exception as e: # pylint: disable=W0718
            return self._fail(str(e))
        return {"ok": True, "status": json.dumps(status)}

    def _shutdown(self):
        """Shutdown the daemon"""
        self.logger.info("Shutting down")
        self.disconnect()
        self.request_stop()

    @staticmethod
    def _confirm(ok, action: str) -> None:
        """Raise when a driver call reports that it refused to act."""
        if not ok:
            raise RuntimeError(f"driver refused to {action}")

    def _fail(self, message):
        """Log an error, record it in daemon state, and build the error return."""
        self.logger.error("Error: %s", message)
        self.state['error'] = message
        return {"ok": False, "error": message}

    def _credential(self, name: str) -> Optional[str]:
        """Read one login credential from config, or from the environment.
        """
        value = self.get_config(f"hardware.{name}")
        if value:
            self.logger.warning(
                "hardware.%s holds the value inline; prefer hardware.%s_env, which names "
                "an environment variable, so the credential stays out of the config file",
                name, name)
            return str(value)

        env_name = self.get_config(f"hardware.{name}_env")
        if not env_name:
            return None
        value = os.environ.get(str(env_name))
        if not value:
            self.logger.error("hardware.%s_env names %s, which is unset or empty",
                              name, env_name)
            return None
        return value

    def _opt_int(self, value) -> Optional[int]:
        """Normalize a config value to an int, or None when it is unset/invalid."""
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            self.logger.warning("Config value '%s' is not an integer, ignoring", value)
            return None

    def keyword_wrapper(self, func, key=None):
        """Wrap a daemon method for use as a keyword getter/setter."""
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if not result.get("ok"):
                message = result.get("error", f"Unknown error in {func.__name__}")
                self.logger.error("keyword_wrapper [%s]: %s", func.__name__, message)
                raise RuntimeError(message)
            if key:
                return result[key]
            return {k: v for k, v in result.items() if k != "ok"}
        return wrapper


def main(daemon_class, description: str):
    """Main entry point shared by the PDU daemon scripts."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-c', '--config', type=str,
                        help='Path to config file (YAML or JSON)')
    parser.add_argument('-d', '--daemon-id', type=str,
                        help='Daemon ID (required for subsystem configs with multiple daemons)')

    args = parser.parse_args()

    if not args.config:
        print("--config is required", file=sys.stderr)
        sys.exit(2)

    try:
        daemon = daemon_class.from_config_file(args.config)
        daemon.serve()
    except KeyboardInterrupt:
        print("\nDaemon interrupted by user")
        sys.exit(0)
    except Exception as e: #pylint: disable=W0718
        print(f"Error running daemon: {e}", file=sys.stderr)
        sys.exit(1)
