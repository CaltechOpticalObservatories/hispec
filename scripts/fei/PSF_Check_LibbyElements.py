#!/home/hsdev/venv/bin/python3
'''
This code checks that all libby-enabled modules are in the correct (default) positions for a PSF check
If a module is not in position, it asks the user whether they'd like to move it into position
At the end, the script clearly reports whether or not all modules ended up in position.

The core part of this code is also available as a function so that other programs can access this capability.
'''
from libby import Client
import numpy as np
import time
import argparse

#----- Inputs
VERBOSE = False  # Default verbosity setting

DEF_POS_TOL = 0.001 # Default position tolerance (in stage-native units)
# Dictionary of module positions. Include position keyword and value
DEFAULT_POSITIONS = {
    'LSM'   :  {'positionvalueh'    : 2.643, 
                'positionvaluev'    : 22.603},
    'MS'    :  {'positionvalueh'    : 1.8,
                'positionvaluev'    : 33.62},
    # -- ADC commented out until Daemon is available --
    # 'ADC'   :  {'positionvalue1'    : 0.0,
    #            'poistionvalue2'    : 0.0},
    'ATCP'  :  {'positionvalue'     : 65.98},
    'ATCFW' :  {'positionvalue'     : 1},
    'ATCL'  :  {'positionvalue'     : 7.15}
}

# Dictionary of module names as known by libby
    # these will be prepended to the position keywords
DEF_FEI_PREFIX = 'hsfei'    
MODULE_DAEMONS = {
    'LSM'   : DEF_FEI_PREFIX + ".lsm",
    'MS'    : DEF_FEI_PREFIX + ".ms",
    'ADC'   : DEF_FEI_PREFIX + ".adc",
    'ATCP'  : DEF_FEI_PREFIX + ".atcp",
    'ATCFW' : DEF_FEI_PREFIX + ".atcfw",
    'ATCL'  : DEF_FEI_PREFIX + ".atcl"
}

# Define the default keyword used to check if a stage is moving
    # Note: the suffix for multi-axis modules is appended based on the last char of the positionvalue keyword
DEF_ISMOVING = 'ismoving'

# Define a set of modules to exclude from the ismoving blocking move feature
NO_ISMOVING_MODULES = set([
    'ATFCW'
])

# Define timeout for moves
MOVE_TIMEOUT = 30   # [seconds] 
# Define interval for sampling whether move has completed
DEF_MOVE_BLOCK_TICK_INTERVAL = 0.2  # [seconds] 

#----- Define helper functions
def vprint(message, verbose=VERBOSE):
    '''Function to only print when verbosity is set to true'''
    if verbose:
        print(message)

def position_formatter(position_list):
    '''
    Function to format a string with the module positions
    This handles when single- and multi-axis modules

    Arg:
        position_list : list of position values for a given module
            NOTE: even single-axis modules must be provided as a one-element list
    Ret:
        a string with the positions for a given module
        If sinlge-axis module:
            gives just the position value number
        If multi-axis module:
            gives something like (X, Y, ...)
    '''
    # Populate first element of the position string
    position_str = f'{position_list[0]:0.3f}'
    if len(position_list) == 1:
        # Since this is a single-axis module, return with no additional formatting
        return position_str

    # Add other axis positions with comma separation
    for pos in position_list[1:]:
        position_str += f', {pos:0.3f}'

    # Surround multi-axis positions by parentheses, then return
    return '(' + position_str + ')'

def check_position_within_tolerance(interface, full_position_keyword, goal_position, tolerance=DEF_POS_TOL):
    '''
    Function to query a position from a module and check if it is within tolerance

    Arg:
        interface : open instance of libby client
        full_position_keyword : full keyword to query with libby (ex. hsfei.atcp.positionvalue)
        goal_position : goal value for the given keyword
        tolerance : (optional) tolerance range for the keyword (Default = DEF_POS_TOL)
    Ret:
        (is_within_tol, current_position)
        is_within_tol : bool - True if current_position is within tolerance
        current_position : value returned by libby
    '''
    current_position = interface.get(full_position_keyword)
    
    if np.abs(current_position - goal_position) <= tolerance:
        is_within_tol = True
    else:
        is_within_tol = False
    
    return (is_within_tol, current_position)
    

