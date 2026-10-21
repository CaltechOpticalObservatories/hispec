#!/usr/bin/env python3
"""
Check that the libby-enabled FEI modules are in their default PSF-check positions.

If a module is not in position, the script asks whether to move it (or moves
it, or leaves it, depending on --move-mode). At the end it reports clearly
whether every module ended up in position.

The check is also available as check_default_positions() for other scripts.

Run it:
    ./PSF_Check_LibbyElements.py                # ask before each move
    ./PSF_Check_LibbyElements.py -m auto-move   # move without asking
    ./PSF_Check_LibbyElements.py -m do-not-move # report only
"""
import argparse
import logging
import sys

from libby import LibbyError

from hispec.fei import ATCFW, ATCL, ATCP, LSM_H, LSM_V, MS_H, MS_V
from hispec.scripting import (
    NotReady, ScriptError, at_target, connect, halt_all, move_and_verify, preflight)

# =============================================================================
# Settings
# =============================================================================

SCRIPT_NAME = "psf-check"

# Default position of each module, per stage, in the stage's own units.
# Stage tolerances are set in hispec/fei/stages.py (0.001 mm; exact slot for
# the filter wheel).
#   LSM, MS and ATCL match the named positions on_axis, keck_mask and focal in
#   config/hsfei/; ATCFW slot 1 is "empty".
# The ADC is left out until it has been checked out under its daemon.
DEFAULT_POSITIONS = {
    "LSM":   {LSM_H: 2.643, LSM_V: 22.603},
    "MS":    {MS_H: 1.8, MS_V: 33.62},
    "ATCP":  {ATCP: 65.98},
    "ATCFW": {ATCFW: 1},
    "ATCL":  {ATCL: 7.15},
}

STAGES = [stage for positions in DEFAULT_POSITIONS.values() for stage in positions]

MOVE_MODES = ["prompt", "auto-move", "do-not-move"]


# =============================================================================
# The check
# =============================================================================

def check_default_positions(verbose=False, move_mode="prompt", client=None):
    """Check every module against its default position, moving it if allowed.

    Args:
        verbose: print each stage's position as it is checked.
        move_mode: what to do when a stage is out of position:
            'prompt'       ask each time
            'auto-move'    move it
            'do-not-move'  leave it and report it
        client: an open libby client to use; one is opened if not given.

    Returns:
        (all_in_pos, modules_in_pos, final_positions)
        all_in_pos      : True if every module is in position
        modules_in_pos  : {module: True/False}
        final_positions : {module: {keyword: position}}, e.g.
                          {"MS": {"positionvalueh": 1.8, "positionvaluev": 33.62}}

    Raises:
        NotReady: a daemon is disconnected or a stage is not homed.
        MoveError: a move was refused, timed out, or ended out of tolerance.
    """
    if move_mode not in MOVE_MODES:
        raise ValueError(f"move_mode must be one of {MOVE_MODES}, not {move_mode!r}")
    if client is None:
        with connect(SCRIPT_NAME) as own_client:
            return check_default_positions(verbose, move_mode, own_client)

    preflight(client, STAGES)

    modules_in_pos = {}
    final_positions = {}
    for module, positions in DEFAULT_POSITIONS.items():
        modules_in_pos[module] = True
        final_positions[module] = {}
        for stage, target in positions.items():
            keyword = stage.position.rsplit(".", 1)[1]
            in_position, position = at_target(client, stage, target)
            if verbose:
                print(f"{stage.name:>16s} is at {position} (default {target})")

            if not in_position:
                print(f"** {stage.name} is at {position}, more than "
                      f"{stage.tolerance} from its default {target}")
                if should_move(stage, target, move_mode):
                    position = move_and_verify(client, stage, target)
                    print(f"   moved {stage.name} to {position}")
                else:
                    print(f"   NOT moving {stage.name}")
                    modules_in_pos[module] = False

            final_positions[module][keyword] = position

    return all(modules_in_pos.values()), modules_in_pos, final_positions


def should_move(stage, target, move_mode):
    """Decide whether to move an out-of-position stage, asking if prompting."""
    if move_mode == "auto-move":
        return True
    if move_mode == "do-not-move":
        return False
    while True:
        answer = input(f"   Move {stage.name} to {target}? [y/n] ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("   Please answer y or n.")


def format_positions(positions):
    """Format one module's positions: '7.150', or '(1.800, 33.620)' for two axes."""
    text = ", ".join(f"{value:0.3f}" for value in positions)
    return f"({text})" if len(positions) > 1 else text


# =============================================================================
# Command line
# =============================================================================

def main():
    """Run the check from the command line and print the summary."""
    defaults = "\n".join(f"  {module:<7s} : {format_positions(list(positions.values()))}"
                         for module, positions in DEFAULT_POSITIONS.items())
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n", maxsplit=1)[0].strip()
        + f"\n\nDefault positions:\n{defaults}",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="print every stage as it is checked")
    parser.add_argument("-m", "--move-mode", default="prompt", choices=MOVE_MODES,
                        help="what to do when a module is not in position "
                             "(default: prompt)")
    parser.add_argument("--no-summary", action="store_true",
                        help="do not print the final positions")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(message)s")

    with connect(SCRIPT_NAME) as client:
        try:
            all_in_pos, modules_in_pos, final_positions = check_default_positions(
                args.verbose, args.move_mode, client)
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

    if all_in_pos:
        print("\nSUCCESS: all libby-enabled modules are in position.")
    else:
        for module, in_pos in modules_in_pos.items():
            if not in_pos:
                print(f"\nWARNING: {module} is NOT in position")

    if not args.no_summary:
        print("\nFinal module positions:")
        for module, positions in final_positions.items():
            print(f"  {module:<7s} : {format_positions(list(positions.values()))}")

    return 0 if all_in_pos else 1


if __name__ == "__main__":
    sys.exit(main())
