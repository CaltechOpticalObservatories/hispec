import numpy as np
import time

import redPM_cmds
import CouplingOptimizer
import Fitter
from pipython import GCSDevice, GCSError

# Default number of reads to do at each point in a scan
NREAD_DFLT = 50


#-- FSM Config / setup
# Connection properites
IPADDRESS = '192.168.29.128'
IPPORT    = 50000
xAx = '1'
yAx = '2'
axes = [xAx, yAx]

# Setup Connection
dev = GCSDevice()

# Test the connection
print(f"** Connecting to controller")
dev.ConnectTCPIP(ipaddress= IPADDRESS, ipport = IPPORT)
print(f"** Connected to: {dev.qIDN()}")
# Close connection for now (we will reconnect only when needed)
dev.CloseConnection()
print(f"Disconnected from controller for now")

#-- Main 2D Scan (using the redPM)

def redPM_TT(start, stop, nsteps, center_coords=None, pause=0.0, nread=NREAD_DFLT):
    # Example: pd_reads, center_coords, deltas = redPM_XY(-0.05, 0.05, 11, )

    if (center_coords is not None) and len(center_coords) != 2:
        raise RuntimeError("center_coords should only be 2 dimensional when using FSM to scan")
    
    # Prealloc output array
    pd_reads = np.full((nsteps,nsteps),np.nan)

    # Format the array of positions to step through
    if center_coords is None:
        # Get current position
        pos = dev.qPOS()
        center_coords = [pos[xAx], pos[yAx]]
    deltas = np.linspace(start, stop, nsteps)
    delxs = deltas+center_coords[0]
    delys = deltas+center_coords[1]

    # Connect to FSM controller
    print(f"** Connecting to controller")
    dev.ConnectTCPIP(ipaddress= IPADDRESS, ipport = IPPORT)
    time.sleep(1)
    print(f"** Connected to: {dev.qIDN()}")

    # Close servo loops (in case they weren't previously closed)
    if not all(dev.qSVO(axes).values()):
        dev.SVO({ax:1 for ax in axes})
        print(f"FSM servo loops closed")

    # Perform scan 
    cur_max_val = -9999  
    cur_max_pos = [np.nan, np.nan]
    with redPM_cmds.redPM_cmds() as pd:
        for yind, dely in enumerate(delys):
            print(f"** Moving to Y = {dely:0.5f}")
            dev.MOV({yAx:dely})
            for xind, delx in enumerate(delxs):
                print(f"** Moving to X = {delx:0.5f}")
                dev.MOV({xAx:delx})
                
                # Give time for PD to settle
                time.sleep(pause)

                # Read power and process measurement
                read_val = pd.read_pd(nread) * redPM_cmds.redPM_cmds.PD_uW_CONVERSION
                pd_reads[xind,yind] = read_val
                if read_val > cur_max_val:
                    cur_max_val = read_val
                    cur_max_pos[:2] = [delx, dely]
                    print(f'==> New Max Power = {read_val:0.5f} uW at ({delx:0.5f}, {dely:0.5f})')
                
    print(f'** Position of maximum PD power: {cur_max_pos}')
    print(f'** Max Power = {cur_max_val}')
    
    # set FSM to position for center of scan
    dev.MOV({xAx:center_coords[0], yAx:center_coords[1]})
    print(f"FSM set to: ({center_coords[0]:0.5f}, {center_coords[1]:0.5f}) ")

    # Disconnect from FSM
    dev.CloseConnection()
    print("** Disconnected from FSM")

    return pd_reads, center_coords, deltas, cur_max_pos, cur_max_val

def redPM_newton_2d(
    start_pos,             # np.array([x, y])
    deltas,                # np.array([dx, dy])
    max_rel_move,          # np.array([x_lim, y_lim])
    nread=NREAD_DFLT,
    pause=0.0,
    max_iters=6,
    step_tol=1e-4,
    eta_tol=1e-4,
):
    """
    Newton optimizer for FSM tip/tilt (X, Y).
    """

    # Connect to FSM controller
    print(f"** Connecting to controller")
    dev.ConnectTCPIP(ipaddress= IPADDRESS, ipport = IPPORT)
    time.sleep(1)
    print(f"** Connected to: {dev.qIDN()}")

    # Close servo loops (in case they weren't previously closed)
    if not all(dev.qSVO(axes).values()):
        dev.SVO({ax:1 for ax in axes})
        print(f"FSM servo loops closed")
    

    with redPM_cmds.redPM_cmds() as pd:

        def move_to(pos, pause):
            dev.MOV({xAx: pos[0], yAx: pos[1]})
            time.sleep(pause)

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
            axis_names=["X", "Y"],
        )

    # Disconnect from FSM
    dev.CloseConnection()
    print("** Disconnected from FSM")

    return best_pos, history

def redPM_automated_tuning(
        start_pos, deltas, max_rel_move,
        nread=NREAD_DFLT, pause=0.0,
        max_iters=6, step_tol=1e-4, eta_tol=1e-4,
        XY_size=0.005, XY_points=17,
        ):
    # Example Usage: res = FSM_Scans.redPM_automated_tuning(start_pos=[17.5, 17.5], deltas=[0.1, 0.1], max_rel_move=[1, 1], pause=0.1, max_iters=12, step_tol=1e-4, eta_tol=1e-4, XY_size=0.04, XY_points=17)

    # ------------------------------------------------------------
    # 1) Newton optimizer
    # ------------------------------------------------------------
    print("\n---- Newton 2D Optimization ----")

    best_pos, history = redPM_newton_2d(
        start_pos=start_pos, deltas=deltas, max_rel_move=max_rel_move,
        nread=nread, pause=pause, max_iters=max_iters,
        step_tol=step_tol, eta_tol=eta_tol
    )

    print(
        f"\n** Newton 2D complete. Best position so far:\n"
        f"X={best_pos[0]:.6f}, Y={best_pos[1]:.6f}"
    )

    print("Giving a moment for controller to disconnect correctly")
    time.sleep(2)

    # ------------------------------------------------------------
    # 2) Detailed XY scan
    # ------------------------------------------------------------
    print("\n---- Detailed XY scan ----")

    pd_readsXY, center_coordsXY, deltasXY, fin_max_pos, fin_max_val = redPM_TT(
        -XY_size, XY_size, XY_points,
        center_coords=best_pos, pause=pause, nread=nread
    )

    # HACK - add fake Z-pos to center_coords so we can use the 2D_FAMScan plotter
    center_coordsXY = [center_coordsXY[0], center_coordsXY[1], np.nan]

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

    print(f"\n\n=== Final Measured Position ===")
    print(f"Power = {fin_max_val:.5f} uW")
    print(f"X = {fin_max_pos[0]:.6f}")
    print(f"Y = {fin_max_pos[1]:.6f}")

    return (
        peak_coords, history,
        pd_readsXY, deltasXY, center_coordsXY, figXY
    )