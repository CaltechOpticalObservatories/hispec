# ozoptics_software

Low-level python modules for operating OZ Optics attenuators

## Currently Supported Models
- DD-100-MC (RS232)
- DD-600-MC (RS232)

## Features
- Connect to OZ Optics attenuators over serial through a terminal server
- Query attenuator state and parameters
- Command full range of attenuation values

## Requirements

- Install base class from https://github.com/COO-Utilities/hardware_device_base

## Installation

```bash
pip install .
```

## Usage

```python
import dd100mc

controller = dd100mc.OZController()
controller.connect('192.168.29.153', 10001)

controller.set_attenuation(36.5)
print(controller.get_attenuation())
controller.set_position(5750)
print(controller.get_position())

# For a comprehensive list of classes and methods, use the help function
help(dd100mc)
```

## 🧪 Testing
Unit tests are located in `tests/` directory.

To run all tests from the project root:

```bash
python -m pytest
```