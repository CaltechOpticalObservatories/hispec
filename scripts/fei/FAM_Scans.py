import numpy as np
import time
import sys

import Fitter
import CouplingOptimizer
import redPM_cmds
sys.path.append("/home/hsdev/dechever/FEI_Stage_Checkout/XeryonTesting/")
from Xeryon_HISPEC import Xeryon, Stage

# Default number of reads to do at each point in a scan
NREAD_DFLT = 50


#-- Xeryon Config / setup

# Flag to enable/disable library-internal logger
ENABLE_LOGGING = True

# Path to settings file to use
#SETTINGS_FILENAME = "/home/hsdev/dechever/settings_FEI_XD24508.txt"
#SETTINGS_FILENAME = "/home/hsdev/dechever/settings_FEI_XD24494.txt"
#SETTINGS_FILENAME = "/home/hsdev/dechever/settings_FEI_XD24508_20250902.txt"    # Blue
SETTINGS_FILENAME = "/home/hsdev/dechever/settings_FEI_XD24494_20250828.txt"   # Red
# Connection properites
COM_PORT = "/dev/ttyRedFAM"

# Max time to wait for move to complete
MOV_TIMEOUT = 20 # [seconds]

# Setup controller and axis objects
controller = Xeryon(COM_port = COM_PORT, baudrate = 115200)
# (letters are defined in the settings_default.txt file)
yAxis = controller.addAxis(Stage.XLS_5_3N, "A")
xAxis = controller.addAxis(Stage.XLS_5_3N, "B")
zAxis = controller.addAxis(Stage.XLS_5_3N, "C")
# Helpful letter-to-axis mapping for printing
LETTER_MAP = {"A":"Y", "B":"X", "C":"Z"}
ordered_axis_list = [xAxis, yAxis, zAxis]

#########################################################################
############################ Basic Raster Scans #########################
#########################################################################

