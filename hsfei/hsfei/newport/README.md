# newport_controller

Low-level Python library to control Newport SMC100PP motion controllers.

## Features
- Connect to Newport controllers over serial through a terminal server
- Query device ID and serial number
- Move individual axes to absolute or relative positions
- Query servo and motion status

## Usage
```python
    from hsfei import NewportController

    controller = NewportController(host='192.168.29.100', port=10006)

    # Print stage 1 parameters
    print(controller.get_params(1))

    # Move axis 1 to position 12.0
    controller.move_abs(1, 12.0)
    
    # Move axis 2 to +12 degrees relative to current position
    controller.move_rel(2, 12.0)

```

## 🧪 Testing
Unit tests are located in `tests/` directory and use `pytest` with `unittest.mock` to simulate hardware behavior — no physical PI controller is required.

To run all tests from the project root:

```bash
pytest
```