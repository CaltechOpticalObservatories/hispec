#!/usr/bin/env python3

import numpy as np
import time
import argparse
import sys

from pipython import GCSDevice, GCSError

# -------------------------
# Configuration
# -------------------------
IPADDRESS = '192.168.29.100'
IPPORT_ILS = 10003
IPPORT_MS  = 10005

# Softcoded center positions
ILS_CENTER = np.array([2.643, 22.603])   # (X, Y)
MS_CENTER  = {  'keck' : np.array([1.800, 33.620]),
                'circ' : np.array([1.600, 61.700])}     
FAM_RED_CENTER  = {     'mmf' : np.array([-22.835, -0.078]),
                        'smf' : np.array([7.3335, -0.1658])}    
FAM_RED_Z_CENTER  = {   'mmf' : 7.700,
                        'smf' : 6.697 }

FAM_BLUE_CENTER = {     'mmf' : np.array([-22.795, -0.035]),
                        'smf' : np.array([-7.8088, 0.0246])}
FAM_BLUE_Z_CENTER = {   'mmf' : 9.150, 
                        'smf' : 9.0443 }

# Relevant optical ratios
OAP_EFL = 180   # [mm] EFL of the OAP
MS_SCALE = 92.6 / 182.6   # ~0.507 -- ratio between MS and ILS motion
FAM_RED_SCALE  = 34.2 / OAP_EFL  # ~0.19 -- ratio between red fiber focal plane and ILS plane
FAM_BLUE_SCALE = 47.3 / OAP_EFL  # ~0.26 -- ratio between blue fiber focal plane and ILS plane

# -------------------------
# Software limits (relative to center)
# -------------------------
ILS_MAX_OFS = 2.35
ILS_OFFSET_LIMITS = {
    "X": (-ILS_MAX_OFS, ILS_MAX_OFS),
    "Y": (-ILS_MAX_OFS, ILS_MAX_OFS),
}

MS_MAX_OFS = 1.2
MS_OFFSET_LIMITS = {
    "X": (-MS_MAX_OFS, MS_MAX_OFS),
    "Y": (-MS_MAX_OFS, MS_MAX_OFS),
}

# FAM limits are in *FAM stage coordinates*, not field coordinates
FAM_RED_MAX_OFS = 0.7
FAM_BLUE_MAX_OFS = 0.7

FAM_RED_OFFSET_LIMITS = {
    "X": (-FAM_RED_MAX_OFS, FAM_RED_MAX_OFS),
    "Y": (-FAM_RED_MAX_OFS, FAM_RED_MAX_OFS),
}

FAM_BLUE_OFFSET_LIMITS = {
    "X": (-FAM_BLUE_MAX_OFS, FAM_BLUE_MAX_OFS),
    "Y": (-FAM_BLUE_MAX_OFS, FAM_BLUE_MAX_OFS),
}

# Motion timeout for FAM [s]
MOV_TIMEOUT = 20.0

# -------------------------
# Helper: verbose printing
# -------------------------
def vprint(msg, verbose=False):
    if verbose:
        print(msg)

# -------------------------
# Helper: offset limit check
# -------------------------
def check_offset_limits(offset, limits, label):
    for i, axis in enumerate(("X", "Y")):
        lo, hi = limits[axis]
        if not (lo <= offset[i] <= hi):
            raise ValueError(
                f"{label} {axis} offset {offset[i]:.4f} "
                f"outside limits [{lo:.4f}, {hi:.4f}]"
            )