#--- 2D (XY) Scan
def redPM_XY(start, stop, nsteps, center_coords=None, pause=0.0, nread=NREAD_DFLT):
    # Example: pd_reads, center_coords, deltas, cur_max_pos, cur_max_val = redPM_XY(-0.05, 0.05, 11, )
    
    # Prealloc output array
    pd_reads = np.full((nsteps,nsteps),np.nan)

    # Connect to xeryon controller
    print(f"** Connecting to controller")
    controller.start(external_settings_default = SETTINGS_FILENAME, do_reset=False, send_settings=False)
    time.sleep(3)
    print(f"** Connected to: {COM_PORT}")

    # Format the array of positions to step through
    moveZ = True   # Flag to note if new Z position was requested
    if center_coords is None:
        moveZ = False   # No need to move Z since we're using current coords as centerpoint
        # Get current position
        center_coords = []
        for axis in ordered_axis_list:
            center_coords.append(axis.getEPOS())
    deltas = np.linspace(start, stop, nsteps)
    delxs = deltas+center_coords[0]
    delys = deltas+center_coords[1]

    # Check Xeryon reference state, and reference if needed
    for axis in controller.getAllAxis():
        axis_letter = axis.getLetter()
        axis_dir    = LETTER_MAP[axis_letter]
        # Check reference state
        resp = axis.isEncoderValid()
        # Reference if needed
        if not resp:
            print(f"** REFERENCING {axis_dir} Axis...")
            # TODO: forceWaiting doesn't seem to work right now. Must fix
            axis.findIndex(forceWaiting = True)
            # Add a small sleep for now to account for issue with forceWaiting
            time.sleep(2)   # TODO:: Remove this sleep
            if not axis.isEncoderValid():
                print(f"** Failed to reference {axis_dir} Axis ('{axis_letter}')!")
                controller.stop()
                print(f"** Disconnected from controller due to this reference failure")
                raise RuntimeError(f"Failed to reference {axis_dir} Axis ('{axis_letter}')")
            else:
                print(f"** {axis_dir} Axis successfully referenced")

    # Set Z Position
    if moveZ:
        zAxis.setDPOS(center_coords[2], outputToConsole=False)
        print(f"FAM moved to Z = {center_coords[2]}")
    else:
        print(f"Using starting Z position ({center_coords[2]})")

    # Perform scan (X/Y only)
    cur_max_val = -9999  
    cur_max_pos = [np.nan, np.nan, center_coords[2]]
    with redPM_cmds.redPM_cmds() as pd:
        for yind, dely in enumerate(delys):
            #print(f"** Moving to Y = {dely:0.5f}")
            yAxis.setDPOS(dely, outputToConsole=False)
            for xind, delx in enumerate(delxs):
                #print(f"** Moving to X = {delx:0.5f}")
                xAxis.setDPOS(delx, outputToConsole=False)

                # Wait to make sure all stages have settled in position
                t0 = time.time()
                while xAxis.isMotorOn() or yAxis.isMotorOn() or zAxis.isMotorOn():
                    if ( time.time() - t0 ) > MOV_TIMEOUT :
                        controller.stopMovements()
                        print(f"\n** WARN: Move did not to complete within {MOV_TIMEOUT} seconds... stopping this move attempt and proceeding to next step")
                        break
                    time.sleep(0.05)

                # Give time for PD to settle
                time.sleep(pause)

                # Read power and process measurement
                read_val = pd.read_pd(nread) * redPM_cmds.redPM_cmds.PD_uW_CONVERSION
                pd_reads[xind, yind] = read_val
                if read_val > cur_max_val:
                    cur_max_val = read_val
                    cur_max_pos[:2] = [delx, dely]
                    #print(f"\n==> New Max Power = {cur_max_val:.5f} uW at ({delx:.5f}, {dely:.5f}, {center_coords[2]:.5f})")

                # Print current scanning status on the same line
                print(f"\rPos: X={delx:.5f}, Y={dely:.5f} | Cur. Max={cur_max_val:.5f} uW at ({cur_max_pos[0]:0.5f}, {cur_max_pos[1]:0.5f})", end="")
                
    print(f'\n** Position of maximum PD power: {cur_max_pos}')
    print(f'** Max Power = {cur_max_val}')
    
    # set FAM to position for center of scan
    xAxis.setDPOS(center_coords[0], outputToConsole=False)
    yAxis.setDPOS(center_coords[1], outputToConsole=False)
    if moveZ:
        zAxis.setDPOS(center_coords[2], outputToConsole=False)
    print(f"FAM set to: ({center_coords[0]:0.5f}, {center_coords[1]:0.5f}, {center_coords[2]:0.5f}) ")

    # Disconnect from FAM
    controller.stop(isPrintEnd=False)
    print("** Disconnected from FAMs")

    return pd_reads, center_coords, deltas, cur_max_pos, cur_max_val

