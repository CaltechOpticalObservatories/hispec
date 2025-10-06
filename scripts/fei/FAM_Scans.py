import numpy as np
import time

import redPM_cmds
from hispec.util import XeryonController, XeryonStage

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
COM_PORT = "/dev/ttyACM0"  #Red = 0, Blue = 1

# Max time to wait for move to complete
MOV_TIMEOUT = 20 # [seconds]

# Setup controller and axis objects
controller = XeryonController(COM_port = COM_PORT, log = ENABLE_LOGGING, settings_filename=SETTINGS_FILENAME)
# (letters are defined in the settings_default.txt file)
yAxis = controller.add_axis(XeryonStage.XLS_5_3N, "A")
xAxis = controller.add_axis(XeryonStage.XLS_5_3N, "B")
zAxis = controller.add_axis(XeryonStage.XLS_5_3N, "C")
# Helpful letter-to-axis mapping for printing
LETTER_MAP = {"A":"Y", "B":"X", "C":"Z"}
ordered_axis_list = [xAxis, yAxis, zAxis]

#-- Main 2D Scan (using the redPM)

def redPM_XY(start, stop, nsteps, center_coords=None, pause=0.0, nread=NREAD_DFLT):
    # Example: pd_reads, center_coords, deltas = redPM_XY(-0.05, 0.05, 11, )
    
    # Prealloc output array
    pd_reads = np.full((nsteps,nsteps),np.nan)

    # Connect to xeryon controller
    print(f"** Connecting to controller")
    controller.start(do_reset=False, auto_send_settings=False)
    time.sleep(3)
    print(f"** Connected to: {COM_PORT}")

    # Format the array of positions to step through
    moveZ = True   # Flag to note if new Z position was requested
    if center_coords is None:
        moveZ = False   # No need to move Z since we're using current coords as centerpoint
        # Get current position
        center_coords = []
        for axis in ordered_axis_list:
            center_coords.append(axis.get_EPOS())
    deltas = np.linspace(start, stop, nsteps)
    delxs = deltas+center_coords[0]
    delys = deltas+center_coords[1]

    # Check Xeryon reference state, and reference if needed
    for axis in controller.get_all_axis():
        axis_letter = axis.get_letter()
        axis_dir    = LETTER_MAP[axis_letter]
        # Check reference state
        resp = axis.is_encoder_valid()
        # Reference if needed
        if not resp:
            print(f"** REFERENCING {axis_dir} Axis...")
            # TODO: forceWaiting doesn't seem to work right now. Must fix
            axis.find_index(forceWaiting = True)
            # Add a small sleep for now to account for issue with forceWaiting
            time.sleep(2)   # TODO:: Remove this sleep
            if not axis.is_encoder_valid():
                print(f"** Failed to reference {axis_dir} Axis ('{axis_letter}')!")
                controller.stop()
                print(f"** Disconnected from controller due to this reference failure")
                raise RuntimeError(f"Failed to reference {axis_dir} Axis ('{axis_letter}')")
            else:
                print(f"** {axis_dir} Axis successfully referenced")

    # Set Z Position
    if moveZ:
        zAxis.set_D_POS(center_coords[2])
        print(f"FAM moved to Z = {center_coords[2]}")
    else:
        print(f"Using starting Z position ({center_coords[2]})")

    # Perform scan (X/Y only)
    cur_max_val = -9999  
    cur_max_pos = [np.nan, np.nan, center_coords[2]]
    with redPM_cmds.redPM_cmds() as pd:
        for yind, dely in enumerate(delys):
            print(f"** Moving to Y = {dely:0.5f}")
            yAxis.set_D_POS(dely)
            for xind, delx in enumerate(delxs):
                print(f"** Moving to X = {delx:0.5f}")
                xAxis.set_D_POS(delx)

                # Wait to make sure all stages have settled in position
                t0 = time.time()
                while xAxis.is_motor_on() or yAxis.is_motor_on() or zAxis.is_motor_on():
                    if ( time.time() - t0 ) > MOV_TIMEOUT :
                        print(f"** WARN: Move in at least 1 of the axes failed to complete within {MOV_TIMEOUT} seconds... proceeding to next step")
                        break
                    time.sleep(0.05)

                # Give time for PD to settle
                time.sleep(pause)

                # Read power and process measurement
                read_val = pd.read_pd(nread) * redPM_cmds.redPM_cmds.PD_uW_CONVERSION
                pd_reads[xind,yind] = read_val
                if read_val > cur_max_val:
                    cur_max_val = read_val
                    cur_max_pos[:2] = [delx, dely]
                    print(f'==> New Max Power = {read_val:0.5f} uW at ({delx:0.5f}, {dely:0.5f}, {center_coords[2]:0.5f})')
                
    print(f'** Position of maximum PD power: {cur_max_pos}')
    print(f'** Max Power = {cur_max_val}')
    
    # set FAM to position for center of scan
    xAxis.set_D_POS(center_coords[0])
    yAxis.set_D_POS(center_coords[1])
    if moveZ:
        zAxis.set_D_POS(center_coords[2])
    print(f"FAM set to: ({center_coords[0]:0.5f}, {center_coords[1]:0.5f}, {center_coords[2]:0.5f}) ")

    # Disconnect from FAM
    controller.stop()
    # The library never resets its stop_thread flag, so we do it explicitly so that we can reconnect later
    controller.get_communication().stop_thread = False
    print("** Disconnected from FAMs")

    return pd_reads, center_coords, deltas