# =========================
# Main logic - Moves ILS and MS to set source point to field position
# =========================
def main(dx, dy, dry_run=False, verbose=False, mask='keck'):

    # -------------------------
    # Compute offsets and targets
    # -------------------------
    ils_offset = np.array([dx, dy])
    ms_offset  = MS_SCALE * ils_offset

    ils_target = ILS_CENTER + ils_offset
    # Parse selected mask to use as the center point
    try:  ms_center = MS_CENTER[mask.lower()]
    except KeyError as e:
        raise ValueError(f"Invalid mask ('{mask}') provided, must be one of {MS_CENTER.keys()}") from e
    ms_target  = ms_center  + ms_offset

    # -------------------------
    # Enforce software limits
    # -------------------------
    try:
        check_offset_limits(ils_offset, ILS_OFFSET_LIMITS, "ILS")
        check_offset_limits(ms_offset,  MS_OFFSET_LIMITS,  "MS")
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1

    if dry_run:
        print("DRY RUN — no motion will be executed")

    # -------------------------
    # Move ILS
    # -------------------------
    vprint("Connecting to ILS...", verbose)
    with GCSDevice() as ILS_X:
        ILS_X.OpenTCPIPDaisyChain(ipaddress=IPADDRESS, ipport=IPPORT_ILS)
        ILS_X.ConnectDaisyChainDevice(1, ILS_X.dcid)
        vprint(f"- Connected to ILS X: {ILS_X.qIDN().strip()}", verbose)

        with GCSDevice() as ILS_Y:
            ILS_Y.ConnectDaisyChainDevice(2, ILS_X.dcid)
            vprint(f"- Connected to ILS Y: {ILS_Y.qIDN().strip()}", verbose)

            print(
                f"ILS : "
                f"({ILS_X.qPOS()['1']:.4f}, {ILS_Y.qPOS()['1']:.4f}) -> "
                f"({ils_target[0]:.4f}, {ils_target[1]:.4f})"
            )

            if not dry_run:
                ILS_X.MOV({'1': ils_target[0]})
                ILS_Y.MOV({'1': ils_target[1]})

                while ILS_X.IsMoving()['1'] or ILS_Y.IsMoving()['1']:
                    time.sleep(0.2)

                # Final sleep to ensure device gets to where we want it
                time.sleep(0.2)
                print(
                    f"* ILS final: "
                    f"({ILS_X.qPOS()['1']:.4f}, {ILS_Y.qPOS()['1']:.4f})"
                )

    # -------------------------
    # Move MS
    # -------------------------
    vprint("Connecting to MS...", verbose)
    with GCSDevice() as MS_Y:
        MS_Y.OpenTCPIPDaisyChain(ipaddress=IPADDRESS, ipport=IPPORT_MS)
        MS_Y.ConnectDaisyChainDevice(1, MS_Y.dcid)
        vprint(f"- Connected to MS Y: {MS_Y.qIDN().strip()}", verbose)

        with GCSDevice() as MS_X:
            MS_X.ConnectDaisyChainDevice(2, MS_Y.dcid)
            vprint(f"- Connected to MS X: {MS_X.qIDN().strip()}", verbose)

            print(
                f"MS  : "
                f"({MS_X.qPOS()['1']:.4f}, {MS_Y.qPOS()['1']:.4f}) -> "
                f"({ms_target[0]:.4f}, {ms_target[1]:.4f})"
            )

            if not dry_run:
                MS_X.MOV({'1': ms_target[0]})
                MS_Y.MOV({'1': ms_target[1]})

                while MS_X.IsMoving()['1'] or MS_Y.IsMoving()['1']:
                    time.sleep(0.2)

                # Final sleep to ensure device gets to where we want it
                time.sleep(0.2)
                print(
                    f"* MS final: "
                    f"({MS_X.qPOS()['1']:.4f}, {MS_Y.qPOS()['1']:.4f})"
                )

    if dry_run:
        print("DRY RUN — no motion executed")

    return 0