#--- 1D (Z - Focus) Scan
def redPM_Z(start, stop, nsteps, center_coords=None, pause=0.0, nread=NREAD_DFLT):
    # Example Usage: pd_reads, center_coords, deltas = FAM_Scans.redPM_Z(-0.1, 0.1, 80, center_coords=[-7.65, -0.03, 7.79], pause=0.0, nread=10)

    # Prealloc output array
    pd_reads = np.full((nsteps),np.nan)

    # Connect to xeryon controller
    print(f"** Connecting to controller")
    controller.start(external_settings_default = SETTINGS_FILENAME, do_reset=False, send_settings=False)
    time.sleep(3)
    print(f"** Connected to: {COM_PORT}")

    # Format the array of positions to step through
    moveXY = True   # Flag to note if new XY position was requested
    if center_coords is None:
        moveXY = False   # No need to move XY since we're using current coords as centerpoint
        # Get current position
        center_coords = []
        for axis in ordered_axis_list:
            center_coords.append(axis.getEPOS())
    deltas = np.linspace(start, stop, nsteps)
    delzs = deltas+center_coords[2]

    # Check Xeryon reference state, and reference if needed
    for axis in controller.getAllAxis():
        axis_letter = axis.getLetter()
        axis_dir    = LETTER_MAP[axis_letter]
        # Check reference state
        resp = axis.isEncoderValid()
        # Reference if needed
        if not resp:
            print(f"** REFERENCING {axis_dir} Axis...")
            # TODO: forceWaiting doesn't seem to work right now. Must fix
            axis.findIndex(forceWaiting = True)
            # Add a small sleep for now to account for issue with forceWaiting
            time.sleep(2)   # TODO:: Remove this sleep
            if not axis.isEncoderValid():
                print(f"** Failed to reference {axis_dir} Axis ('{axis_letter}')!")
                controller.stop()
                print(f"** Disconnected from controller due to this reference failure")
                raise RuntimeError(f"Failed to reference {axis_dir} Axis ('{axis_letter}')")
            else:
                print(f"** {axis_dir} Axis successfully referenced")

    # Set XY Position
    if moveXY:
        xAxis.setDPOS(center_coords[0], outputToConsole=False)
        print(f"FAM moved to X = {center_coords[0]}")
        yAxis.setDPOS(center_coords[1], outputToConsole=False)
        print(f"FAM moved to Y = {center_coords[1]}")
    else:
        print(f"Using starting X position ({center_coords[0]})")
        print(f"Using starting Y position ({center_coords[1]})")

    # Perform scan (X/Y only)
    cur_max_val = -9999  
    cur_max_pos = [center_coords[0], center_coords[1], np.nan]
    with redPM_cmds.redPM_cmds() as pd:
        for zind, delz in enumerate(delzs):
            zAxis.setDPOS(delz, outputToConsole=False)

            # Wait for stages to settle
            t0 = time.time()
            while xAxis.isMotorOn() or yAxis.isMotorOn() or zAxis.isMotorOn():
                if ( time.time() - t0 ) > MOV_TIMEOUT :
                    controller.stopMovements()
                    print(f"\n** WARN: Move did not to complete within {MOV_TIMEOUT} seconds... stopping this move attempt and proceeding to next step")
                    break
                time.sleep(0.05)

            # Give time for PD to settle
            time.sleep(pause)

            # Read power and process measurement
            read_val = pd.read_pd(nread) * redPM_cmds.redPM_cmds.PD_uW_CONVERSION
            pd_reads[zind] = read_val
            if read_val > cur_max_val:
                cur_max_val = read_val
                cur_max_pos[2] = delz

            # Print scanning status on same line
            print(f"\rPos: Z={delz:.5f} | Cur. Max={cur_max_val:.5f} uW at ({cur_max_pos[0]:0.5f}, {cur_max_pos[1]:0.5f}, {cur_max_pos[2]:0.5f})", end="")
                
    print(f'\n** Position of maximum PD power: {cur_max_pos}')
    print(f'** Max Power = {cur_max_val}')
    
    # set FAM to position for center of scan
    if moveXY:
        xAxis.setDPOS(center_coords[0], outputToConsole=False)
        yAxis.setDPOS(center_coords[1], outputToConsole=False)
    zAxis.setDPOS(center_coords[2], outputToConsole=False)
    print(f"FAM set to: ({center_coords[0]:0.5f}, {center_coords[1]:0.5f}, {center_coords[2]:0.5f}) ")

    # Disconnect from FAM
    controller.stop(isPrintEnd=False)
    print("** Disconnected from FAMs")


    return pd_reads, center_coords, deltas

#-- TODO: ADD a function that does a set of 2D scans and then a 1D scan followed by a final 2D. 
#         This could be an alternative to the Newton minimization.
#         The functions should use the gaussian fitting functions to find the optimal position


#########################################################################
################## Nicer Optimization Functions #########################
#########################################################################

