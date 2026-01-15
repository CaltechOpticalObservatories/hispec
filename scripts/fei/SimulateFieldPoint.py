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
MS_CENTER  = np.array([1.800, 33.620])   # (X, Y)

MS_SCALE = 92.6 / 182.6   # ~0.507

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
# Main logic
# =========================
def main(dx, dy, dry_run=False, verbose=False):

    def vprint(msg):
        if verbose:
            print(msg)

    # -------------------------
    # Compute offsets and targets
    # -------------------------
    ils_offset = np.array([dx, dy])
    ms_offset  = MS_SCALE * ils_offset

    ils_target = ILS_CENTER + ils_offset
    ms_target  = MS_CENTER  + ms_offset

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
    vprint("Connecting to ILS...")
    with GCSDevice() as ILS_X:
        ILS_X.OpenTCPIPDaisyChain(ipaddress=IPADDRESS, ipport=IPPORT_ILS)
        ILS_X.ConnectDaisyChainDevice(1, ILS_X.dcid)
        vprint(f"- Connected to ILS X: {ILS_X.qIDN().strip()}")

        with GCSDevice() as ILS_Y:
            ILS_Y.ConnectDaisyChainDevice(2, ILS_X.dcid)
            vprint(f"- Connected to ILS Y: {ILS_Y.qIDN().strip()}")

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
    vprint("Connecting to MS...")
    with GCSDevice() as MS_Y:
        MS_Y.OpenTCPIPDaisyChain(ipaddress=IPADDRESS, ipport=IPPORT_MS)
        MS_Y.ConnectDaisyChainDevice(1, MS_Y.dcid)
        vprint(f"- Connected to MS Y: {MS_Y.qIDN().strip()}")

        with GCSDevice() as MS_X:
            MS_X.ConnectDaisyChainDevice(2, MS_Y.dcid)
            vprint(f"- Connected to MS X: {MS_X.qIDN().strip()}")

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
# Command-line entry point
# =========================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Move ILS and MS by a field offset")
    parser.add_argument("dx", type=float, help="Field offset in X (ILS)")
    parser.add_argument("dy", type=float, help="Field offset in Y (ILS)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print motions but do not move stages")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output (debug / engineering info)")
    args = parser.parse_args()

    result = main( dx=args.dx, dy=args.dy, dry_run=args.dry_run, verbose=args.verbose )

    sys.exit()
