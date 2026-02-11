#!/usr/bin/env python3

import numpy as np
import time
import argparse
from pathlib import Path

import redPM_cmds
import SimulateFieldPoint
import FAM_Scans
import Fitter

# -------------------------
# Saving properties
# -------------------------
SAVE_DIR = "/home/hsdev/dechever/AIT_Verification_Data/Experiment5_FOVCouplingCheck"
MASK_TYPE = "Keck"  # "Circ" or "Keck" (used only for filename formatting)

# -------------------------
# FAM selection
# -------------------------
# USER SETTINGS
FAM_TO_USE = 'red'  # One ofL "red" or "blue"
FAM_FIBER  = 'smf'  # One of: "mmf" or "smf"
IS_RUN_AUTOMOPT = False      # Flag to select if auto-optimizer should be used for SMF case

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
# Auto-optimizer defaults
# -------------------------
DEF_DELTAS = [0.007, 0.007, 0.01]
DEF_MAX_REL_MOVE = [0.1, 0.1, 0.5]  # [0.02, 0.02, 0.06]
DEF_PAUSE = 0.1
DEF_MAX_ITERS = 12
DEF_STEP_TOL = 1e-4
DEF_ETA_TOL = 1e-4
DEF_XY_SIZE = 0.003
DEF_XY_POINTS = 15
DEF_XY_QUICKSIZE = 0.017
DEF_XY_QUICKPOINTS = 13

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