# --- Helper Function
def move_and_wait(x=None, y=None, z=None, pause=0.0):
    if x is not None:
        xAxis.setDPOS(x, outputToConsole=False)
    if y is not None:
        yAxis.setDPOS(y, outputToConsole=False)
    if z is not None:
        zAxis.setDPOS(z, outputToConsole=False)

    t0 = time.time()
    while xAxis.isMotorOn() or yAxis.isMotorOn() or zAxis.isMotorOn():
        if ( time.time() - t0 ) > MOV_TIMEOUT :
            controller.stopMovements()
            print(f"\n** WARN: Move did not to complete within {MOV_TIMEOUT} seconds... stopping this move attempt")
            break
        time.sleep(0.05)

    time.sleep(pause)

# --- Optimizer using finite-difference Netwon Ascent
def redPM_newton_3d(
    start_pos,             # np.array([x, y, z])
    deltas,                # np.array([dx, dy, dz])
    max_rel_move,          # np.array([x_lim, y_lim, z_lim])
    nread=NREAD_DFLT,
    pause=0.0,
    max_iters=6,
    step_tol=1e-4,
    eta_tol=1e-4,
):
    """
    Newton optimizer for FAM X/Y/Z stages.
    """

    print(f"** Connecting to FAM controller")
    controller.start(external_settings_default = SETTINGS_FILENAME, do_reset=False, send_settings=False)
    time.sleep(3)
    print(f"** Connected to: {COM_PORT}")

    # --- Reference axes if needed ---
    for axis in controller.getAllAxis():
        # Check reference state
        if not axis.isEncoderValid():
            # Axis was not referenced; do so now
            axis_letter = axis.getLetter()
            axis_dir = LETTER_MAP[axis_letter]
            print(f"** REFERENCING {axis_dir} Axis...")
            axis.findIndex(forceWaiting=True)
            time.sleep(2)
            if not axis.isEncoderValid():
                controller.stopMovements()
                controller.stop()
                raise RuntimeError(f"Failed to reference {axis_dir} Axis ('{axis_letter}'). Disconnected from controller due to this issue.")
            else:
                print(f"** {axis_dir} successfully referenced")

    with redPM_cmds.redPM_cmds() as pd:

        def move_to(pos, pause):
            move_and_wait(pos[0], pos[1], pos[2], pause=pause)

        def read_power():
            return pd.read_pd(nread) * redPM_cmds.redPM_cmds.PD_uW_CONVERSION

        best_pos, best_eta, history = CouplingOptimizer.redPM_newton_core(
            move_to=move_to,
            read_power=read_power,
            start_pos=start_pos,
            deltas=deltas,
            max_rel_move=max_rel_move,
            pause=pause,
            max_iters=max_iters,
            step_tol=step_tol,
            eta_tol=eta_tol,
            axis_names=["X", "Y", "Z"],
        )

    controller.stopMovements()
    controller.stop(isPrintEnd=False)
    print("** Disconnected from FAMs")

    return best_pos, history


