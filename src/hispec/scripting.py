"""Helpers for test scripts that drive HISPEC through libby keywords.

A test script reads and writes keywords with a ``libby.Client`` directly; this
module holds the few steps that need more than one keyword and are easy to get
wrong when each script writes its own:

* :func:`connect` reaches the shared broker under a name that says who is
  commanding, so the daemon logs can tell scripts apart;
* :func:`preflight` refuses to start when a daemon is disconnected or a stage
  is not homed, before anything moves;
* :func:`move_and_verify` writes a position, waits for the stage to stop and
  checks where it ended up;
* :func:`halt_all` stops every stage a script might have moving, for Ctrl-C
  and error paths.

Every write goes through the daemon, so its soft limits, error keywords and
the keygrabber's telemetry all see what a script does.
"""
from __future__ import annotations

import getpass
import logging
import os
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from libby import Client, LibbyError

from .daemon import broker_url

logger = logging.getLogger(__name__)

#: Seconds :func:`move_and_verify` waits for a stage to stop moving.
DEFAULT_MOVE_TIMEOUT_S = 60.0

#: Seconds a stopped stage gets to settle into tolerance before a move fails.
#: Covers a read of ``ismoving`` that lands before the motion has started.
SETTLE_S = 1.0

#: Seconds between position reads while settling.
SETTLE_POLL_S = 0.1


class ScriptError(Exception):
    """Base class for the errors these helpers raise."""


class NotReady(ScriptError):
    """A daemon or stage failed the preflight check; nothing was moved."""


class MoveError(ScriptError):
    """A move was refused, did not finish, or ended out of tolerance."""


@dataclass(frozen=True)
class Stage:
    """
    Args:
        daemon: ``<group>.<daemon>``, e.g. ``"hsfei.ms"``.
        suffix: Axis suffix on a multi-stage daemon (``"h"`` gives
            ``positionvalueh``); empty for a single-stage daemon.
        tolerance: How close, in the stage's units, counts as in position.
        has_ismoving: The daemon reports motion through ``ismoving``. When
            False, as for a filter wheel, a position write returns only once
            the move is done, so there is nothing to wait on or halt.
        has_isreferenced: The daemon reports homing through ``isreferenced``.
    """

    daemon: str
    suffix: str = ""
    tolerance: float = 0.001
    has_ismoving: bool = True
    has_isreferenced: bool = True

    @property
    def name(self) -> str:
        """Short label for messages, e.g. ``hsfei.ms.h``."""
        return f"{self.daemon}.{self.suffix}" if self.suffix else self.daemon

    @property
    def position(self) -> str:
        """The stage's ``positionvalue`` keyword."""
        return f"{self.daemon}.positionvalue{self.suffix}"

    @property
    def ismoving(self) -> str:
        """The stage's ``ismoving`` keyword."""
        return f"{self.daemon}.ismoving{self.suffix}"

    @property
    def isreferenced(self) -> str:
        """The stage's ``isreferenced`` keyword."""
        return f"{self.daemon}.isreferenced{self.suffix}"


def connect(script_name: str) -> Client:
    """Connect to the shared HISPEC broker, as ``script-<name>-<user>-<pid>``.

    Use it in a ``with`` block so the connection closes however the script
    ends::

        with connect("psf-check") as client:
            print(client.get("hsfei.atcl.positionvalue"))
    """
    self_id = f"script-{script_name}-{getpass.getuser()}-{os.getpid()}"
    return Client.rabbitmq(self_id=self_id, rabbitmq_url=broker_url())


def preflight(client: Client, stages: Iterable[Stage]) -> None:
    """Check every daemon is connected and every stage homed, before moving.

    Reports every problem at once rather than the first, so one run shows
    everything that needs fixing.

    Raises:
        NotReady: A daemon is unreachable or disconnected, or a stage is not
            referenced.
    """
    stages = list(stages)
    daemons = list(dict.fromkeys(stage.daemon for stage in stages))
    names = [f"{daemon}.isconnected" for daemon in daemons]
    names += [stage.isreferenced for stage in stages if stage.has_isreferenced]
    replies = client.read(names)

    problems = []
    for name in names:
        reply = replies[name]
        if not reply.get("ok", False):
            problems.append(f"{name}: could not read ({reply.get('error')})")
        elif reply.get("value") is not True:
            problems.append(f"{name} is {reply.get('value')}")
    if problems:
        raise NotReady("not ready to move:\n  " + "\n  ".join(problems))
    logger.info("preflight passed for %s", ", ".join(daemons))


def at_target(client: Client, stage: Stage, target: float) -> Tuple[bool, float]:
    """Return whether a stage is within tolerance of ``target``, and where it is."""
    position = client.get(stage.position)
    return abs(position - target) <= stage.tolerance, position


def move_and_verify(client: Client, stage: Stage, target: float, *,
                    timeout_s: float = DEFAULT_MOVE_TIMEOUT_S) -> float:
    """Move a stage, wait for it to stop, and check it reached ``target``.

    A stage still moving at ``timeout_s`` is halted before the error is
    raised, so a failed move never leaves a stage running unattended.

    Returns:
        The position the stage ended at.

    Raises:
        MoveError: The daemon refused the move, the stage did not stop in
            time, or it stopped outside ``stage.tolerance`` of ``target``.
    """
    logger.info("moving %s to %s", stage.name, target)
    try:
        client.set(stage.position, target)
    except LibbyError as err:
        raise MoveError(f"{stage.name}: move to {target} refused: {err}") from err

    if stage.has_ismoving:
        result = client.wait_for_result(f"${stage.ismoving} == false", timeout_s)
        if not result.satisfied:
            halt_all(client, [stage])
            raise MoveError(f"{stage.name}: still moving after {timeout_s}s; halted")

    deadline = time.monotonic() + SETTLE_S
    while True:
        in_position, position = at_target(client, stage, target)
        if in_position:
            logger.info("%s is at %s", stage.name, position)
            return position
        if time.monotonic() >= deadline:
            break
        time.sleep(SETTLE_POLL_S)

    message = (f"{stage.name}: stopped at {position}, not within "
               f"{stage.tolerance} of {target}")
    daemon_error = _last_error(client, stage.daemon)
    if daemon_error:
        message += f" (daemon lasterror: {daemon_error})"
    raise MoveError(message)


def halt_all(client: Client, stages: Iterable[Stage]) -> List[str]:
    """Fire ``halt`` on every daemon owning one of ``stages``.

    Best effort: one daemon that cannot be reached does not stop the others
    being halted.

    Returns:
        A message for each daemon the halt failed on; empty when all halted.
    """
    daemons = dict.fromkeys(stage.daemon for stage in stages if stage.has_ismoving)
    failures = []
    for daemon in daemons:
        try:
            client.set(f"{daemon}.halt", True)
            logger.warning("halted %s", daemon)
        except LibbyError as err:
            failures.append(f"{daemon}: halt failed: {err}")
            logger.error("%s: halt failed: %s", daemon, err)
    return failures


def _last_error(client: Client, daemon: str) -> Optional[str]:
    """Read a daemon's ``lasterror``, or None if it is empty or unreadable."""
    try:
        return client.get(f"{daemon}.lasterror") or None
    except LibbyError:
        return None


__all__: List[str] = [
    "DEFAULT_MOVE_TIMEOUT_S",
    "MoveError",
    "NotReady",
    "ScriptError",
    "Stage",
    "at_target",
    "connect",
    "halt_all",
    "move_and_verify",
    "preflight",
]