def redPM_Z(start, stop, nsteps, center_coords=None, pause=0.0, nread=NREAD_DFLT):
    # Example Usage: pd_reads, center_coords, deltas = FAM_Scans.redPM_Z(-0.1, 0.1, 80, center_coords=[-7.65, -0.03, 7.79], pause=0.0, nread=10)

    # Prealloc output array
    pd_reads = np.full((nsteps),np.nan)

    # Connect to xeryon controller
    print(f"** Connecting to controller")
    controller.start(do_reset = False, auto_send_settings=False)
    time.sleep(3)
    print(f"** Connected to: {COM_PORT}")

    # Format the array of positions to step through
    moveXY = True   # Flag to note if new XY position was requested
    if center_coords is None:
        moveXY = False   # No need to move XY since we're using current coords as centerpoint
        # Get current position
        center_coords = []
        for axis in ordered_axis_list:
            center_coords.append(axis.get_EPOS())
    deltas = np.linspace(start, stop, nsteps)
    delzs = deltas+center_coords[2]

    # Check Xeryon reference state, and reference if needed
    for axis in controller.get_all_axis():
        axis_letter = axis.get_letter()
        axis_dir    = LETTER_MAP[axis_letter]
        # Check reference state
        resp = axis.is_encoder_valid()
        # Reference if needed
        if not resp:
            print(f"** REFERENCING {axis_dir} Axis...")
            # TODO: forceWaiting doesn't seem to work right now. Must fix
            axis.find_index(forceWaiting = True)
            # Add a small sleep for now to account for issue with forceWaiting
            time.sleep(2)   # TODO:: Remove this sleep
            if not axis.is_encoder_valid():
                print(f"** Failed to reference {axis_dir} Axis ('{axis_letter}')!")
                controller.stop()
                print(f"** Disconnected from controller due to this reference failure")
                raise RuntimeError(f"Failed to reference {axis_dir} Axis ('{axis_letter}')")
            else:
                print(f"** {axis_dir} Axis successfully referenced")

    # Set XY Position
    if moveXY:
        xAxis.set_D_POS(center_coords[0])
        print(f"FAM moved to X = {center_coords[0]}")
        yAxis.set_D_POS(center_coords[1])
        print(f"FAM moved to Y = {center_coords[1]}")
    else:
        print(f"Using starting X position ({center_coords[0]})")
        print(f"Using starting Y position ({center_coords[1]})")

    # Perform scan (X/Y only)
    cur_max_val = -9999  
    cur_max_pos = [center_coords[0], center_coords[1], np.nan]
    with redPM_cmds.redPM_cmds() as pd:
        for zind, delz in enumerate(delzs):
            print(f"** Moving to Z = {delz:0.5f}")
            zAxis.set_D_POS(delz)

            # Wait to make sure all stages have settled in position
            t0 = time.time()
            while xAxis.is_motor_on() or yAxis.is_motor_on() or zAxis.is_motor_on():
                if ( time.time() - t0 ) > MOV_TIMEOUT :
                    print(f"** WARN: Move in at least 1 of the axes failed to complete within {MOV_TIMEOUT} seconds... proceeding to next step")
                time.sleep(0.05)

            # Give time for PD to settle
            time.sleep(pause)

            # Read power and process measurement
            read_val = pd.read_pd(nread) * redPM_cmds.redPM_cmds.PD_uW_CONVERSION
            pd_reads[zind] = read_val
            if read_val > cur_max_val:
                cur_max_val = read_val
                cur_max_pos[2] = [delz]
                print(f'==> New Max Power = {read_val:0.5f} uW at ({center_coords[0]:0.5f}, {center_coords[1]:0.5f}, {delz:0.5f})')
                
    print(f'** Position of maximum PD power: {cur_max_pos}')
    print(f'** Max Power = {cur_max_val}')
    
    # set FAM to position for center of scan
    if moveXY:
        xAxis.set_D_POS(center_coords[0])
        yAxis.set_D_POS(center_coords[1])
    zAxis.set_D_POS(center_coords[2])
    print(f"FAM set to: ({center_coords[0]:0.5f}, {center_coords[1]:0.5f}, {center_coords[2]:0.5f}) ")

    # Disconnect from FAM
    controller.stop()
    # The library never resets its stop_thread flag, so we do it explicitly so that we can reconnect later
    controller.get_communication().stop_thread = False
    print("** Disconnected from FAMs")


    return pd_reads, center_coords, deltas
