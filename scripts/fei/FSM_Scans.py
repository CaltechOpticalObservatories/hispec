import numpy as np
import time

import redPM_cmds
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

    return pd_reads, center_coords, deltas