def redPM_newton_3d_ORIG(
    start_pos,             # np.array([x, y, z])
    deltas,                # np.array([dx, dy, dz])
    max_rel_move,          # np.array([x_lim, y_lim, z_lim])
    nread=NREAD_DFLT,
    pause=0.0,
    max_iters=6,
    step_tol=1e-4,
    eta_tol=1e-4
):
    """
    Finite-difference Newton ascent on log(power).

    Returns:
        final_pos : np.array([x, y, z])
        history   : list of dicts with gradients, curvatures, etc.

    Sample Usage:
        best_pos, history = FAM_Scans.redPM_newton_3d(start_pos=[7.332, -0.163, 6.7251], deltas=[0.007, 0.007, 0.01], 
                                max_rel_move=[0.02, 0.02, 0.06], pause=0.2, max_iters=12, step_tol=1e-4, eta_tol=1e-4)
    """

    deltas = np.asarray(deltas, dtype=float)
    max_rel_move = np.asarray(max_rel_move, dtype=float)
    start_pos = np.asarray(start_pos, dtype=float)

    history = []

    # --- Connect controller ---
    print(f"** Connecting to controller")
    controller.start(external_settings_default = SETTINGS_FILENAME, do_reset=False, send_settings=False)
    time.sleep(3)
    print(f"** Connected to: {COM_PORT}")

    # --- Reference axes if needed ---
    for axis in controller.getAllAxis():
        # Check reference state
        if not axis.isEncoderValid():
            # Axis was not referenced; do so now
            axis_letter = axis.getLetter()
            axis_dir = LETTER_MAP[axis_letter]
            print(f"** REFERENCING {axis_dir} Axis...")
            axis.findIndex(forceWaiting=True)
            time.sleep(2)
            if not axis.isEncoderValid():
                controller.stop()
                raise RuntimeError(f"Failed to reference {axis_dir} Axis ('{axis_letter}'). Disconnected from controller due to this issue.")
            else:
                print(f"** {axis_dir} successfully referenced")

    # --- Move to starting position ---
    print(f"** Moving to start_pos = {start_pos}")
    move_and_wait(*start_pos, pause=pause)

    cur_pos = start_pos.copy()
    prev_eta = None

    best_eta = -np.inf
    best_pos = cur_pos.copy()

    with redPM_cmds.redPM_cmds() as pd:
        for it in range(max_iters):
            print(f"\n=== Newton iteration {it} ===")

            # --- Center measurement ---
            move_and_wait(*cur_pos, pause=pause)
            eta0 = pd.read_pd(nread) * redPM_cmds.redPM_cmds.PD_uW_CONVERSION
            f0 = np.log(max(eta0, 1e-12))

            # --- Track best-ever ---
            if eta0 > best_eta:
                best_eta = eta0
                best_pos = cur_pos.copy()


            grad = np.zeros(3)
            hess = np.zeros(3)

            # --- Finite differences ---
            for i, axis_name in enumerate(["X", "Y", "Z"]):
                step_vec = np.zeros(3)
                step_vec[i] = deltas[i]

                # +sample step
                move_and_wait(*(cur_pos + step_vec), pause=pause)
                read = pd.read_pd(nread) * redPM_cmds.redPM_cmds.PD_uW_CONVERSION
                fp = np.log(max(read, 1e-12))   # use 1e-12 as a floor so we don't get Nan's

                # -sample step
                move_and_wait(*(cur_pos - step_vec), pause=pause)
                read = pd.read_pd(nread) * redPM_cmds.redPM_cmds.PD_uW_CONVERSION
                fm = np.log(max(read, 1e-12))   # use 1e-12 as a floor so we don't get NaN's

                grad[i] = (fp - fm) / (2 * deltas[i])
                hess[i] = (fp - 2 * f0 + fm) / (deltas[i] ** 2)

                print(
                    f" {axis_name}: grad={grad[i]:+.3e}, "
                    f"hess={hess[i]:+.3e}"
                )

            # --- Newton step ---
            step = np.zeros(3)
            for i in range(3):
                if hess[i] < 0:
                    step[i] = -grad[i] / hess[i]

            proposed_pos = cur_pos + step

            # --- Safety clamp to prevent moving too far ---
            lower = start_pos - max_rel_move
            upper = start_pos + max_rel_move
            proposed_pos = np.minimum(np.maximum(proposed_pos, lower), upper)

            # --- Evaluate proposed position ---
            move_and_wait(*proposed_pos, pause=pause)
            eta_new = pd.read_pd(nread) * redPM_cmds.redPM_cmds.PD_uW_CONVERSION

            # --- Track best-ever ---
            if eta_new > best_eta:
                best_eta = eta_new
                best_pos = proposed_pos.copy()


            history.append({
                "iter": it,
                "pos": cur_pos.copy(),
                "power": eta0,
                "grad": grad.copy(),
                "hess": hess.copy(),
                "step": step.copy(),
                "best_power_so_far": best_eta,
            })


            print(
                f" Power: {eta0:.5f} uW --> {eta_new:.5f} uW, "
                f"|step|={np.linalg.norm(step)*1e3:.3f} um"
            )

            # --- Convergence checks ---
            # Check if eta is improving by a meaningful amount
            rel_eta_improve = (
                np.inf if prev_eta is None
                else (eta_new - prev_eta) / max(prev_eta, 1e-12)
            )

            if (prev_eta is not None) and (rel_eta_improve < eta_tol):
                print("** Converged: coupling improvement below threshold")
                cur_pos = proposed_pos
                break

            step_norm = np.linalg.norm(proposed_pos - cur_pos)
            if step_norm < step_tol:
                print("** Converged: step size below threshold")
                cur_pos = proposed_pos
                break

            # Accept step
            cur_pos = proposed_pos
            prev_eta = eta_new

            # shrink deltas so we take smaller steps as we get closer
            deltas *= 0.7

    # --- Final position ---
    move_and_wait(*best_pos)
    controller.stop(isPrintEnd=False)
    print("** Disconnected from FAMs")

    print(
        f"\n=== BEST COUPLING POSITION FOUND ===\n"
        f"Power = {best_eta:.5f} uW\n"
        f"X = {best_pos[0]:.6f}\n"
        f"Y = {best_pos[1]:.6f}\n"
        f"Z = {best_pos[2]:.6f}\n"
    )
    return best_pos, history

