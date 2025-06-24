# sunpower

A collection of Python interfaces for communicating with HISPEC FEI components.

## Features

- Query device status, error, and firmware version
- Get and set target temperature
- Get and set user commanded power
- Get reject and cold head temperatures
- Turn cooler on or off
- Supports both serial and TCP (socket) connections with error handling

## Installation

```bash
pip install .
```

## Usage
### Serial Connection
```python
from hispec.util.sunpower.sunpower_controller import SunpowerCryocooler

controller = SunpowerCryocooler(port='/dev/ttyUSB0', baudrate=9600, quiet=True)

print("\n".join(controller.get_status()))
controller.set_target_temp(300.0)
controller.turn_on_cooler()
print("\n".join(controller.get_commanded_power()))
controller.set_commanded_power(10.0)
print("\n".join(controller.get_reject_temp()))
print("\n".join(controller.get_cold_head_temp()))
```

### TCP Connection
```python
from hispec.util.sunpower.sunpower_controller import SunpowerCryocooler

controller = SunpowerCryocooler(
    connection_type='tcp',
    tcp_host='192.168.29.100',
    tcp_port=10016,
    quiet=True
)

print("\n".join(controller.get_status()))
controller.set_target_temp(300.0)
controller.turn_on_cooler()
print("\n".join(controller.get_commanded_power()))
controller.set_commanded_power(10.0)
print("\n".join(controller.get_reject_temp()))
print("\n".join(controller.get_cold_head_temp()))
```

## 🧪 Testing
Unit tests are located in `tests/` directory and use `pytest` with `unittest.mock` to simulate hardware behavior — no physical sunpower controller is required.

To run all tests from the project root:

```bash
pytest
```
