# sunpower

A collection of Python interfaces for communicating with HISPEC FEI components.

## Features


- Query device status, error, and firmware version
- Get and set target temperature
- Get and set user commanded power
- Get reject and cold head temperatures
- Turn cooler on or off
- Async API for non-blocking operation

## Installation

```bash
pip install .
```

## Usage

```python
import asyncio
from hispec.util.sunpower.sunpower_controller import SunpowerCryocooler


async def main():
    controller = SunpowerCryocooler(port='/dev/ttyUSB0', baudrate=9600, quiet=True)
    await controller.get_status()
    await controller.set_target_temp(300.0)
    await controller.turn_on_cooler()
    await controller.get_commanded_power()
    await controller.set_commanded_power(10.0)
    await controller.get_reject_temp()
    await controller.get_cold_head_temp()


asyncio.run(main())
```

## 🧪 Testing
Unit tests are located in `tests/` directory and use `pytest` with `unittest.mock` to simulate hardware behavior — no physical sunpower controller is required.

To run all tests from the project root:

```bash
pytest
```