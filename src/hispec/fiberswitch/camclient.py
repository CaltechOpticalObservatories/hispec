"""The fiber switch daemon's handle on its channel's camera daemon.

The switcher PLC and the DI-2000 inspection camera run as separate daemons
(fiberswitch<channel> and fiberswitch<channel>cam). The switch daemon's
controller still inspects fiber ends, through CameraDaemonClient, which has
the two InspectionCamera methods FiberSwitchController calls and does them by
keyword on the camera daemon:

- set_setting(name, value) writes the camera daemon's `settings`;
- inspect(tag, cancel, max_defect_area_fraction) writes its `inspect`, waits
  for that job to finish and returns the result from `lastresult`, as the
  camera's own inspect would. If the controller's job is cancelled meanwhile
  it fires the camera daemon's `halt` and raises JobAborted.

The calls go over a libby.Client of their own, built by make_client on first
use: the daemon's own connection runs keyword handlers on one thread, so a
handler waiting there for the camera daemon's reply would never see it.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable, Dict, Optional

from hispec.fiberswitch.jobs import ERROR_PREFIX, ABORTED, OK, JobAborted


class CameraDaemonError(RuntimeError):
    """The camera daemon refused a command, failed it or did not answer."""


class CameraDaemonClient:  # pylint: disable=too-many-instance-attributes
    """Inspect and set camera settings through the camera daemon's keywords."""

    # pylint: disable=too-many-arguments
    def __init__(self, daemon: str, make_client: Callable[[], Any], *,
                 timeout_s: float = 10.0, inspect_timeout_s: float = 180.0,
                 poll_s: float = 0.2, clock: Callable[[], float] = time.monotonic) -> None:
        if daemon.count(".") != 1:
            raise ValueError(f"camera.daemon must be <group>.<daemon>, got {daemon!r}")
        self.daemon = daemon.lower()
        self.timeout_s = timeout_s
        self.inspect_timeout_s = inspect_timeout_s
        self.poll_s = poll_s
        self._clock = clock
        self._make_client = make_client
        self._client = None
        self._lock = threading.Lock()

    def set_setting(self, name: str, value: float) -> None:
        """Set one camera property, as InspectionCamera.set_setting does."""
        self._set("settings", json.dumps({name: float(value)}))

    def inspect(self, tag: str, cancel: Optional[threading.Event] = None,
                max_defect_area_fraction: Optional[float] = None) -> Dict[str, Any]:
        """Run an inspection on the camera daemon and return its record."""
        if cancel is not None and cancel.is_set():
            raise JobAborted("inspect aborted before it started")
        request: Dict[str, Any] = {"tag": tag}
        if max_defect_area_fraction is not None:
            request["max_dirt"] = float(max_defect_area_fraction)
        before = int(self._get("jobid"))
        self._set("inspect", json.dumps(request))
        status = self._wait(before, cancel, f"inspect {tag}")
        if status == ABORTED:
            raise JobAborted(f"{self.daemon} aborted inspect {tag}")
        if status != OK:
            raise CameraDaemonError(f"{self.daemon} inspect {tag}: "
                                    f"{status.removeprefix(ERROR_PREFIX)}")
        record = json.loads(self._get("lastresult") or "{}")
        if record.get("tag") != tag or "image" not in record:
            raise CameraDaemonError(f"{self.daemon} did not report inspect {tag}'s result")
        return record

    def connected(self) -> bool:
        """The camera daemon answers and its camera is open."""
        try:
            return bool(self._get("isconnected"))
        except CameraDaemonError:
            return False

    def close(self) -> None:
        """Close this client's own libby connection."""
        with self._lock:
            client, self._client = self._client, None
        if client is not None:
            client.close()

    # Internals

    def _wait(self, before: int, cancel: Optional[threading.Event], label: str) -> str:
        """Wait for the job after `before` to finish; its jobstatus."""
        deadline = self._clock() + self.inspect_timeout_s
        while True:
            if cancel is not None and cancel.is_set():
                self._halt()
                raise JobAborted(f"{label} aborted")
            # Read busy first: a job seen finished here is finished in jobid
            # and jobstatus too
            busy = bool(self._get("busy"))
            if not busy and int(self._get("jobid")) > before:
                return str(self._get("jobstatus"))
            if self._clock() >= deadline:
                self._halt()
                raise CameraDaemonError(f"{self.daemon}: {label} still running after "
                                        f"{self.inspect_timeout_s:g} s; halted")
            if cancel is not None:
                cancel.wait(self.poll_s)
            else:
                time.sleep(self.poll_s)

    def _halt(self) -> None:
        try:
            self._set("halt", True)
        except CameraDaemonError:
            pass

    def _get(self, keyword: str) -> Any:
        return self._call(lambda c, name: c.get(name, timeout_s=self.timeout_s), keyword)

    def _set(self, keyword: str, value: Any) -> Any:
        return self._call(lambda c, name: c.set(name, value, timeout_s=self.timeout_s),
                          keyword)

    def _call(self, fn, keyword: str) -> Any:
        name = f"{self.daemon}.{keyword}"
        try:
            return fn(self._connection(), name)
        except CameraDaemonError:
            raise
        except Exception as e:  # pylint: disable=broad-exception-caught
            # libby's errors already name the keyword
            raise CameraDaemonError(str(e)) from e

    def _connection(self):
        with self._lock:
            if self._client is None:
                try:
                    self._client = self._make_client()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    raise CameraDaemonError(f"cannot reach the broker: {e}") from e
            return self._client