def redPM_newton_3d_with_Zscan(
        start_pos, deltas, max_rel_move,
        nread=NREAD_DFLT, pause=0.0,
        max_iters=6, step_tol=1e-4, eta_tol=1e-4,
        Zscan_size=0.04, Zscan_points=61
        ):

    # --- Step 1: Run 3D Newton optimizer ---
    best_pos, history = redPM_newton_3d(start_pos=start_pos, deltas=deltas, max_rel_move=max_rel_move,
                                        nread=nread, pause=pause, max_iters=max_iters,
                                        step_tol=step_tol, eta_tol=eta_tol)

    print(f"\n** Newton 3D complete. Best position so far:\n"
          f"X={best_pos[0]:.6f}, Y={best_pos[1]:.6f}, Z={best_pos[2]:.6f}")
    
    print("Giving a moment for controller to disconnect correctly")
    time.sleep(2)

    # --- Step 2: Do simple Z-only scan around Newton result ---
    pd_reads, center_coords, z_deltas = redPM_Z(-Zscan_size, Zscan_size, Zscan_points, center_coords=best_pos,
                                               pause=pause, nread=nread)

    # --- Step 3: Fit a Gaussian to the Z scan ---
    peak_coords, Z_peak, popt, fig = Fitter.plot_1D_FAMScan_with_gaussFit(pd_reads, center_coords, z_deltas)

    # --- Step 5: Print final optimized position ---
    print(f"\n=== FINAL OPTIMIZED POSITION AFTER Z SCAN ===")
    print(f"Power = {Z_peak:.5f} uW (peak of fitted Gaussian)")
    print(f"X = {peak_coords[0]:.6f}")
    print(f"Y = {peak_coords[1]:.6f}")
    print(f"Z = {peak_coords[2]:.6f}")

    return best_pos, history, pd_reads, z_deltas, fig

