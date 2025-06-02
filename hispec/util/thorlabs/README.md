# Thorlabs_controllers

Low-level Python modules to send commands to Thorlabs motion controllers.

## Currently Supported Models
- FW102C - fw102c.py

## Features
- Connect to Thorlabs controllers over serial through a terminal server
- Query state and parameters
- Move individual axes to absolute or relative positions

## Usage

```python
from hispec.util import fw102c

controller = fw102c.FilterWheelController()
controller.set_connection(ip='192.168.29.100', port=10010)
controller.connect()

# Print filter wheel current position
print(controller.get_position())

# Move filter wheel to filter 5
controller.move(5)

# For a comprehensive list of classes and methods, use the help function
help(fw102c)

```

## 🧪 Testing
Unit tests are located in `tests/` directory.

To run all tests from the project root:

```bash
pytest
```