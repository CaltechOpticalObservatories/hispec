# pi_controller

Low-level Python library to control PI 863 and PI 663 motion controllers using the [pipython](https://pypi.org/project/pipython/) library.

## Features
- Connect and disconnect to PI controllers over TCP/IP
- Query device ID and serial number
- Move individual axes to absolute or named positions
- Save and recall named positions (per-controller, persisted to disk)
- Query servo and motion status
- Emergency halt of motion
- Structured error handling via `pipython.GCSError`

## Example Usage
```python
    from hsfei import PIControllerBase

    controller = PIControllerBase()
    controller.connect_tcp('192.168.0.100')

    # Print controller ID string
    print(controller.get_idn())

    # Move axis 1 to position 12.0
    controller.set_position('1', 12.0)

    # Save current position as "home"
    controller.set_named_position('1', 'home')

    # Later on, move back to "home" position
    controller.go_to_named_position('home')

    controller.disconnect()
```

## 🧪 Testing
Unit tests are located in `tests/` directory and use `pytest` with `unittest.mock` to simulate hardware behavior — no physical PI controller is required.

To run all tests from the project root:

```bash
pytest
```