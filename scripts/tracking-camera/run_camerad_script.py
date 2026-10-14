#!/usr/bin/env python3
"""
Take ATC exposures through the camera_interface bindings.

Does what the socksend version of this script does, but drives the camera in
process, so there is no shell round trip and a failed command raises instead
of printing a return code.

Two acquisition styles:

  counted   default; --frames per sequence, --repeat sequences
  freerun   --freerun; one continuous session until --seconds or Ctrl-C
  autofetch --autofetch; --frames pushed by the Archon unsolicited

A window below 50x50 produces faster than anything but autofetch can read, so
the other two modes refuse one.

Needs hispec and the per-instrument bindings in the environment running it:

    pip install <hispec checkout>
    pip install <camera-interface>/packaging/tracking

The camerad .cfg comes from --config, else $CAMERAD_CONFIG, else the ATC
config in the checkout named by DEFAULT_CONFIG below. The InfluxDB token comes
from $INFLUXDB_TOKEN; the detector temperature falls back to a default if it
is unset or the query fails.
"""

import argparse
import os
import re
import signal
import threading
import time

from hispec.driver.tracking_camera import ReadMode, TrackingCamera

# Used when neither --config nor $CAMERAD_CONFIG is given
DEFAULT_CONFIG = "/home/hsdev/atcam/etc/hispecatc.cfg"

DETECTOR_PIXELS = 2048
# A 10x10 window reads out in about 1 ms, far faster than a non-autofetch
# fetch; the controller then overruns the host and leaves data unread
MIN_NON_AUTOFETCH_ROI = 50
STOP_CHECK_S = 4.0
DEFAULT_TEMPERATURE_K = 99.9
INFLUX_URL = "hispec.caltech.edu:8086"
INFLUX_ORG = "caltech"
DETTEMP_QUERY = (
    'from(bucket: "HISPEC") |> range(start: -30s) '
    '|> filter(fn: (r) => r["_field"] == "tA_detector")'
)


def parse_args():
    """Parse the command line."""
    parser = argparse.ArgumentParser(description="Take ATC exposures.")
    parser.add_argument("--config",
                        default=os.environ.get("CAMERAD_CONFIG", DEFAULT_CONFIG),
                        help="camerad .cfg file; defaults to $CAMERAD_CONFIG "
                             "then to the ATC config")
    parser.add_argument("--exptime", type=float, default=0,
                        help="Exposure time, in the unit LONGEXPOSURE selects")
    parser.add_argument("--mode", type=str, default="guiding",
                        choices=("roi", "guiding", "fullframe"), help="Subframe mode")
    parser.add_argument("--exposure", type=str, default="rxr",
                        choices=tuple(m.value for m in ReadMode), help="Readout mode")
    parser.add_argument("--roi", type=int, default=618,
                        help="Square window size, centred; ignored for fullframe")
    parser.add_argument("--imtype", type=str, default="TEST", help="Image type")
    parser.add_argument("--observer", type=str, default="", help="OBSERVER header value")
    parser.add_argument("--autofetch", action="store_true",
                        help="stream frames unsolicited; needs a small window")
    parser.add_argument("--freerun", action="store_true",
                        help="Run continuously instead of taking counted frames")
    parser.add_argument("--seconds", type=float, default=0.0,
                        help="With --freerun, how long to run; 0 means until Ctrl-C")
    parser.add_argument("--frames", type=int, default=3,
                        help="Frames to acquire; reads per sequence for UTR")
    parser.add_argument("--repeat", type=int, default=1,
                        help="Times to repeat a counted sequence")
    parser.add_argument("--pause", type=float, default=0,
                        help="Seconds to pause between sequences")
    return parser.parse_args()


