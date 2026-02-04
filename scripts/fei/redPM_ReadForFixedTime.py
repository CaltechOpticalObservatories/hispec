#!/usr/bin/env python3

import time
import csv
import numpy as np
import matplotlib.pyplot as plt
from redPM_cmds import redPM_cmds

# --------------------
# User settings
# --------------------
duration_min = 120.0     # minutes to record
dt = 0.1               # seconds between averaged samples
NREAD = 5              # samples per averaged point
outpath = "/home/hsdev/dechever/AIT_Verification_Data/LaserBankStability/"
outfile = "1510_Stability_HalfPower_LongPeriod3.csv"

# --------------------
# Acquisition
# --------------------
t0 = time.time()
t_end = t0 + duration_min * 60

times = []
powers = []

try:
    with open(outpath+outfile, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "power_uW"])

        with redPM_cmds() as pm:
            while True:
                now = time.time()
                if now >= t_end:
                    break

                t = now - t0
                p = pm.read_pd(NREAD) * redPM_cmds.PD_uW_CONVERSION

                times.append(t)
                powers.append(p)
                writer.writerow([f"{t:.6f}", f"{p:.6f}"])

                remaining = t_end - now
                print(f"\rRunning... {t:6.1f}s elapsed, {remaining:6.1f}s remaining",
                      end="", flush=True)

                time.sleep(dt)

except KeyboardInterrupt:
    print("\nInterrupted by user — saving partial data.")

finally:
    fullpath = outpath+outfile
    print("\nDone. Saved to:", fullpath)

    if times:
        times_np = np.array(times)
        powers_np = np.array(powers)
        mean_p = powers_np.mean()
        std_p = powers_np.std()

        plt.figure()
        plt.plot(times_np, powers_np, label="Power")
        plt.xlabel("Time [s]")
        plt.ylabel("Power [µW]")
        plt.title(outfile)
        plt.grid(True)

        # Show mean ± std as text on plot
        textstr = f"Mean = {mean_p:.3f} µW\nSTD = {std_p:.3f} µW"
        plt.gca().text(0.05, 0.95, textstr, transform=plt.gca().transAxes,
                       fontsize=10, verticalalignment='top',
                       bbox=dict(facecolor='white', alpha=0.7))

        plt.show()
