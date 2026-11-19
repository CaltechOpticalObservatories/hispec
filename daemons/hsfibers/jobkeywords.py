"""Keywords that watch a fiberswitch daemon's background job (hispec.fiberswitch.jobs).

libby runs every keyword handler on the transport's single receive thread, so
a setter that blocks for a move or an inspection also blocks every other
keyword on that daemon, including the one that would halt it. The fiberswitch
daemons therefore validate a command in its setter, start it as a JobRunner
job and return; clients poll `busy` and read `jobstatus` when it clears.
"""

from hispec.fiberswitch.jobs import JobRunner


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
