# smc100pp_controller

Low-level Python modules to send commands to Newport motion controllers.

## Currently Supported Models
- SMC100PP - smc100pp.py

## Features
- Connect to Newport controllers over serial through a terminal server
- Query stage state and parameters
- Move individual axes to absolute or relative positions

## Usage

```python
import smc100pp

controller = smc100pp.StageController()
controller.connect(host='192.168.29.100', port=10006)

# Print stage 1 parameters
print(controller.get_params(1))

# Print stage2 state
print(controller.get_state(2))

# Move axis 1 to position 12.0
controller.move_abs(12.0, 1)

# Move axis 2 to +12 degrees relative to current position
controller.move_rel(12.0, 2)

# For a comprehensive list of classes and methods, use the help function
help(smc100pp)

```

## 🧪 Testing
Unit tests are located in `tests/` directory.

To run all tests from the project root:

```bash
pytest
```