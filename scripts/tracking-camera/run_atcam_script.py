#!/usr/bin/env python3
"""
Take ATC exposures through the hsfei.atcam daemon.

The keyword counterpart of run_camerad_script.py: the same acquisition styles
and short options, but every step is a keyword write through the broker, so it
runs while the daemon holds the Archon and from any host that reaches the
broker.

  counted   default; --frames per sequence, --repeat sequences
  autofetch --autofetch; --frames pushed by the Archon unsolicited
  freerun   --freerun; one continuous session until --seconds or Ctrl-C

    run_atcam_script.py -m guiding -e rx -r 10 -a -n 300

The broker credentials come from HISPEC_RABBITMQ_USER and
HISPEC_RABBITMQ_PASSWORD, as for the daemons:

    set -a; . /etc/hispec/secrets.env; set +a
"""

import argparse
import signal
import time

from libby import Client

from hispec.daemon import broker_url
from hispec.driver.tracking_camera import ReadMode

DAEMON = "hsfei.atcam"
DETECTOR_PIXELS = 2048
# A 10x10 window reads out in about 1 ms, far faster than a non-autofetch
# fetch; the controller then overruns the host and leaves data unread
MIN_NON_AUTOFETCH_ROI = 50
# The Archon allocates a 16k network write buffer per connection and will not
# transmit a frame that does not fit
MAX_AUTOFETCH_BYTES = 16384
AUTOFETCH_HEADER_LEN = 36
BYTES_PER_PIXEL = 2
# Every frame carries the exposure and its reset image side by side
FRAME_WIDTH_FACTOR = 2

# Mode and geometry writes reprogram the controller, which outlasts the
# client's default RPC timeout
WRITE_TIMEOUT_S = 30.0
INITIALIZE_TIMEOUT_S = 300.0
POLL_S = 0.5
STOP_CHECK_S = 4.0
STATE_IDLE = "idle"
STATE_ERROR = "error"
BUSY_STATES = ("exposing", "aborting")


class Atcam:
    """Read and write one daemon's keywords by their bare names."""

    def __init__(self, client: Client, daemon: str) -> None:
        self.client = client
        self.daemon = daemon

    def get(self, name):
        """Return a keyword's value."""
        return self.client.get(f"{self.daemon}.{name}")

    def set(self, name, value, timeout_s=WRITE_TIMEOUT_S):
        """Write a keyword, raising if the daemon rejects it."""
        return self.client.set(f"{self.daemon}.{name}", value, timeout_s=timeout_s)

    def trigger(self, name, timeout_s=WRITE_TIMEOUT_S):
        """Fire a trigger keyword."""
        self.set(name, True, timeout_s=timeout_s)

    def ensure(self, name, value):
        """Write a keyword only if it differs, since some writes act on the camera."""
        if self.get(name) != value:
            self.set(name, value)

    def wait_idle(self, timeout_s=None):
        """Wait for the run to settle; raise if it ends in error or times out."""
        deadline = None if timeout_s is None else time.monotonic() + timeout_s
        while (state := self.get("state")) in BUSY_STATES:
            if deadline is not None and time.monotonic() > deadline:
                raise SystemExit(f"{self.daemon} still {state} after {timeout_s:.0f}s")
            time.sleep(POLL_S)
        if state != STATE_IDLE:
            raise SystemExit(f"{self.daemon} ended in state {state}; "
                             f"lasterror: {self.get('lasterror')}")


