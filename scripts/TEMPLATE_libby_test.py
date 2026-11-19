#!/usr/bin/env python3
"""
TEMPLATE: copy this file to start a new HISPEC test script.

    cp scripts/TEMPLATE_libby_test.py scripts/<subsystem>/My_Test_Name.py

It works for any part of the instrument (FEI, calibration, power, ...),
because it only talks to daemons through libby keywords.

Then fill in the three sections marked EDIT HERE:
  1. this description, saying what the test checks;
  2. the settings: the stages and values the test uses;
  3. run_test(), the steps of the test.

Everything else (connecting, safety checks, stopping stages on Ctrl-C or on
an error, the PASS/FAIL line) is already done for you.

Talk to the instrument only through libby keywords, as shown below. Do not
import from hispec.driver or open serial ports or IP addresses yourself: the
daemons own the hardware, and going through them is what gives your script
soft limits, error reporting and a record in the telemetry (Grafana).

Run it:
    ./My_Test_Name.py

To give the script command-line options, add them with argparse;
scripts/fei/PSF_Check_LibbyElements.py is an example.

See "Writing Test Scripts" in the HISPEC docs (docs/operations/test_scripts.md)
for how to find keyword names.
"""
import logging
import sys

from libby import LibbyError

from hispec.scripting import (
    NotReady, ScriptError, Stage, connect, halt_all, move_and_verify, preflight)

# =============================================================================
# EDIT HERE: settings
# =============================================================================

# A short name for this script. It appears in the daemon logs, so whoever
# reads them can see which script sent a command.
SCRIPT_NAME = "template"

# The stages this script moves. A Stage is a daemon ("<group>.<daemon>", as
# `libby list` shows it), plus the axis name if the daemon has several:
#     Stage("hsfei.atcl")                     a single-axis daemon
#     Stage("hsfei.ms", "h")                  axis "h" of a two-axis daemon
#     Stage("hsfei.atcfw", tolerance=0,       a filter wheel: no ismoving or
#           has_ismoving=False,                 isreferenced keyword
#           has_isreferenced=False)
# Ready-made FEI stages can be imported instead: from hispec.fei import ATCL
ATCL = Stage("hsfei.atcl")

# Every stage this script might move. preflight() checks these are connected
# and homed before anything moves, and they are all halted if the script
# stops early.
STAGES = [ATCL]

# Where each stage should go, in the stage's own units (mm, degrees, or slot
# number for a filter wheel).
TARGETS = {
    ATCL: 7.15,
}


# =============================================================================
# EDIT HERE: the test steps
# =============================================================================

def run_test(client):
    """The steps of the test. Return True if it passed, False if not.

    `client` reads and writes any keyword, on any daemon:
        client.get("hscal.yjettherm.t2A_blue_etalon")    read a value
        client.set("hsfei.atcfw.positionnamed", "OD1")   write a value
        client.wait_for("$hsfei.atcl.ismoving == false", 30)
                                                         wait up to 30 s
    For a stage, use the helpers, which also wait and check the result:
        move_and_verify(client, ATCL, 7.15)   move, wait, check position
        at_target(client, ATCL, 7.15)         (True/False, where it is now)
    (at_target needs adding to the hispec.scripting import above.)
    """
    # Example step 1: read a value that is not a stage.
    temperature = client.get("hscal.yjettherm.t2A_blue_etalon")
    print(f"Blue etalon temperature: {temperature}")

    # Example step 2: move each stage to its target. move_and_verify stops
    # the test with an error if a move fails, so there is nothing to check.
    for stage, target in TARGETS.items():
        move_and_verify(client, stage, target)

    # Example step 3: decide whether the test passed, for example
    #     if temperature > 300:
    #         print("Etalon too warm")
    #         return False
    return True


# =============================================================================
# You should not need to change anything below this line.
# =============================================================================

def main():
    """Run the test, and stop every stage if it fails."""
    # Shows each step the helpers take (checks, moves, halts) with a timestamp
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    with connect(SCRIPT_NAME) as client:
        try:
            preflight(client, STAGES)
            passed = run_test(client)
        except NotReady as err:
            # Nothing has moved yet, so there is nothing to halt
            print(f"\nFAILED: {err}")
            return 1
        except KeyboardInterrupt:
            print("\nStopped by Ctrl-C; halting stages.")
            halt_all(client, STAGES)
            return 130
        except (ScriptError, LibbyError) as err:
            print(f"\nFAILED: {err}")
            halt_all(client, STAGES)
            return 1

    print("\nPASSED" if passed else "\nFAILED: see the messages above")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
