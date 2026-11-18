"""One background job at a time, with keywords to watch it.

libby runs every keyword handler on the transport's single receive thread, so
a setter that blocks for a move or an inspection also blocks every other
keyword on that daemon, including the one that would halt it. The daemons in
this package therefore validate a command in its setter, start it here and
return; clients poll `busy` and read `jobstatus` when it clears.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

IDLE = "idle"
RUNNING = "running"
OK = "ok"
ABORTED = "aborted"
ERROR_PREFIX = "error: "


class JobAborted(RuntimeError):
    """Raised inside a job that saw its cancel event set."""


class JobRunner:
    """Run one labelled job at a time on a worker thread."""

    def __init__(self, logger=None) -> None:
        self.logger = logger
        self.cancel = threading.Event()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._label = ""
        self._status = IDLE
        self._job_id = 0

    @property
    def busy(self) -> bool:
        """True while a job is running."""
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    @property
    def state(self) -> str:
        """The running job's label, else idle."""
        with self._lock:
            running = self._thread is not None and self._thread.is_alive()
            return self._label if running else IDLE

    @property
    def status(self) -> str:
        """Outcome of the latest job: running, ok, aborted or 'error: ...'."""
        with self._lock:
            return self._status

    @property
    def job_id(self) -> int:
        """Number of the latest job started; 0 before the first."""
        with self._lock:
            return self._job_id

    def start(self, label: str, fn: Callable[[threading.Event], None]) -> int:
        """Run fn(cancel_event) on a worker thread; refuse while one is running.

        Returns the new job's id.
        """
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError(f"busy with {self._label}; wait or abort it first")
            self.cancel.clear()
            self._job_id += 1
            self._label = label
            self._status = RUNNING
            self._thread = threading.Thread(target=self._run, args=(label, fn),
                                            name=f"job-{label}", daemon=True)
            self._thread.start()
            return self._job_id

    def abort(self) -> None:
        """Ask the running job to stop at its next check."""
        self.cancel.set()

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait for the running job to finish; True if none is left running."""
        with self._lock:
            thread = self._thread
        if thread is None:
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def _run(self, label: str, fn: Callable[[threading.Event], None]) -> None:
        try:
            fn(self.cancel)
            status = OK
        except JobAborted as e:
            status = ABORTED
            self._log("warning", "%s aborted: %s", label, e)
        except Exception as e:  # pylint: disable=broad-exception-caught
            status = f"{ERROR_PREFIX}{e}"
            self._log("error", "%s failed: %s", label, e)
        with self._lock:
            self._status = status

    def _log(self, level: str, msg: str, *args) -> None:
        if self.logger is not None:
            getattr(self.logger, level)(msg, *args)


def register_job_keywords(registry, runner: JobRunner, *, abort_action=None,
                          abort_name: str = "abort") -> None:
    """Register busy, state, jobid, jobstatus and the abort trigger."""
    registry.bool("busy", getter=lambda: runner.busy,
                  description="A command is running; poll until false, then read jobstatus.")
    registry.string("state", getter=lambda: runner.state,
                    description="Label of the running command, else idle.")
    registry.int("jobid", getter=lambda: runner.job_id,
                 description="Number of the latest command started.")
    registry.string("jobstatus", getter=lambda: runner.status,
                    description="Outcome of the latest command: running, ok, aborted "
                                "or 'error: <message>'.")
    registry.trigger(abort_name, action=abort_action or runner.abort,
                     description="Stop the running command at its next safe point.")
