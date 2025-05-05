# Sunpower Controller

A Python interface for communicating with Sunpower cryocoolers over a serial port.

## Installation

```bash
pip install .
```

## Usage

```python
from sunpower_controller import SunpowerController

controller = SunpowerController()
await controller.get_status()
```