def detector_temperature():
    """Return the detector temperature, or a default if InfluxDB is unreachable."""
    token = os.environ.get("INFLUXDB_TOKEN")
    if not token:
        print("INFLUXDB_TOKEN unset: using default detector temperature")
        return DEFAULT_TEMPERATURE_K
    try:
        # Imported here so the script runs without influxdb-client installed
        from influxdb_client import InfluxDBClient  # pylint: disable=C0415

        client = InfluxDBClient(url=INFLUX_URL, token=token, org=INFLUX_ORG)
        result = client.query_api().query(org=INFLUX_ORG, query=DETTEMP_QUERY)
        return result.to_values()[0].mapping["_value"]
    except Exception as exc:  # pylint: disable=W0718
        print(f"WARNING: unable to read InfluxDB ({exc}): using default")
        return DEFAULT_TEMPERATURE_K


def write_headers(camera, args):
    """Write this sequence's FITS keywords to the camera."""
    acquired = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"
    keywords = {
        "OBSERVER": (args.observer, "who took this"),
        "LOCATION": ("On FEI", "where is the ATC"),
        "IMTYPE": (args.imtype, "image type"),
        "ACQTIME": (acquired, "UTC time of acquisition"),
        "DETTEMP": (f"{detector_temperature()}", "detector temperature in K"),
    }
    for name, (value, comment) in keywords.items():
        camera.set_fits_key(name, value, comment)


def configure(camera, args):
    """Apply the camera mode, readout mode and geometry.

    No h2rg_init: it enables Pad B output, after which the configured taps
    read nothing and every frame comes back zero.
    """
    camera.open()
    camera.load()
    camera.power(True)
    camera.datacube(args.exposure in ("utr_rr", "utr_gr"))

    # The camera mode reloads its parameters from the ACF, so it goes first
    camera.set_camera_mode(args.mode)
    camera.set_readmode(ReadMode(args.exposure))

    # The window state is deliberately left as the ACF mode sets it, matching
    # the counted script; touching it changes TAPLINES and so the frame width
    if args.mode == "guiding":
        low = DETECTOR_PIXELS // 2 - args.roi // 2
        camera.set_guiding_roi(low, low + args.roi - 1, low, low + args.roi - 1)
    elif args.mode == "roi":
        camera.set_centred_roi(args.roi, args.roi)
    camera.exptime(args.exptime)


def written(camera):
    """Return frames written per output."""
    return {o.name: o.frames_written for o in camera.output_status()}


def buffer_frames(camera):
    """Return the controller's per-buffer frame counters."""
    return dict(re.findall(r"(BUF\dFRAME)=(\d+)", camera.native("FRAME")))


def stop_freerun(camera):
    """Abort, disarm freerun, and report whether the detector actually stopped.

    Ignores further interrupts: a second Ctrl-C here would leave the detector
    streaming, which is the one outcome worth preventing.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    print("stopping (interrupts ignored until the detector is idle)")
    # Only abort: AbortSeq clears freerun itself, and every extra command here
    # goes to the socket the detector is streaming on
    try:
        camera.abort()
    except RuntimeError as exc:
        print(f"WARNING: abort failed ({exc})")

    before = written(camera)
    time.sleep(STOP_CHECK_S)
    if written(camera) == before:
        print(f"stopped: no new frames over {STOP_CHECK_S:.0f}s")
    else:
        print("WARNING: STILL STREAMING, the detector did not stop")


def run_freerun(camera, args):
    """Stream continuously until the duration elapses or Ctrl-C."""
    write_headers(camera, args)
    camera.set_freerun(True)
    camera.expose(1)
    print("freerun running; Ctrl-C to stop")
    start = time.monotonic()
    try:
        while args.seconds <= 0 or time.monotonic() - start < args.seconds:
            time.sleep(1.0)
            print(f"  t={time.monotonic() - start:5.1f}s {written(camera)}")
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        stop_freerun(camera)


def run_counted(camera, args):
    """Take the requested frames, repeated as asked."""
    for sequence in range(args.repeat):
        write_headers(camera, args)
        camera.expose(args.frames)
        print(f"sequence {sequence + 1} of {args.repeat} complete")
        if args.pause:
            time.sleep(args.pause)


# The Archon allocates a 16k network write buffer per connection and will not
# transmit a frame that does not fit
MAX_AUTOFETCH_BYTES = 16384
AUTOFETCH_HEADER_LEN = 36
BYTES_PER_PIXEL = 2
# Every frame carries the exposure and its reset image side by side, so an
# N column window comes back 2N wide
FRAME_WIDTH_FACTOR = 2


# Short enough that Ctrl-C feels immediate
JOIN_POLL_S = 0.2
# The producer ends when its read fails after autofetch is disarmed
STOP_JOIN_S = 15.0


def stop_autofetch(camera):
    """Disarm autofetch, ignoring further interrupts until it is off.

    Not camera.abort(): that writes the ACF abort parameter over the streaming
    socket, where the reply collides with frame data. Disarming goes through
    the controller's own control connection and clears Expose and freerun too.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    print("stopping (interrupts ignored until autofetch is disarmed)")
    try:
        camera.set_autofetch(False)
    except RuntimeError as exc:
        print(f"WARNING: could not disarm autofetch: {exc}")