#----- Main Function: Iterate through modules checking position
def check_default_positions(verbose=VERBOSE, move_mode='prompt'):
    '''
    Function to run the position check

    Iterates through all modules, checks their position against the default, and moves them to position if desired

    Arg:
        verbose : sets verbosity for the function
        move_mode : one of 'prompt', 'auto-move', 'do-not-move'
            'prompt'        will prompt the user whenever a module is not in position
            'auto-move'     automatically moves the stages into position if needed
            'do-not-move'   keeps stages wherever they are, even if not in position
    Ret:
        (all_in_pos, modules_in_pos, final_positions)
        all_in_pos  : bool - True if all modules are in position
        modules_in_pos  : dict of modules with True/False whether each module is in position
        final_positions : dict with final positions for all modules
    '''
    move_mode_options = ['prompt', 'auto-move', 'do-not-move']
    assert move_mode in move_mode_options, f"move_mode must be one of {move_mode_options}, but got {move_mode}"

    # Start the libby interface
    interface = Client.rabbitmq()

    # Preallocate dict to hold whether any module didn't end up in the final goal position
        # This should only happen if user choose 'no' to moving a module that is out of position
    in_position = {module: True for module in DEFAULT_POSITIONS.keys()}

    # Preallocate a dict to hold where all the modules ended up
    final_positions ={module: {} for module in DEFAULT_POSITIONS.keys()}

    # Check each module
    for module, positions in DEFAULT_POSITIONS.items():
        vprint(f"Checking that {module:>7s} is at {position_formatter(list(positions.values()))}", verbose=verbose)
        # Note whether this is a multi-axis module
        is_multi_axis = len(positions) > 1

        # Check each position/axis, 1 at a time
        for axis_keyword, position in positions.items():
            # Format the full keyword
            full_position_keyword = MODULE_DAEMONS[module] + "." + axis_keyword

            # Get current position
            (is_within_tol, current_position) = check_position_within_tolerance(interface, full_position_keyword, position)
            final_positions[module][axis_keyword] = current_position
            vprint(f"  {module} is currently at {axis_keyword} = {current_position}", verbose=verbose)

            # Check if current position is within tolerance of goal
            if is_within_tol:
                # current position is within tolerance, so notify (optionally) and move on
                vprint(f"    current position is  within {DEF_POS_TOL} of the goal position ({position})", verbose=verbose)
                continue
            
            # current position is beyond tolerance of goal
            print(f"** {module} {axis_keyword} is >{DEF_POS_TOL} from goal position ({current_position} vs. {position}) ")

            if move_mode == 'prompt':
                # Check with user whether they'd like to move the stage
                move_input = input(f"Would you like to move it to the goal position ({position})? ([y]es/[n]o):\n\t")

                if 'y' in move_input.lower():
                    do_move = True
                elif 'n' in move_input.lower():
                    do_move = False
                else:
                    interface.close()
                    raise ValueError(f"Invalid input recieved to move question. Received {move_input} but should be 'y'/'n' or 'yes'/'no'")
            elif move_mode == 'auto-move':
                do_move = True
            elif move_mode == 'do-not-move':
                do_move = False

            if do_move:
                # User has chosen to move the stage, so let's do that
                vprint(f"** Moving {module} to {axis_keyword} = {position}. Will wait up to {MOVE_TIMEOUT} seconds for move to complete", verbose=verbose)
                interface.set(full_position_keyword, position)

                # Wait for the module to complete its move, assuming it has a keyword we can spin on
                if module in NO_ISMOVING_MODULES:
                    # In this case, the module has no ismoving keyword, so just sleep briefly, then proceed
                        # This is basically just for the ATCFW...
                    time.sleep(DEF_MOVE_BLOCK_TICK_INTERVAL)
                else:
                    # Figure out what ismoving keyword to spin on
                    full_ismoving_keyword = MODULE_DAEMONS[module] + "." + DEF_ISMOVING
                    if is_multi_axis:
                        # Since stage is multi-axis, get the axis suffix from the positionvalue* keyword and append it
                        suffix = axis_keyword[-1]
                        full_ismoving_keyword += suffix

                    # Spin until stage stops moving or until timeout is reached
                    blocking_start_time = time.time()
                    tick_count = 0
                    while interface.get(full_ismoving_keyword):
                        elapsed_time = time.time() - blocking_start_time
                        # check if we've exceeded the timeout
                        if elapsed_time > MOVE_TIMEOUT:
                            interface.close()
                            raise RuntimeError(f"{module} failed to complete its move within {MOVE_TIMEOUT} seconds")
                        
                        if (tick_count % 5) == 0:
                            print(f"Waiting for {module} to finish moving... ({elapsed_time:0.1f}s elapsed)")

                        # wait 1 tick interval
                        tick_count += 1
                        time.sleep(DEF_MOVE_BLOCK_TICK_INTERVAL)
                
                # Confirm that stage got to the desired position
                (is_within_tol, current_position) = check_position_within_tolerance(interface, full_position_keyword, position)
                if not is_within_tol:
                    interface.close()
                    raise ValueError(f"{module} failed to get within {DEF_POS_TOL} of goal position even after move")
                
                # Update the final positions so we have the latest and greatest value
                final_positions[module][axis_keyword] = current_position

            else:
                # User has chosen NOT to move the stage, so just let them know
                print(f"** NOT moving {module} {axis_keyword} to new position.")

                # Update the fact that the stage did not end up in the goal position
                in_position[module] = False
            
        vprint(f"==> {module:>7s} is at {position_formatter(list(final_positions[module].values()))}", verbose=verbose)

    
    # Clean up the libby interface
    interface.close()

    #----- Give final summary report
    if all(in_position.values()):
        return True, in_position, final_positions
    else:
        return False, in_position, final_positions

if __name__ == '__main__':
    # Format a help string that summarizes the default position for each module
    positions_summary = '\n'.join(
        f"  {module:<9s} : {position_formatter(list(positions.values()))}" 
        for module, positions in DEFAULT_POSITIONS.items()
    )

    parser = argparse.ArgumentParser(
        description='Check that all modules are in default positions for a PSF check.\n\n'
                    + f'Default positions:\n{positions_summary}',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-v', '--verbose', action='store_true', default=VERBOSE,
                        help='Enable verbose output')
    parser.add_argument('-m', '--move-mode', default='prompt',
                        choices=['prompt', 'auto-move', 'do-not-move'],
                        help='What do do when a module is not in position. (default=prompt)')
    parser.add_argument('--no-summary', action='store_true', default=False,
                        help='Suppress the final summary print of stage positions')
    
    args = parser.parse_args()
    (all_in_position, modules_in_position, final_positions) = check_default_positions(verbose=args.verbose, move_mode=args.move_mode)

    if all_in_position:
        print("\nSUCCESS: All libby-enabled modules are in position!\n")
    else:
        for module, is_in_position in modules_in_position.items():
            if is_in_position:
                continue
            print(f"\nWARNING: {module} is NOT in position\n")

    if not args.no_summary:
        print('Final Module Positions:')
        for module, final_position in final_positions.items():
            print(f'  {module:<7s} : {position_formatter(list(final_position.values()))}')