def redPM_automated_tuning(
        start_pos, deltas, max_rel_move,
        nread=NREAD_DFLT, pause=0.0,
        max_iters=6, step_tol=1e-4, eta_tol=1e-4,
        Zscan_size=0.04, Zscan_points=61,
        XY_size=0.005, XY_points=17,
        XY_quick_size=0.002, XY_quick_points=9
        ):
    # Sample Use: res = FAM_Scans.redPM_automated_tuning(start_pos=[-7.80971, 0.02319, 9.0455], deltas=[0.007, 0.007, 0.01], max_rel_move=[0.02, 0.02, 0.06], pause=0.2, max_iters=12, step_tol=1e-4, eta_tol=1e-4, XY_size=0.003, XY_points=17)

    # ------------------------------------------------------------
    # 1) Newton optimizer
    # ------------------------------------------------------------
    print("\n---- Newton 3D Optimization ----")

    best_pos, history = redPM_newton_3d(
        start_pos=start_pos, deltas=deltas, max_rel_move=max_rel_move,
        nread=nread, pause=pause, max_iters=max_iters,
        step_tol=step_tol, eta_tol=eta_tol
    )

    print(
        f"\n** Newton 3D complete. Best position so far:\n"
        f"X={best_pos[0]:.6f}, Y={best_pos[1]:.6f}, Z={best_pos[2]:.6f}"
    )

    print("Giving a moment for controller to disconnect correctly")
    time.sleep(2)

    # ------------------------------------------------------------
    # 2) Quick XY scan
    # ------------------------------------------------------------
    print("\n---- Quick XY-only scan ----")

    pd_readsXY, center_coordsXY, deltasXY, _, _ = redPM_XY(
        -XY_quick_size, XY_quick_size, XY_quick_points,
        center_coords=best_pos, pause=pause, nread=nread
    )

    print("Giving a moment for controller to disconnect correctly")
    time.sleep(2)

    # ------------------------------------------------------------
    # 3) Gaussian fit to XY scan
    # ------------------------------------------------------------
    peak_coordsXY, A_xy, poptXY, figXY_quick = (
        Fitter.plot_2D_FAMScan_with_gaussFit(pd_readsXY, center_coordsXY, deltasXY)
    )

    print(
        f"\n** XY recentered via Gaussian fit:\n"
        f"X={peak_coordsXY[0]:.6f}, Y={peak_coordsXY[1]:.6f}"
    )

    # Update only X/Y
    cur_pos = np.array([peak_coordsXY[0], peak_coordsXY[1], best_pos[2]])

    # ------------------------------------------------------------
    # 4) Z scan
    # ------------------------------------------------------------
    print("\n---- Simple Z-only scan ----")

    pd_readsZ, center_coordsZ, deltasZ = redPM_Z(
        -Zscan_size, Zscan_size, Zscan_points,
        center_coords=cur_pos, pause=pause, nread=nread
    )

    print("Giving a moment for controller to disconnect correctly")
    time.sleep(2)

    # ------------------------------------------------------------
    # 5) Gaussian fit to Z scan
    # ------------------------------------------------------------
    peak_coordsZ, Z_peak, poptZ, figZ = (
        Fitter.plot_1D_FAMScan_with_gaussFit(pd_readsZ, center_coordsZ, deltasZ)
    )

    print(f"\n** Focus set via Gaussian fit: Z={peak_coordsZ[2]:.6f}")

    # Update only Z
    cur_pos[2] = peak_coordsZ[2]

    # ------------------------------------------------------------
    # 6) Final XY scan
    # ------------------------------------------------------------
    print("\n---- Final XY-only scan ----")

    pd_readsXY, center_coordsXY, deltasXY, fin_max_pos, fin_max_val = redPM_XY(
        -XY_size, XY_size, XY_points,
        center_coords=cur_pos, pause=pause, nread=nread
    )

    print("Giving a moment for controller to disconnect correctly")
    time.sleep(2)

    peak_coords, A_peak, poptXY, figXY = (
        Fitter.plot_2D_FAMScan_with_gaussFit(pd_readsXY, center_coordsXY, deltasXY)
    )

    # ------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------
    print(f"\n\n=== Final Optimized Position - Gaussian Fit ===")
    print(f"Power = {A_peak:.5f} uW (peak of fitted Gaussian)")
    print(f"X = {peak_coords[0]:.6f}")
    print(f"Y = {peak_coords[1]:.6f}")
    print(f"Z = {peak_coords[2]:.6f}")

    print(f"\n\n=== Final Measured Position ===")
    print(f"Power = {fin_max_val:.5f} uW")
    print(f"X = {fin_max_pos[0]:.6f}")
    print(f"Y = {fin_max_pos[1]:.6f}")
    print(f"Z = {fin_max_pos[2]:.6f}")

    return (
        peak_coords, history,
        pd_readsZ, deltasZ, center_coordsZ, figZ,
        pd_readsXY, deltasXY, center_coordsXY, figXY
    )