def run_autofetch(camera, args):
    """Stream the requested frames with the Archon pushing them unsolicited."""
    frame_bytes = (AUTOFETCH_HEADER_LEN
                   + args.roi * FRAME_WIDTH_FACTOR * args.roi * BYTES_PER_PIXEL)
    if frame_bytes >= MAX_AUTOFETCH_BYTES:
        raise SystemExit(f"roi {args.roi} gives {frame_bytes} byte frames; autofetch "
                         f"needs under {MAX_AUTOFETCH_BYTES}, so use a smaller roi")

    write_headers(camera, args)
    camera.set_autofetch(True)
    print(f"autofetch running, {args.frames} frames; Ctrl-C to stop")
    started = time.monotonic()
    interrupted = False

    # On a thread so the main thread stays able to take SIGINT: expose() blocks
    # in C++ with the GIL released, so a handler cannot run until it returns
    worker = threading.Thread(target=camera.expose, args=(args.frames,),
                              name="autofetch", daemon=True)
    worker.start()
    try:
        while worker.is_alive():
            worker.join(JOIN_POLL_S)
    except KeyboardInterrupt:
        interrupted = True
    finally:
        stop_autofetch(camera)
        worker.join(STOP_JOIN_S)
    elapsed = time.monotonic() - started

    # Per output, not summed: every output writes the same frames, so adding
    # them reports a multiple of the real count
    frames = max((o.frames_written for o in camera.output_status()), default=0)
    if interrupted:
        print(f"interrupted after {frames} frames")
    if elapsed > 0:
        print(f"{frames} frames in {elapsed:.2f}s = {frames / elapsed:.1f} fps")


def main():
    """Configure the camera, then acquire."""
    args = parse_args()
    if args.freerun and args.autofetch:
        raise SystemExit("--freerun and --autofetch cannot be combined")
    if (not args.autofetch and args.mode in ("guiding", "roi")
            and args.roi < MIN_NON_AUTOFETCH_ROI):
        raise SystemExit(
            f"roi {args.roi} produces faster than a non-autofetch readout can "
            f"fetch, which leaves data unread and wedges the controller; use "
            f"--autofetch, raise --exptime, or use roi "
            f"{MIN_NON_AUTOFETCH_ROI} or more")
    if not os.path.exists(args.config):
        raise SystemExit(f"no such config: {args.config}")
    for name, value in sorted(vars(args).items()):
        print(f"{name}: {value}")

    camera = TrackingCamera.from_config(args.config)
    configure(camera, args)

    try:
        acquire(camera, args)
    finally:
        # Nothing else releases the primary and control sockets
        camera.close()

    for output in camera.output_status():
        print(f"{output.name}: wrote {output.frames_written}, "
              f"dropped {output.frames_dropped}, last {output.last_written}")


def acquire(camera, args):
    """Dispatch to the requested acquisition mode."""
    if args.freerun:
        run_freerun(camera, args)
    elif args.autofetch:
        run_autofetch(camera, args)
    else:
        run_counted(camera, args)


if __name__ == "__main__":
    main()
