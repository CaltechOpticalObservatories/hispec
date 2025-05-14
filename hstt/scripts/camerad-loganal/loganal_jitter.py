#!/usr/bin/env python
"""Analyze camerad log files"""
import sys
import datetime
import numpy as np

ofile = sys.argv[1].split('.')[0] + '.dat'
ofn = open(ofile, 'w')

tfmt = "%Y-%m-%dT%H:%M:%S.%f"
nexp = 0
nseq = -1
seqno = 1
in_exposure = False
in_read = False
in_wait = False
prev_archon_ts = None
print("")
with open(sys.argv[1]) as fn:
    lines = fn.readlines()
    for ln in lines:
        ts_str = ln.split()[0]

        if " hroi " in ln:
            # print(ln)
            vstart = int(ln.split()[-4])
            vstop = int(ln.split()[-3])
            hstart = int(ln.split()[-2])
            hstop = int(ln.split()[-1])

        if "FASTLOADPARAM Expose " in ln:
            # print(ln)
            nseq = int(ln.split()[-1])
            nexp = 0
            deltas = []
            rdeltas = []
            wdeltas = []
            successfully_read_ts = []
            archon_ts = []

        if "waiting for new frame:" in ln:
            # print(ln)
            ts_exp_start = datetime.datetime.strptime(ts_str, tfmt)
            in_exposure = True
            in_wait = True

        if "received currentframe:" in ln:
            ts_wait_stop = datetime.datetime.strptime(ts_str, tfmt)
            if in_wait:
                wdeltas.append(ts_wait_stop - ts_exp_start)
                in_wait = False

        if "will read image data" in ln:
            ts_rd_start = datetime.datetime.strptime(ts_str, tfmt)
            frame = int(ln.split()[-1])
            in_read = True

        if "successfully read" in ln:
            if in_read:
                ts_rd_stop = datetime.datetime.strptime(ts_str, tfmt)
                rdeltas.append(ts_rd_stop - ts_rd_start)
                successfully_read_ts.append(ts_rd_stop.timestamp()*1e6)
                in_read = False

        if "READOUT COMPLETE" in ln:
            # print(ln)
            if in_exposure:
                ts_exp_stop = datetime.datetime.strptime(ts_str, tfmt)
                deltas.append(ts_exp_stop - ts_exp_start)
                nexp += 1
                in_exposure = False

        if "Last frame read" in ln:
            last_frame = int(ln.split()[-4])
            if frame == last_frame:
                print("Sequence synced")
            else:
                print("Sequence NOT synced")
        
        if "timestamp in hex" in ln:
            index = ln.find("decimal: ")
            current_ts = int(ln[index + 9:])
            archon_ts.append(current_ts)

        if "READOUT SEQUENCE COMPLETE" in ln:
            if nexp > 1:
                print("\nSequence %d" % seqno)
                print(vstart, vstop, hstart, hstop)
                print(vstop-vstart+1, "x", hstop-hstart+1)
                print(nexp, "out of ", nseq)
                gdelts = deltas[1:]
                d_hz = []
                for d in gdelts:
                    d_hz.append(1.e6/d.microseconds)
                d_hz = np.asarray(d_hz)
                r_hz = []
                for r in rdeltas:
                    r_hz.append(1.e6/r.microseconds)
                r_hz = np.asarray(r_hz)
                w_hz = []
                for w in wdeltas:
                    w_hz.append(1.e6/w.microseconds)
                w_hz = np.asarray(w_hz)

                successfully_read_ts = np.asarray(successfully_read_ts)
                successfully_read_deltas = np.diff(successfully_read_ts)
                archon_deltas = np.diff(archon_ts)

                print(f'Median Loop Time = {np.median(successfully_read_deltas):0.2f} us | Mean Loop Time = {successfully_read_deltas.mean():0.2f} us | Jitter = {np.std(successfully_read_deltas):0.2f} us')


                print("Expos Hz = %.3f +- %.3f" % (np.median(d_hz), d_hz.std()))
                print("Fetch Hz = %.3f +- %.3f" % (np.median(r_hz), r_hz.std()))
                print("Wait  Hz = %.3f +- %.3f" % (np.median(w_hz), w_hz.std()))
                print(f"Archon ts diff median: {np.median(archon_deltas):0.2f} | Mean time {archon_deltas.mean():0.2f} | Jitter = {np.std(archon_deltas):0.2f}")
                ofn.write(
                    "%3d %4d %4d %4d %4d %3d %3d %3d %3d "
                    "%8.3f %8.3f %8.3f %8.3f %8.3f %8.3f\n"
                    % (seqno, vstart, vstop, hstart, hstop,
                       vstop-vstart+1, hstop-hstart+1, nexp, nseq,
                       d_hz.mean(), d_hz.std(), r_hz.mean(), r_hz.std(),
                       w_hz.mean(), w_hz.std()))
                seqno += 1
            else:
                print("Sequence %d" % seqno)
                print(vstart, vstop, hstart, hstop)
                print(vstop - vstart + 1, "x", hstop - hstart + 1)
                print(nexp, "out of ", nseq)
                print("")
                seqno += 1

ofn.close()

## Timing Jitter Plots
import matplotlib.pyplot as plt
plt.ion()

fig, axs = plt.subplots(2,3, figsize=(8.6, 7.7))

# Loop Time vs Iteration Full
axs[0,0].plot(successfully_read_deltas, 'o', markersize=2)
axs[0,0].set_title('Full Scale')
axs[0,0].set_xlabel('Loop Iteration'); axs[0,0].set_ylabel('Runtime [us]')

# Loop Time Histogram Full
axs[0,1].hist(successfully_read_deltas, bins=20)
axs[0,1].set_title('Full Scale')
axs[0,1].set_xlabel('Loop Time [us]'); axs[0,1].set_ylabel('Occurrences')

# Loop Time vs Iteration Full
axs[1,0].plot(successfully_read_deltas, 'o', markersize=2)
axs[1,0].set_title('Zoom In')
axs[1,0].set_xlabel('Loop Iteration'); axs[1,0].set_ylabel('Runtime [us]')
axs[1,0].set_ylim(900, 1200)

# Loop Time Histogram Full
axs[1,1].hist(successfully_read_deltas, bins=20)
axs[1,1].set_title('Zoom In')
axs[1,1].set_xlabel('Loop Time [us]'); axs[1,1].set_ylabel('Occurrences')
axs[1,1].set_ylim(0, 100)

# Loop Time vs Iteration Full
axs[0,2].plot(archon_deltas, 'o', markersize=2)
axs[0,2].set_title('Full Scale Archon times')
axs[0,2].set_xlabel('Loop Iteration'); axs[0,0].set_ylabel('Runtime [us]')


fig.suptitle(f'Camerad Log File\nStatistics - STD={np.std(successfully_read_deltas):0.2f}us Mean={successfully_read_deltas.mean():0.2f}us')
plt.tight_layout()
