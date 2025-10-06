import numpy as np
import matplotlib.pyplot as plt

# Enable interactive plotting from the start
plt.ion()


def plot_2D_scan(pd_reads, deltas, center_coords, isPlotLog=False):
    '''Function to plot a 2D scan

    Example: plotres = tools.plot_2D_scan(pd_reads, deltas, center_coords)
    '''
    title_prefix = '2D Coupling'
    if len(center_coords) ==2:
        # Assume this is an FSM scan
            # Use mrad for title
        title_coords = f'\nCenter = ({center_coords[0]:0.3f} , {center_coords[1]:0.3f}) mrad'
        # Rest of units will be urad
        units = 'urad'
    else:
        # Assume this is a FAM scan
            # use mm for title
        title_coords = f'\nCenter = ({center_coords[0]:0.4f} , {center_coords[1]:0.4f}, {center_coords[2]:0.4f}) mm'
        # Rest of units will be um
        units = 'um'

    # Rescale the spatial units to urad or um
    scale = 1e3
    
    if isPlotLog:    
        fig, (ax_lin, ax_log) = plt.subplots(1,2, figsize=(11,4.91))
        plt.tight_layout()
    else:
        fig, (ax_lin) = plt.subplots(1,1, figsize=(5.5,4.62))
    pcm = ax_lin.imshow(pd_reads.T, origin='lower', extent=[deltas[0]*scale, deltas[-1]*scale, deltas[0]*scale, deltas[-1]*scale])
    ax_lin.set_title(title_prefix + title_coords)
    ax_lin.set_ylabel('Y-Displacement ['+units+']')
    ax_lin.set_xlabel('X-Displacement ['+units+']')
    fig.colorbar(pcm, ax=ax_lin)

    if isPlotLog:
        pcm = ax_log.imshow(np.log10(pd_reads.T), origin='lower', extent=[deltas[0]*scale, deltas[-1]*scale, deltas[0]*scale, deltas[-1]*scale])
        ax_log.set_title(title_prefix + '(log10)' + title_coords)
        ax_lin.set_ylabel('Y-Displacement ['+units+']')
        ax_lin.set_xlabel('X-Displacement ['+units+']')
        fig.colorbar(pcm, ax=ax_log)

    return fig
 

def plot_1D_scan(pd_reads, deltas, center_coords, isPlotLog=False):
    '''Function to plot a 1D scan

    Example: plotres = tools.plot_1D_scan(pd_reads, deltas, center_coords)
    '''
    scale = 1e3
    
    if isPlotLog:    
        fig, (ax_lin, ax_log) = plt.subplots(1,2, figsize=(11,4.91))
    else:
        fig, (ax_lin) = plt.subplots(1,1, figsize=(5.5,4.62))
    ax_lin.plot(deltas*scale, pd_reads, '-o')
    ax_lin.set_title(f'1D Coupling\nCenter = ({center_coords[0]:0.3f} , {center_coords[1]:0.3f}, {center_coords[2]:0.3f}) mm')
    ax_lin.set_xlabel('Z-Displacement [um]')
    ax_lin.set_ylabel('Power [uW]')

    if isPlotLog:
        ax_log.semilogy(deltas*scale, pd_reads, '-o')
        ax_log.set_title(f'1D Coupling \nCenter = ({center_coords[0]:0.3f} , {center_coords[1]:0.3f}, {center_coords[2]:0.3f}) mm')
        ax_log.set_xlabel('Z-Displacement [um]')
        ax_log.set_ylabel('Power [uW]')

    plt.tight_layout()
    
    return fig