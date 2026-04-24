#!/usr/bin/env python3

import numpy as np
import time
import argparse
from pathlib import Path

import redPM_cmds
import SimulateFieldPoint
import FAM_Scans
import FSM_Scans
import Fitter

# -------------------------
# Saving properties
# -------------------------
SAVE_DIR = "/home/hsdev/dechever/AIT_Verification_Data/Experiment5_FOVCouplingCheck/Experiment5c_FSM"

# -------------------------
# Mask selection
# -------------------------
MASK_TYPE = "Keck"  # One of: "Circ" or "Keck"

# -------------------------
# FSM Settings
# -------------------------
FSM_CENTER = np.array([17.5, 17.5])
LSM_TO_FSM_RATIO = 6.12 / 2.2   # [FSM mrad / LSM mm]

# -------------------------
# FAM selection
# -------------------------
# USER SETTINGS
FAM_TO_USE = 'blue'  # One of: "red" or "blue"

# Make sure we connect to the correct FAM...
if 'r' in FAM_TO_USE.lower():
    print("*** Using RED FAM ***")
    FAM_Scans.SETTINGS_FILENAME = "/home/hsdev/dechever/settings_FEI_XD24494_20250828.txt"
    FAM_Scans.COM_PORT = "/dev/ttyRedFAM"
elif 'b' in FAM_TO_USE.lower():
    print("*** Using BLUE FAM ***")
    FAM_Scans.SETTINGS_FILENAME = "/home/hsdev/dechever/settings_FEI_XD24508_20250902.txt"
    FAM_Scans.COM_PORT = "/dev/ttyBlueFAM"
else:
    raise ValueError("'FAM_TO_USE' must be one of 'red' or 'blue'")
FAM_Scans.controller.setCOMPort(FAM_Scans.COM_PORT)

# -------------------------
# Helpers
# -------------------------
def wait_for_fam_motion():
    """Block until all FAM axes stop or timeout."""
    t0 = time.time()
    while (FAM_Scans.xAxis.isMotorOn() or
           FAM_Scans.yAxis.isMotorOn() or
           FAM_Scans.zAxis.isMotorOn()):
        if (time.time() - t0) > FAM_Scans.MOV_TIMEOUT:
            FAM_Scans.controller.stopMovements()
            print(f"\n** WARN: Move did not complete within {FAM_Scans.MOV_TIMEOUT} s — stopping move attempt but proceeding with code")
            break
        time.sleep(0.05)

def wait_for_fam_disconnect(timeout = 3):
    """Block until the FAM reports that it's disconnected"""
    t0 = time.time()
    while (not FAM_Scans.controller.getCommunication().stop_thread) and FAM_Scans.controller.getCommunication().ser.is_open:
        if (time.time() - t0) > timeout:
            print(f"\n** WARN: Seems like we did not disconnect from the controller within {timeout} s, moving on anyway")
            break
        time.sleep(0.05)

def wait_for_fam_connect(timeout = 3):
    """Block until the FAM reports that it connected"""
    t0 = time.time()
    while FAM_Scans.controller.getCommunication().stop_thread and (not FAM_Scans.controller.getCommunication().ser.is_open):
        if (time.time() - t0) > timeout:
            print(f"\n** WARN: Seems like we did not connect to the controller within {timeout} s, moving on anyway")
            break
        time.sleep(0.05)

def vprint(message, verbose):
    if verbose:
        print(message)

def move_fsm(new_pos, verbose=False):
    """Move the FSM to a specific position"""
    try:
        vprint("** Connecting to FSM controller", verbose=verbose)
        FSM_Scans.dev.ConnectTCPIP(ipaddress= FSM_Scans.IPADDRESS, ipport = FSM_Scans.IPPORT)
        time.sleep(1)
        FSM_Scans.dev.MOV({FSM_Scans.xAx:new_pos[0], FSM_Scans.yAx:new_pos[1]})

        # No need to wait for move to complete since the FSM moves so ridiculously fast...

        print(f"FSM set to: ({new_pos[0]:0.5f}, {new_pos[1]:0.5f}) ")
    finally:
        # Disconnect from FSM
        FSM_Scans.dev.CloseConnection()
        # There is some sort of race-condition on the disconnect, so let's give it a moment for the FSM to disconnect....
        time.sleep(1)
        vprint("** Disconnected from FSM", verbose=verbose)

def move_fam(new_pos, verbose=False):
    """Move the FAM to a specific position"""
    try:
        vprint("** Connecting to FAM controller", verbose=verbose)
        FAM_Scans.controller.start(external_settings_default = FAM_Scans.SETTINGS_FILENAME, do_reset=False, send_settings=False)
        wait_for_fam_connect()
        if len(new_pos) > 1:
            # Got a fully-qualified 3-axis position, so move all 3 axes
            FAM_Scans.xAxis.setDPOS(new_pos[0], outputToConsole=False)
            FAM_Scans.yAxis.setDPOS(new_pos[1], outputToConsole=False)
            FAM_Scans.zAxis.setDPOS(new_pos[2], outputToConsole=False)
        else:
            FAM_Scans.zAxis.setDPOS(new_pos[0], outputToConsole=False)
        wait_for_fam_motion()
    finally:
        # Disconnect from FAM
        FAM_Scans.controller.stopMovements()
        FAM_Scans.controller.stop(isPrintEnd=False)
        wait_for_fam_disconnect()
        vprint("** Disconnected from FAM", verbose=verbose)

