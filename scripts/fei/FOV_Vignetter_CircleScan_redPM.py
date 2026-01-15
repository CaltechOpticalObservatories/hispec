import numpy as np
import time
import argparse
from pathlib import Path

import redPM_cmds
import SimulateFieldPoint

# -------------------------
# Main
# -------------------------
def main(separation, nread, settle_time=0.2, verbose=False):

    results = {}
    raw_data = {}

    def measure(label):
        time.sleep(settle_time)
        with redPM_cmds.redPM_cmds() as pd:
            vals = pd.readN(nread) * redPM_cmds.redPM_cmds.PD_uW_CONVERSION
        raw_data[label] = vals
        results[label] = (np.mean(vals), np.std(vals))
        print(f"{label:>12s}: {results[label][0]:.4f} +/- {results[label][1]:.4f} uW")

    print("\n--- Moving to on-center ---")
    SimulateFieldPoint.main(0.0, 0.0, verbose=verbose)
    measure("center_1")

    # -------------------------
    # Circular field points
    # -------------------------
    angles = np.linspace(0, 2*np.pi, 8, endpoint=False)

    for i, theta in enumerate(angles):
        dx = separation * np.cos(theta)
        dy = separation * np.sin(theta)

        label = f"pt_{i}_({dx:+.3f},{dy:+.3f})"
        print(f"\n--- Moving to {label} ---")
        try:
            SimulateFieldPoint.main(dx, dy, verbose=verbose)
        except Exception as e:
            print(f"ERROR moving to {label}: {e}")
            raise
        measure(label)

    # -------------------------
    # Return to center
    # -------------------------
    print("\n--- Returning to on-center ---")
    SimulateFieldPoint.main(0.0, 0.0, verbose=verbose)
    measure("center_2")

    # Print the starting and ending center values so you can compare if there was a power drift
    c1 = results["center_1"][0]
    c2 = results["center_2"][0]
    print(f"\nCenter drift: {c2 - c1:+.4f} uW")

    # -------------------------
    # Save data
    # -------------------------
    outdir = Path("/home/hsdev/dechever/AIT_Verification_Data/Experiment7_VignetteChecks")
    outdir.mkdir(parents=True, exist_ok=True)  # ensure folder exists

    stem = f"BlueFibFocus_PDPos3_circle_scan_sep_{separation:.3f}mm"
    outname = outdir / f"{stem}.npz"

    i = 1
    while outname.exists():
        outname = outdir / f"{stem}_{i}.npz"
        i += 1

    np.savez(outname, separation_mm=separation, nread=nread, raw_pd=raw_data, stats=results)

    print(f"\nSaved raw data to {outname.resolve()}")

# -------------------------
# CLI entry point
# -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Circular field power scan using ILS/MS and redPM")
    parser.add_argument("separation", type=float, help="Separation in mm at the ILS")
    parser.add_argument("--nread", type=int, default=1000, help="Number of PD samples per position")
    parser.add_argument("--settle-time", type=float, default=2.0, help="Settle time after moves [s]")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose motion output")

    args = parser.parse_args()

    main(separation=args.separation, nread=args.nread, settle_time=args.settle_time, verbose=args.verbose)
