# camerad

Typed access to the HISPEC tracking camera, in process, with no `camerad`
daemon and no text protocol in between.

## Prerequisite

This wraps `camera_interface`, a pybind11 module built from
[camera-interface](https://github.com/CaltechOpticalObservatories/camera-interface).
It is a compiled extension rather than a PyPI package, so it has to be built
and put on `PYTHONPATH`. pybind11 is needed only to compile it, not to import
it, so it does not belong in this project's dependencies:

```bash
cd camera-interface/build
pip install pybind11
cmake -DCONTROLLER=archon -DINSTRUMENT=hispec_tracking_camera \
      -DBUILD_PYTHON_MODULE=ON ..
make camera_interface
export PYTHONPATH=$PWD/../lib
```

## Usage

```python
from hispec.driver.camerad import TrackingCamera, ReadMode

camera = TrackingCamera.from_config("hispecatc.cfg")
camera.initialize()                       # open, load, power on, h2rg_init

camera.set_camera_mode("GUIDING")
camera.set_readmode(ReadMode.RX)
camera.set_window(True)
camera.set_guiding_roi(51, 60, 51, 60)
print(camera.geometry())                  # Geometry(y0=51, y1=60, x0=51, x1=60)

camera.exptime("0")                       # forwarded to camera_interface.Camera
camera.expose("1")
print(camera.output_status())
```

Instrument commands have real signatures here so callers do not build argument
strings by hand. Anything not defined on `TrackingCamera` is forwarded to the
underlying `camera_interface.Camera`, so base commands are reached directly.

A failed command raises `RuntimeError`. An invalid `ReadMode` raises
`ValueError` before anything is sent.

## Tests

`tests/util/camerad/` runs against a fake camera, so neither the extension nor
hardware is needed:

```bash
python -m unittest discover -s tests/util/camerad
```