def parse_args():
    """Parse the command line."""
    parser = argparse.ArgumentParser(description="Take ATC exposures through hsfei.atcam.")
    parser.add_argument("-d", "--daemon", default=DAEMON, help="Camera daemon address")
    parser.add_argument("--init", action="store_true",
                        help="Run initialize first: open, load firmware and power on")
    parser.add_argument("-t", "--exptime", type=float, default=0, help="Exposure time, s")
    parser.add_argument("-m", "--mode", type=str, default="guiding",
                        choices=("roi", "guiding", "fullframe"), help="Subframe mode")
    parser.add_argument("-e", "--exposure", type=str, default="rxr",
                        choices=tuple(m.value for m in ReadMode), help="Readout mode")
    parser.add_argument("-r", "--roi", type=int, default=618,
                        help="Square window size; ignored for fullframe")
    parser.add_argument("-w", "--window", type=int, nargs=4,
                        metavar=("Y0", "Y1", "X0", "X1"),
                        help="Guiding window as inclusive bounds; a centred "
                             "--roi square if omitted")
    parser.add_argument("-a", "--autofetch", action="store_true",
                        help="Stream frames unsolicited; needs a small window")
    parser.add_argument("-f", "--freerun", action="store_true",
                        help="Run continuously instead of taking counted frames")
    parser.add_argument("-s", "--seconds", type=float, default=0.0,
                        help="With --freerun, how long to run; 0 means until Ctrl-C")
    parser.add_argument("-n", "--frames", type=int, default=3,
                        help="Frames to acquire; reads per sequence for UTR")
    parser.add_argument("-R", "--repeat", type=int, default=1,
                        help="Times to repeat a counted sequence")
    parser.add_argument("-p", "--pause", type=float, default=0,
                        help="Seconds to pause between sequences")
    return parser.parse_args()


def guiding_bounds(args):
    """Return the window's inclusive bounds, a centred --roi square by default."""
    if args.window is not None:
        return tuple(args.window)
    low = DETECTOR_PIXELS // 2 - args.roi // 2
    high = low + args.roi - 1
    return low, high, low, high


def window_shape(args):
    """Return the window's rows and columns, however it was specified."""
    y0, y1, x0, x1 = guiding_bounds(args)
    return y1 - y0 + 1, x1 - x0 + 1


def check_args(args):
    """Refuse what run_camerad_script.py refuses, before touching the camera."""
    if args.window is not None:
        if args.mode != "guiding":
            raise SystemExit(f"--window places a guiding window, but --mode is {args.mode}")
        y0, y1, x0, x1 = args.window
        if y1 < y0 or x1 < x0:
            raise SystemExit(f"--window bounds are inclusive and ascending, "
                             f"so Y1 >= Y0 and X1 >= X0; got {args.window}")
        if y0 < 0 or x0 < 0 or y1 >= DETECTOR_PIXELS or x1 >= DETECTOR_PIXELS:
            raise SystemExit(f"--window {args.window} runs off the "
                             f"{DETECTOR_PIXELS} pixel detector")
    if args.mode == "fullframe":
        return
    if args.autofetch:
        rows, cols = window_shape(args)
        frame_bytes = (AUTOFETCH_HEADER_LEN
                       + rows * cols * FRAME_WIDTH_FACTOR * BYTES_PER_PIXEL)
        if frame_bytes >= MAX_AUTOFETCH_BYTES:
            raise SystemExit(f"a {rows}x{cols} window gives {frame_bytes} byte frames; "
                             f"autofetch needs under {MAX_AUTOFETCH_BYTES}")
        return
    smallest = min(window_shape(args)) if args.mode == "guiding" else args.roi
    if smallest < MIN_NON_AUTOFETCH_ROI:
        raise SystemExit(f"a {smallest} pixel axis outruns a non-autofetch readout; "
                         f"use --autofetch or keep every axis at "
                         f"{MIN_NON_AUTOFETCH_ROI} or more")


def configure(atcam, args):
    """Apply the subframe mode, readout mode, geometry and exposure settings."""
    if args.init:
        atcam.trigger("initialize", timeout_s=INITIALIZE_TIMEOUT_S)
    atcam.wait_idle()
    atcam.ensure("autofetch", False)
    atcam.ensure("freerun", False)
    atcam.set("datacube", args.exposure in ("utr_rr", "utr_gr"))

    # subframemode reselects the ACF section, so it goes before the geometry
    atcam.set("subframemode", args.mode)
    atcam.set("readmode", args.exposure)
    if args.mode == "guiding":
        atcam.set("guidingroi", " ".join(str(b) for b in guiding_bounds(args)))
    elif args.mode == "roi":
        atcam.set("subframeheight", args.roi)
        atcam.set("subframewidth", args.roi)
    atcam.set("exptime", args.exptime)
    print(f"{atcam.daemon}: {args.mode} {args.exposure}, geometry "
          f"{atcam.get('guidingroi')} ({atcam.get('geometrystatus')})")


