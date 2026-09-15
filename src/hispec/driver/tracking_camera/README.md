# tracking_camera

The HISPEC tracking camera's own commands, on top of
[pycamerad](https://github.com/COO-Utilities/pycamerad), which provides
everything common to any camerad camera.

## Prerequisite

pycamerad wraps `camera_interface`, a pybind11 module built from
[camera-interface](https://github.com/CaltechOpticalObservatories/camera-interface).
It is a compiled extension built per instrument rather than a package on an
index, so it cannot be a dependency in `pyproject.toml` and has to be built
separately. pybind11 is needed only to compile it, not to import it, so it is
not a dependency of this project either:

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
from hispec.driver.tracking_camera import TrackingCamera, ReadMode

camera = TrackingCamera.from_config("hispecatc.cfg")
camera.initialize()                       # open, load, power on, h2rg_init

camera.set_camera_mode("GUIDING")
camera.set_readmode(ReadMode.RX)
camera.set_window(True)
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
