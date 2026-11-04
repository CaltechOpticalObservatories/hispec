# tracking_camera

The HISPEC tracking camera's own commands, on top of
[pycamerad](https://github.com/COO-Utilities/pycamerad), which provides
everything common to any camerad camera.

## Prerequisite

pycamerad wraps `camera_interface_tracking`, a pybind11 module built from
[hispec-tracking-camera-instrument](https://github.com/CaltechOpticalObservatories/hispec-tracking-camera-instrument)
against [camera-interface](https://github.com/CaltechOpticalObservatories/camera-interface).
It is compiled per instrument, so it comes with the `atcam` extra, which
`systemd/install.sh` installs on `feiserver` only. To change its code on that
host, see "Changing an extra's code on a host" in `docs/install.md`.

Anywhere else, install it into whichever environment runs hispec. The
instrument repository is private:

```bash
pip install "camera-interface-tracking @ git+ssh://git@github.com/CaltechOpticalObservatories/hispec-tracking-camera-instrument.git"
```

The module is named `camera_interface_tracking`, which is what
`TrackingCamera.MODULE_NAME` loads, so it can share an environment with other
instruments' builds. The shared-memory output is on in that package and needs
ImageStreamIO, found under `/usr/local` with no flags; for another prefix add
`--config-settings=cmake.define.ImageStreamIO_DIR=<prefix>/lib/cmake`.

### Build dependencies

Ubuntu 24.04 and 26.04:

```bash
sudo apt-get install -y build-essential cmake ninja-build \
  libccfits-dev libcfitsio-dev libcurl4-openssl-dev nlohmann-json3-dev \
  libzmq3-dev libopencv-dev libboost-thread-dev libboost-chrono-dev
```

zmqpp is not packaged for Ubuntu, so build it from source as CI does:

```bash
git clone --depth 1 https://github.com/zeromq/zmqpp.git
cmake -S zmqpp -B zmqpp/build && cmake --build zmqpp/build -j"$(nproc)"
sudo cmake --install zmqpp/build && sudo ldconfig
```

macOS, where zmqpp is packaged:

```bash
brew install cmake cfitsio ccfits nlohmann-json zeromq zmqpp opencv boost
```

`ENABLE_SHM_OUTPUT=ON` additionally needs
[ImageStreamIO](https://github.com/milk-org/ImageStreamIO) built from source.
It does not compile on macOS, so the shared-memory output is Linux-only.

## Usage

```python
from hispec.driver.tracking_camera import TrackingCamera, ReadMode

camera = TrackingCamera.from_config("hispecatc.cfg")
camera.initialize()                       # open, load, power on

camera.set_camera_mode("GUIDING")
camera.set_readmode(ReadMode.RX)
camera.set_guiding_roi(51, 60, 51, 60)
print(camera.geometry())                  # Geometry(y0=51, y1=60, x0=51, x1=60)

camera.exptime(0.0)                       # from pycamerad, typed
camera.expose(1)
print(camera.output_status())             # -> [OutputStatus(...)]
```

This class holds only commands the HISPEC instrument provides, giving them real
signatures so callers do not build argument strings by hand. Everything common
to any camerad camera, including `exptime`, `expose`, `power` and
`output_status`, comes from `pycamerad.Camerad`.

A failed command raises `RuntimeError`. An invalid `ReadMode` raises
`ValueError` before anything is sent.

## Tests

`tests/util/tracking_camera/` runs against a fake camera, so neither the extension nor
hardware is needed:

```bash
python -m unittest discover -s tests/util/tracking_camera
```