def prompt_normalization():
    """
    Prompt user to take manual normalization measurement
    """
    print("\n-- Moving FAM to correct position for normalization measurement")
    move_fam([-7.5], verbose=False)
    time.sleep(1)
    print(" ====== PLEASE TAKE MANUAL NORMALIZATION MEASUREMENT NOW ======")
    isdone = input("type 'done' once done; this will allow the code to proceed:\n")
    while "done" not in isdone.lower():
        print(f"** Sorry, '{isdone}' is not recognized...")
        isdone = input("type 'done' once done; this will allow the code to proceed:\n")

# -------------------------
# Main
# -------------------------
def main(separation, nread, settle_time=0.2, verbose=False, save_flnm=None):

    results = {}
    raw_data = {}
    optimizer_data = {}

    def measure(label, start_pos):
        """
        Center the PSF onto the fiber and then hold, reading PD at that position
        """
        print("\n-- Large FOV scan to find fiber tip")
        pd_readsXY, center_coordsXY, deltasXY, _, _ = FSM_Scans.redPM_TT(
            start=-0.3, stop=0.3, nsteps=15, center_coords=start_pos, pause=0.1, nread=50, verbose=False)
        peak_coords, _, _, _ = Fitter.plot_2D_FAMScan_with_gaussFit(pd_readsXY, center_coordsXY.tolist()+[np.nan], deltasXY)
        print("\n-- Smaller FOV scan to center well before focus scan")
        pd_readsXY, center_coordsXY, deltasXY, _, _ = FSM_Scans.redPM_TT(
            start=-0.08, stop=0.08, nsteps=15, center_coords=peak_coords[:2], pause=0.1, nread=50, verbose=False)
        peak_coords, _, _, _ = Fitter.plot_2D_FAMScan_with_gaussFit(pd_readsXY, list(center_coordsXY)+[np.nan], deltasXY)
        print("\n-- Moving to optimized XY position on FSM")
        move_fsm(peak_coords, verbose=verbose)
        print("\n-- Focus scan (using FAM)")
            # center_coords = None makes it so we use the current FAM position as the center point
        pd_readsZ, center_coordsZ, deltasZ = FAM_Scans.redPM_Z(
            -0.2, 0.2, 71, center_coords=None, pause=0.1, nread=100)
        peak_coordsZ, _, _, _ = Fitter.plot_1D_FAMScan_with_gaussFit(pd_readsZ, center_coordsZ, deltasZ)
        print("\n-- Moving to optimized focus position ---")
        wait_for_fam_disconnect()
        move_fam(peak_coordsZ, verbose=verbose)
        print("\n-- Final small FOV, fine XY-only scan")
        pd_readsXY, center_coordsXY, deltasXY, _, _ = FSM_Scans.redPM_TT(
            start=-0.035, stop=0.035, nsteps=15, center_coords=peak_coords[:2], pause=0.1, nread=50, verbose=False)
        peak_coords, _, _, _ = Fitter.plot_2D_FAMScan_with_gaussFit(pd_readsXY, list(center_coordsXY)+[np.nan], deltasXY)

        print("\n--- Moving to final optimized FSM position")
        move_fsm(peak_coords, verbose=verbose)

        print("\n--- Measuring at optimized position ---")
        time.sleep(settle_time)
        with redPM_cmds.redPM_cmds() as pd:
            vals = pd.readN(nread) * redPM_cmds.redPM_cmds.PD_uW_CONVERSION

        raw_data[label] = vals
        results[label] = (np.mean(vals), np.std(vals))

        optimizer_data[label] = {
            "start_pos": np.array(start_pos),
            "peak_coords": np.array(peak_coords[:2]),
            "pd_readsXY": np.array(pd_readsXY),
            "deltasXY": np.array(deltasXY),
            "center_coordsXY": np.array(center_coordsXY),
            "pd_ReadsZ": np.array(pd_readsZ),
            "deltasZ": np.array(deltasZ)
        }

        print(f"{label:>12s}: {results[label][0]:.4f} +/- {results[label][1]:.4f} uW")

        # Prompt user to take normalization measurement!
        prompt_normalization()

    # ============================================================
    # Center point (initial)
    # ============================================================
    print("\n--- Moving to on-center ---")
    dx, dy = 0.0, 0.0
    SimulateFieldPoint.main(dx, dy, verbose=verbose, mask=MASK_TYPE)
    # Make sure FAM is set to place the fiber on-axis
    _, start_pos = SimulateFieldPoint.move_FAM(0, 0, FAM=FAM_TO_USE, ref_mode="center", verbose=False, fib_type='SMF')
    # Make sure FSM is set to on-axis
    move_fsm(FSM_CENTER, verbose=verbose)
    measure("center_1", FSM_CENTER)

    # ============================================================
    # Circular field points
    # ============================================================
    print("\n--- Circular field points ---")
    angles = np.linspace(0, 2*np.pi, 2, endpoint=False)

    for i, theta in enumerate(angles):
        dx = separation * np.cos(theta)
        dy = separation * np.sin(theta)
        label = f"circ_{i}_dx{dx:+.3f}_dy{dy:+.3f}"

        print(f"\n--- Moving to {label} ---")
        try:
            SimulateFieldPoint.main(dx, dy, verbose=verbose, mask=MASK_TYPE)
            # Make sure FAM is set to place the fiber on-axis
            _, start_pos = SimulateFieldPoint.move_FAM(0, 0, FAM=FAM_TO_USE, ref_mode="center", verbose=False, fib_type='SMF')
            # Move FSM to re-center the PSF
                # NOTE: the FSM X/Y axes are flipped compared to the LSM
            fsm_dx = dy*LSM_TO_FSM_RATIO
            fsm_dy = dx*LSM_TO_FSM_RATIO
            start_pos = FSM_CENTER+[fsm_dx, fsm_dy]
            move_fsm(start_pos, verbose=verbose)
            measure(label, start_pos)
        except Exception as e:
            print(f"ERROR moving to {label}: {e}")
            raise

    '''
    # ============================================================
    # Square corner points (±sep, ±sep)
    # ============================================================
    print("\n--- Square corner field points ---")
    corners = [
        (+separation, +separation),
        (+separation, -separation),
        (-separation, +separation),
        (-separation, -separation),
    ]

    for i, (dx, dy) in enumerate(corners):
        label = f"corner_{i}_dx{dx:+.3f}_dy{dy:+.3f}"

        print(f"\n--- Moving to {label} ---")
        try:
            SimulateFieldPoint.main(dx, dy, verbose=verbose, mask=MASK_TYPE)
            # Make sure FAM is set to place the fiber on-axis
            _, start_pos = SimulateFieldPoint.move_FAM(0, 0, FAM=FAM_TO_USE, ref_mode="center", verbose=False, fib_type='SMF')
            # Move FSM to re-center the PSF
                # NOTE: the FSM X/Y axes are flipped compared to the LSM
            fsm_dx = dy*LSM_TO_FSM_RATIO
            fsm_dy = dx*LSM_TO_FSM_RATIO
            start_pos = FSM_CENTER+[fsm_dx, fsm_dy]
            move_fsm(start_pos, verbose=verbose)
            measure(label, start_pos)
        except Exception as e:
            print(f"ERROR moving to {label}: {e}")
            raise
    '''

    # ============================================================
    # Return to center (final)
    # ============================================================
    print("\n--- Returning to on-center ---")
    dx, dy = 0.0, 0.0
    SimulateFieldPoint.main(dx, dy, verbose=verbose, mask=MASK_TYPE)
    # Make sure FAM is set to place the fiber on-axis
    _, start_pos = SimulateFieldPoint.move_FAM(0, 0, FAM=FAM_TO_USE, ref_mode="center", verbose=False, fib_type='SMF')
    # Make sure FSM is set to on-axis
    move_fsm(FSM_CENTER, verbose=verbose)
    measure("center_2", FSM_CENTER)

    # Drift check
    c1 = results["center_1"][0]
    c2 = results["center_2"][0]
    print(f"\nCenter drift: {c2 - c1:+.4f} uW")

    # ============================================================
    # Save data
    # ============================================================
    outdir = Path(SAVE_DIR)
    outdir.mkdir(parents=True, exist_ok=True)

    stem = f"{FAM_TO_USE}FAM_{MASK_TYPE}Mask_sep_{separation:.3f}mm"
    outname = outdir / f"{stem}.npz"

    i = 1
    while outname.exists():
        outname = outdir / f"{stem}_{i}.npz"
        i += 1

    np.savez(outname, separation_mm=separation, nread=nread, raw_pd=raw_data, stats=results, optimizer=optimizer_data)

    print(f"\nSaved raw data to {outname.resolve()}")


# -------------------------
# CLI entry point
# -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Field scan using FSM to recenter PSF")
    parser.add_argument("separation", type=float, help="Separation in mm at the LSM")
    parser.add_argument("--nread", type=int, default=1000, help="Number of PD samples per position")
    parser.add_argument("--settle-time", type=float, default=2.0, help="Settle time after moves [s]")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose motion output")

    args = parser.parse_args()

    main(separation=args.separation, nread=args.nread, settle_time=args.settle_time, verbose=args.verbose)

    input("Press any key to close this terminal (this lets you review the plots)")
