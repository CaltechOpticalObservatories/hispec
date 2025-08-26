#####
# Basic tests of the ZMQ-based camerad readout timing
#
# This file is based on xsub-socket.py by Mike
#####

import zmq
import time
import numpy as np
import time
import matplotlib.pyplot as plt

NS2US = 1e-3        # nanosecond to microsecond conversion
NS2SEC = 1e-9       # nanosecond to second conversion

# User Inputs
Nsamp = 5000       # Size of preallocated timestamps array (max number of samples)
isPrint = False     # Flag to print receive messages to terminal
isPlot = True       # Flag to plot the results

def main():
    # Create a ZeroMQ context
    context = zmq.Context()

    # Create a PULL socket
    socket = context.socket(zmq.XSUB)

    # Bind the socket to port 5555
    socket.connect("tcp://localhost:5555")

    # Subscribe to all topics
    socket.send(b'\x01')
    print("Listening for messages on port 5555...")

    # Preallocate array to hold msg read timestamps
    timestamps = np.empty(Nsamp, dtype=int)
    ctr = 0

    # Continuously listen for incoming messages
    try:
        while True:
            try:
                message = socket.recv()
                timestamps[ctr] = time.perf_counter_ns()
                if isPrint: 
                    print(f'Time: {timestamps[ctr]} - Raw data:  {message}')

            except zmq.Again:
                timestamps[ctr] = -1*time.perf_counter_ns()
                time.sleep(5)
                # print("Waiting for messages...")
            
            ctr += 1
            # Bailout if the next read will exceed user-requested samples
            if ctr >= Nsamp:
                ctr -= 1
                break
    except KeyboardInterrupt as e:
        print('Ctrl-C detected --- exiting reader loop')

    return timestamps[:ctr]

if __name__ == "__main__":
    timestamps = main()
    timedeltas = np.diff(timestamps) * NS2US

    # Compute statistics
    STD     = np.std(timedeltas)
    Mean    = np.mean(timedeltas)
    Median   = np.median(timedeltas)

    ######## Printed statistics
    if any(timestamps < 0):
        Nneg = np.count_nonzero(timestamps<0)
        print(f"\nWARNING:::\n\t{Nneg} timestamps were negative, meaning recv failed sometimes")

    print(f'\nSamples: {len(timestamps)} | STD: {STD:0.3f} us | Mean: {Mean:0.3f} us | Media: {Median:0.3f}')

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

        plt.figure()
        plt.plot(np.arange(len(timedeltas)), timedeltas, 'o', markersize=2)
        plt.title(f'Time Deltas\nSamples: {len(timestamps)} | STD: {STD:0.3f} us | Mean: {Mean:0.3f} us')
        plt.xlabel('Loop Iteration')
        plt.ylabel('Loop Time [us]')

        plt.figure()
        plt.hist(timedeltas, bins=10)
        plt.xlabel('Loop Time [us]')
        plt.ylabel('Occurrences')