# sunpower

A collection of Python interfaces for communicating with HISPEC FEI components.

## Features


- Query device status, error, and firmware version
- Get and set target temperature
- Turn cooler on or off
- Async API for non-blocking operation

## Installation

```bash
pip install .
```

## Usage

```python
import asyncio
from hispec.util.sunpower.controller import SunpowerController

async def main():
    controller = SunpowerController(port='/dev/ttyUSB0', baudrate=9600, quiet=True)
    await controller.get_status()
    await controller.set_target_temp(300.0)
    await controller.turn_on_cooler()

asyncio.run(main())
```

## 🧪 Testing
Unit tests are located in `tests/` directory and use `pytest` with `unittest.mock` to simulate hardware behavior — no physical sunpower controller is required.

To run all tests from the project root:

```bash
pytest
```