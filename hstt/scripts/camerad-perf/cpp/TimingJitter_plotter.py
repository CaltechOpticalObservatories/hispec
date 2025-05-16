import numpy as np
import matplotlib.pyplot as plt

# Conversions
NS2US   = 1e-3
NS2SEC  = 1e-9

# User Inputs
filename    = "JitterResults/250326_Try10.csv"
isPlot      = True      # Flag to plot the results

# Load the data
timestamps = np.genfromtxt(filename)
timedeltas = np.diff(timestamps) * NS2US

# Compute statistics
STD     = np.std(timedeltas)
Mean    = np.mean(timedeltas)

######## Printed statistics
print(f'\nSamples: {len(timestamps)} | STD: {STD:0.3f} us | Mean: {Mean:0.3f} us')

# Check if any timedeltas were far out of form (major outliers)
outSig = 8      # tolerance for outliers (number of +sigma from mean)
outliers = np.where(timedeltas > Mean + outSig*STD)[0]
if len(outliers):
    print(f"{len(outliers)} outliers (+{outSig} sigma) were found in loop delta:")
    for outlier in outliers:
        print(f"\tInd: {outlier} | Delta: {timedeltas[outlier]} us")

    print('Excluding the outliers, our stats improve to:')
    inForm = np.delete(timedeltas, outliers)
    print(f'Samples: {len(inForm)+1} | STD: {np.std(inForm):0.3f} us | Mean: {np.mean(inForm):0.3f} us')

######## Plotted statistics
if isPlot:
    plt.ion()
    
    # A 0-referenced time vector for X axis of plots (in seconds)
    timeXAx = (timestamps-timestamps[0]) * NS2SEC

    '''
    plt.figure()
    plt.plot(np.arange(len(timedeltas)), timedeltas, 'o', markersize=2)
    plt.title(f'Time Deltas\nSamples: {len(timestamps)} | STD: {STD:0.3f} us | Mean: {Mean:0.3f} us')
    plt.xlabel('Loop Iteration')
    plt.ylabel('Loop Time [us]')

    plt.figure()
    plt.hist(timedeltas, bins=100)
    plt.xlabel('Loop Time [us]')
    plt.ylabel('Occurrences')
    '''

    fig, axs = plt.subplots(2,2, figsize=(8.6, 7.7))

    # Loop Time vs Iteration Full
    axs[0,0].plot(timedeltas, 'o', markersize=2)
    axs[0,0].set_title('Full Scale')
    axs[0,0].set_xlabel('Loop Iteration'); axs[0,0].set_ylabel('Runtime [us]')

    # Loop Time Histogram Full
    axs[0,1].hist(timedeltas, bins=20)
    axs[0,1].set_title('Full Scale')
    axs[0,1].set_xlabel('Loop Time [us]'); axs[0,1].set_ylabel('Occurrences')

    # Loop Time vs Iteration Full
    axs[1,0].plot(timedeltas, 'o', markersize=2)
    axs[1,0].set_title('Zoom In')
    axs[1,0].set_xlabel('Loop Iteration'); axs[1,0].set_ylabel('Runtime [us]')
    axs[1,0].set_ylim(300,700)

    # Loop Time Histogram Full
    axs[1,1].hist(timedeltas, bins=20)
    axs[1,1].set_title('Zoom In')
    axs[1,1].set_xlabel('Loop Time [us]'); axs[1,1].set_ylabel('Occurrences')
    axs[1,1].set_ylim(0, 100)


    fig.suptitle(f'ZMQ Reciever End\nStatistics - STD={np.std(timedeltas):0.2f}us Mean={timedeltas.mean():0.2f}us')
    plt.tight_layout()