def run_counted(atcam, args):
    """Take the requested frames, repeated as asked."""
    atcam.set("nframes", args.frames)
    for sequence in range(args.repeat):
        atcam.trigger("expose")
        atcam.wait_idle()
        print(f"sequence {sequence + 1} of {args.repeat} complete: {atcam.get('lastframe')}")
        if args.pause:
            time.sleep(args.pause)


def ignore_interrupts():
    """Ignore further Ctrl-C, which would leave the detector streaming."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    print("stopping (interrupts ignored until the detector is idle)")


def stop_autofetch_run(atcam):
    """End a counted autofetch run early.

    Abort before disarming, so the daemon records the run as aborted rather
    than failed when disarming ends it.
    """
    ignore_interrupts()
    atcam.trigger("abort")
    atcam.set("autofetch", False)
    atcam.wait_idle(timeout_s=WRITE_TIMEOUT_S)


def stop_freerun(atcam, args):
    """End a freerun session: disarm the push first, then abort the loop."""
    ignore_interrupts()
    if args.autofetch:
        atcam.set("autofetch", False)
    atcam.trigger("abort")
    atcam.wait_idle(timeout_s=WRITE_TIMEOUT_S)


def run_autofetch(atcam, args):
    """Stream the requested frames with the Archon pushing them unsolicited."""
    atcam.set("nframes", args.frames)
    atcam.set("autofetch", True)
    start_count = atcam.get("frameswritten")
    started = time.monotonic()
    atcam.trigger("expose")
    print(f"autofetch running, {args.frames} frames; Ctrl-C to stop")
    try:
        atcam.wait_idle()
    except KeyboardInterrupt:
        print("\ninterrupted")
        stop_autofetch_run(atcam)
    else:
        atcam.set("autofetch", False)
    elapsed = time.monotonic() - started
    frames = atcam.get("frameswritten") - start_count
    print(f"{frames} frames in {elapsed:.2f}s = {frames / elapsed:.1f} fps")


def run_freerun(atcam, args):
    """Stream continuously until the duration elapses or Ctrl-C."""
    if args.autofetch:
        atcam.set("autofetch", True)
    atcam.set("freerun", True)
    start_count = atcam.get("frameswritten")
    atcam.trigger("expose")
    print(f"freerun running{' with autofetch' if args.autofetch else ''}; Ctrl-C to stop")
    start = time.monotonic()
    try:
        while args.seconds <= 0 or time.monotonic() - start < args.seconds:
            time.sleep(1.0)
            print(f"  t={time.monotonic() - start:5.1f}s "
                  f"frames={atcam.get('frameswritten') - start_count}")
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        stop_freerun(atcam, args)
        before = atcam.get("frameswritten")
        time.sleep(STOP_CHECK_S)
        if atcam.get("frameswritten") == before:
            print(f"stopped: no new frames over {STOP_CHECK_S:.0f}s")
        else:
            print("WARNING: STILL STREAMING, the detector did not stop")
        atcam.set("freerun", False)


def main():
    """Configure the camera through the daemon, then acquire."""
    args = parse_args()
    check_args(args)
    with Client.rabbitmq(rabbitmq_url=broker_url()) as client:
        atcam = Atcam(client, args.daemon)
        configure(atcam, args)
        if args.freerun:
            run_freerun(atcam, args)
        elif args.autofetch:
            run_autofetch(atcam, args)
        else:
            run_counted(atcam, args)


if __name__ == "__main__":
    main()