# -------------------------
# Main
# -------------------------
def main(separation, nread, settle_time=0.2, verbose=False, save_flnm=None):

    results = {}
    raw_data = {}
    optimizer_data = {}

    def measure(label, start_pos):
        """
        Center the fiber on the PSF and then hold, reading PD at that position
        """
        if 'sm' in FAM_FIBER.lower():
            if IS_RUN_AUTOMOPT:
                # Use auto-optimizer routine to try to center on the SMF
                print("\n--- SMF and Auto-optimizer requested for optimization ---")

                # Call signature:
                # redPM_automated_tuning(start_pos, deltas, max_rel_move, nread, pause,
                #                        max_iters, step_tol, eta_tol, Zscan_size,
                #                        Zscan_points, XY_size, XY_points, 
                #                        XY_quick_size, XY_quick_points)
                (peak_coords, _, _, _, _, _, 
                pd_readsXY, deltasXY, center_coordsXY, _) = FAM_Scans.redPM_automated_tuning(
                        start_pos=start_pos,
                        deltas=DEF_DELTAS,
                        max_rel_move=DEF_MAX_REL_MOVE,
                        pause=DEF_PAUSE,
                        max_iters=DEF_MAX_ITERS,
                        step_tol=DEF_STEP_TOL,
                        eta_tol=DEF_ETA_TOL,
                        XY_size=DEF_XY_SIZE,
                        XY_points=DEF_XY_POINTS,
                        XY_quick_size=DEF_XY_QUICKSIZE,
                        XY_quick_points=DEF_XY_QUICKPOINTS
                    )
            else:
                print("\n--- SMF and Simple Raster Scans requested for optimization ---")
                print("\n-- Large FOV scan to find PSF")
                pd_readsXY, center_coordsXY, deltasXY, _, _ = FAM_Scans.redPM_XY(
                    start=-0.05, stop=0.05, nsteps=15, center_coords=start_pos, pause=0.1, nread=50)
                peak_coords, _, _, _ = Fitter.plot_2D_FAMScan_with_gaussFit(pd_readsXY, center_coordsXY, deltasXY)
                print("\n-- Smaller FOV scan to center well before focus scan")
                pd_readsXY, center_coordsXY, deltasXY, _, _ = FAM_Scans.redPM_XY(
                    start=-0.01, stop=0.01, nsteps=15, center_coords=peak_coords, pause=0.1, nread=50)
                peak_coords, _, _, _ = Fitter.plot_2D_FAMScan_with_gaussFit(pd_readsXY, center_coordsXY, deltasXY)
                print("\n-- Focus scan")
                pd_readsZ, center_coordsZ, deltasZ = FAM_Scans.redPM_Z(
                    -0.2, 0.2, 71, center_coords=peak_coords, pause=0.1, nread=100)
                peak_coordsZ, _, _, _ = Fitter.plot_1D_FAMScan_with_gaussFit(pd_readsZ, center_coordsZ, deltasZ)
                print("\n-- Final small FOV, fine XY-only scan")
                pd_readsXY, center_coordsXY, deltasXY, _, _ = FAM_Scans.redPM_XY(
                    start=-0.005, stop=0.005, nsteps=15, center_coords=peak_coordsZ, pause=0.1, nread=50)
                peak_coords, _, _, _ = Fitter.plot_2D_FAMScan_with_gaussFit(pd_readsXY, center_coordsXY, deltasXY)

        if 'mm' in FAM_FIBER.lower():
            # Use basic raster scans to center on the MMF
            print("\n--- MMF requested - using raster scans for optimization")
            # First do a large FOV, low-res scan to find the fiber tip
            print("\n-- Quick Large FOV XY-only scan")
            pd_readsXY, center_coordsXY, deltasXY, _, _ = FAM_Scans.redPM_XY(
                start=-0.2, stop=0.2, nsteps=11, center_coords=start_pos, pause=0.1, nread=50 )
            # Use the gaussian fitter to roughly-center on the PSF
            peak_coords, _, _, _ = Fitter.plot_2D_FAMScan_with_gaussFit(pd_readsXY, center_coordsXY, deltasXY)
            print("\n-- Smaller FOV, finer XY-only scan")
            pd_readsXY, center_coordsXY, deltasXY, _, _ = FAM_Scans.redPM_XY(
                start=-0.075, stop=0.075, nsteps=15, center_coords=peak_coords, pause=0.1, nread=50)
            peak_coords, _, _, _ = Fitter.plot_2D_FAMScan_with_gaussFit(pd_readsXY, center_coordsXY, deltasXY)
            
        print("Giving a moment for controller to disconnect correctly")
        wait_for_fam_disconnect()
        print("\n--- Moving to optimized position ---")
        FAM_Scans.controller.start(external_settings_default = FAM_Scans.SETTINGS_FILENAME, do_reset=False, send_settings=False)
        wait_for_fam_connect()
        FAM_Scans.xAxis.setDPOS(peak_coords[0], outputToConsole=False)
        FAM_Scans.yAxis.setDPOS(peak_coords[1], outputToConsole=False)
        FAM_Scans.zAxis.setDPOS(peak_coords[2], outputToConsole=False)
        wait_for_fam_motion()

        # Disconnect from FAM
        FAM_Scans.controller.stopMovements()
        FAM_Scans.controller.stop(isPrintEnd=False)
        wait_for_fam_disconnect()
        print("** Disconnected from FAM")

        print("\n--- Measuring at optimized position ---")
        time.sleep(settle_time)
        with redPM_cmds.redPM_cmds() as pd:
            vals = pd.readN(nread) * redPM_cmds.redPM_cmds.PD_uW_CONVERSION

        raw_data[label] = vals
        results[label] = (np.mean(vals), np.std(vals))

        optimizer_data[label] = {
            "start_pos": np.array(start_pos),
            "peak_coords": np.array(peak_coords),
            "pd_readsXY": np.array(pd_readsXY),
            "deltasXY": np.array(deltasXY),
            "center_coordsXY": np.array(center_coordsXY),
        }
        if ('sm' in FAM_FIBER.lower()) and (not IS_RUN_AUTOMOPT):
            optimizer_data[label]['pd_readsZ'] = np.array(pd_readsZ)
            optimizer_data[label]['deltasZ'] = np.array(deltasZ)

        print(f"{label:>12s}: {results[label][0]:.4f} +/- {results[label][1]:.4f} uW")

    # ============================================================
    # Center point (initial)
    # ============================================================
    print("\n--- Moving to on-center ---")
    dx, dy = 0.0, 0.0
    SimulateFieldPoint.main(dx, dy, verbose=verbose)
    _, start_pos = SimulateFieldPoint.move_FAM(dx, dy, FAM=FAM_TO_USE, ref_mode="center", verbose=False)
    measure("center_1", start_pos)

    # ============================================================
    # Circular field points
    # ============================================================
    print("\n--- Circular field points ---")
    angles = np.linspace(0, 2*np.pi, 8, endpoint=False)

    for i, theta in enumerate(angles):
        dx = separation * np.cos(theta)
        dy = separation * np.sin(theta)
        label = f"circ_{i}_dx{dx:+.3f}_dy{dy:+.3f}"

        print(f"\n--- Moving to {label} ---")
        try:
            SimulateFieldPoint.main(dx, dy, verbose=verbose)
            _, start_pos = SimulateFieldPoint.move_FAM(dx, dy, FAM=FAM_TO_USE, ref_mode="center", verbose=False)
        except Exception as e:
            print(f"ERROR moving to {label}: {e}")
            raise

        measure(label, start_pos)
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
            SimulateFieldPoint.main(dx, dy, verbose=verbose)
            _, start_pos = SimulateFieldPoint.move_FAM(dx, dy, FAM=FAM_TO_USE, ref_mode="center", verbose=False)
        except Exception as e:
            print(f"ERROR moving to {label}: {e}")
            raise

        measure(label, start_pos)

    # ============================================================
    # Return to center (final)
    # ============================================================
    print("\n--- Returning to on-center ---")
    SimulateFieldPoint.main(0.0, 0.0, verbose=verbose)
    _, start_pos = SimulateFieldPoint.move_FAM(0.0, 0.0, FAM=FAM_TO_USE, ref_mode="center", verbose=False)
    measure("center_2", start_pos)

    # Drift check
    c1 = results["center_1"][0]
    c2 = results["center_2"][0]
    print(f"\nCenter drift: {c2 - c1:+.4f} uW")

    # ============================================================
    # Save data
    # ============================================================
    outdir = Path(SAVE_DIR)
    outdir.mkdir(parents=True, exist_ok=True)

    stem = f"{FAM_TO_USE}FAM_{FAM_FIBER.upper()}_{MASK_TYPE}Mask_sep_{separation:.3f}mm"
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
    parser = argparse.ArgumentParser(description="Circular + square-corner field scan")
    parser.add_argument("separation", type=float, help="Separation in mm at the ILS")
    parser.add_argument("--nread", type=int, default=1000, help="Number of PD samples per position")
    parser.add_argument("--settle-time", type=float, default=2.0, help="Settle time after moves [s]")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose motion output")

    args = parser.parse_args()

    main(separation=args.separation, nread=args.nread, settle_time=args.settle_time, verbose=args.verbose)

    input("Press any key to close this terminal (this lets you review the plots)")