# =========================
# FAM Plane Logic - Moves FAM stages to match field point shift
# =========================
def move_FAM(dx, dy, FAM=None, ref_mode="center", dry_run=False, verbose=False, fib_type='smf'):

    # Import Xeryon library, which will be needed for moving the FAM
    from hispec.util.xeryon import Xeryon, Stage

    # -------------------------
    # Validate the selected FAM
    # -------------------------
    if FAM is None:
        raise ValueError("'FAM' must be provided as either 'red' or 'blue'")
    if 'r' in FAM.lower():
        FAM_LABEL = "Red FAM"
        FAM_SCALE = FAM_RED_SCALE
        FAM_LIMITS = FAM_RED_OFFSET_LIMITS
        SETTINGS_FILENAME = "/home/hsdev/dechever/settings_FEI_XD24494_20250828.txt"
        COM_PORT = "/dev/ttyRedFAM"
        try: 
            FAM_CENTER = FAM_RED_CENTER[fib_type.lower()]
            FAM_Z_CENTER = FAM_RED_Z_CENTER[fib_type.lower()]
        except KeyError as e:
            raise ValueError(f"Invalid fib_type ('{fib_type}') provided, must be one of {FAM_RED_CENTER.keys()}") from e
    elif 'b' in FAM.lower():
        FAM_LABEL = "Blue FAM"
        FAM_SCALE = FAM_BLUE_SCALE
        FAM_LIMITS = FAM_BLUE_OFFSET_LIMITS
        SETTINGS_FILENAME = "/home/hsdev/dechever/settings_FEI_XD24508_20250902.txt"
        COM_PORT = "/dev/ttyBlueFAM"
        try: 
            FAM_CENTER = FAM_BLUE_CENTER[fib_type.lower()]
            FAM_Z_CENTER = FAM_BLUE_Z_CENTER[fib_type.lower()]
        except KeyError as e:
            raise ValueError(f"Invalid fib_type ('{fib_type}') provided, must be one of {FAM_BLUE_CENTER.keys()}") from e
    else:
        raise ValueError("'FAM' must be one of 'red' or 'blue'")

    # -------------------------
    # Compute requested delta (always the same)
    # -------------------------
    dy = -dy    # NOTE: the FAM y-axis is flipped compared to the camera
    fam_delta = np.array([dx, dy]) * FAM_SCALE

    # -------------------------
    # Enforce software limits on delta from center
    # -------------------------
    try:
        check_offset_limits(fam_delta, FAM_LIMITS, FAM_LABEL)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1, [np.nan, np.nan, np.nan]

    if dry_run:
        print("DRY RUN — no motion will be executed")

    # -------------------------
    # Connect to controller
    # -------------------------
    vprint(f"Connecting to {FAM_LABEL}...", verbose)
    controller = Xeryon(COM_port=COM_PORT, baudrate=115200)

    # (letters are defined in the settings file)
    yAxis = controller.addAxis(Stage.XLS_5_3N, "A")
    xAxis = controller.addAxis(Stage.XLS_5_3N, "B")
    zAxis = controller.addAxis(Stage.XLS_5_3N, "C")

    # Helpful letter-to-axis mapping for printing
    LETTER_MAP = {"A": "Y", "B": "X", "C": "Z"}
    ordered_axis_list = [xAxis, yAxis, zAxis]

    controller_started = False
    try:
        controller.start(external_settings_default=SETTINGS_FILENAME, do_reset=False, send_settings=False)
        controller_started = True
        time.sleep(3)
        vprint(f"- Connected to {FAM_LABEL} on {COM_PORT}", verbose)

        # -------------------------
        # Check reference state - we assume if they are referenced, then controller is initialized correctly
        # -------------------------
        for axis in ordered_axis_list:
            axis_letter = axis.getLetter()
            axis_dir = LETTER_MAP[axis_letter]
            if not axis.isEncoderValid():
                raise RuntimeError(
                    f"{axis_dir} Axis seems to not be referenced. "
                    f"Please reference FAM and try again."
                )

        # -------------------------
        # Read current positions
        # -------------------------
        x0 = xAxis.getDPOS()
        y0 = yAxis.getDPOS()
        z0 = zAxis.getDPOS()

        if ref_mode == "center":
            xt, yt = FAM_CENTER + fam_delta
            zt = FAM_Z_CENTER
            ref_label = "center"
        elif ref_mode == "current":
            xt = x0 + fam_delta[0]
            yt = y0 + fam_delta[1]
            zt = z0
            ref_label = "current"
        else:
            raise ValueError("ref_mode must be 'center' or 'current'")

        print(
            f"{FAM_LABEL} ({ref_label}-referenced): "
            f"({x0:.4f}, {y0:.4f}, {z0:.4f}) -> "
            f"({xt:.4f}, {yt:.4f}, {zt:.4f})"
        )

        # -------------------------
        # Move
        # -------------------------
        if not dry_run:
            xAxis.setDPOS(xt)
            yAxis.setDPOS(yt)
            zAxis.setDPOS(zt)

            # Wait to make sure all stages have settled in position
            t0 = time.time()
            while xAxis.isMotorOn() or yAxis.isMotorOn() or zAxis.isMotorOn():
                if (time.time() - t0) > MOV_TIMEOUT:
                    controller.stopMovements()
                    print(
                        f"\n** WARN: Move did not complete within {MOV_TIMEOUT} seconds... "
                        f"stopping this move attempt"
                    )
                    break
                time.sleep(0.05)

            # Final readback
            xf = xAxis.getEPOS()
            yf = yAxis.getEPOS()
            zf = zAxis.getEPOS()
            print(
                f"* {FAM_LABEL} final: "
                f"({xf:.4f}, {yf:.4f}, {zf:.4f})"
            )

    finally:
        if controller_started:
            vprint("Disconnecting from Xeryon...", verbose)
            controller.stopMovements()
            controller.stop()
            vprint("...Disconnected", verbose)

    return 0, [xt, yt, zt]

# =========================
# Command-line entry point
# =========================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Move ILS and MS by a field offset")
    parser.add_argument("dx", type=float, help="Field offset in X (ILS) [mm]")
    parser.add_argument("dy", type=float, help="Field offset in Y (ILS) [mm]")
    parser.add_argument("--fam", choices=["red", "blue"],
                        help="Also move the specified FAM (red or blue)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print motions but do not move stages")
    parser.add_argument("--fam-ref", choices=["center", "current"], default="center",
                        help="FAM reference frame: 'center' (default) or 'current'")
    parser.add_argument("--mask", choices=["keck", "circ"], default="keck",
                        help="Mask to use: 'keck' (default) or 'circ'")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output (debug / engineering info)")
    args = parser.parse_args()

    result = main(dx=args.dx, dy=args.dy, dry_run=args.dry_run, verbose=args.verbose, mask=args.mask)

    if (not result) and (args.fam is not None):
        fam_result, _ = move_FAM(dx=args.dx, dy=args.dy, FAM=args.fam,
                               ref_mode=args.fam_ref,
                               dry_run=args.dry_run, verbose=args.verbose)
        result = result or fam_result

    sys.exit(result)
