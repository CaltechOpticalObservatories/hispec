# pi_controller

Low-level Python library to control PI 863 and PI 663 motion controllers using the [pipython](https://pypi.org/project/pipython/) library.

## Features
- Connect to a single PI controller over TCP/IP, including through terminal server
- Connect to a TCP/IP-based daisy chain via a terminal server
- Automatically detect and select connected devices in a daisy chain
- Manage multiple controllers in the same daisy chain
- Log controller actions and errors (with optional quiet mode)
- Check the reference (home) state and execute reference moves (homing)
- Store and recall named positions per controller
- Query and set servo status (open/close firmware loops)
- Query motion status
- Emergency halt of motion
- Structured error handling via `pipython.GCSError`

## Example Usage
```python
from pi import PIControllerBase

# Connect to a Single Controller
controller = PIControllerBase()
controller.connect_tcp('192.168.0.100')
device_key = ('192.168.0.100', 50000, 1)

print(controller.get_idn(device_key))

# Connect to a Daisy Chain
controller = PIControllerBase()
controller.connect_tcpip_daisy_chain("192.168.29.100", 10005)

# List available devices
devices = controller.list_devices_on_chain("192.168.29.100", 10005)
for device_id, desc in devices:
    print(f"Device {device_id}: {desc}")

# Use a device_key for further operations
device_key = ("192.168.29.100", 10005, 2)
print("Now on device 2:", controller.get_idn(device_key))

# Check if axis '1' is referenced
is_referenced = controller.is_controller_referenced(device_key, '1')
print("Axis 1 referenced:", is_referenced)

# Perform a reference move (home) on axis '1'
success = controller.reference_move(device_key, '1', method="FRF", blocking=True, timeout=30)
if success:
    print("Reference move completed successfully.")
else:
    print("Reference move failed or timed out.")

# Move axis 1 to position 12.0
controller.set_position(device_key, '1', 12.0)

# Save current position as "home"
controller.set_named_position(device_key, '1', 'home')

# Later on, move back to "home" position
controller.go_to_named_position(device_key, 'home')

controller.disconnect_device(device_key)
controller.disconnect_all()
```

## API Summary
| Method                                       | Description                                  |
|----------------------------------------------|----------------------------------------------|
| `connect_tcp(ip, port=50000)`                | Connect to a single PI controller            |
| `connect_tcpip_daisy_chain(ip, port)`        | Open a TCP-based daisy chain                 |
| `list_devices_on_chain(ip, port)`            | Return list of connected devices for a chain |
| `get_idn(device_key)`                        | Get the controller identification string     |
| `get_serial_number(device_key)`              | Get the serial number from the IDN           |
| `get_axes(device_key)`                       | Return available axes                        |
| `get_position(device_key, axis_index)`       | Get current position of axis by index        |
| `servo_status(device_key, axis)`             | Check if the servo on an axis is enabled     |
| `get_error_code(device_key)`                 | Get the controller's last error code         |
| `halt_motion(device_key)`                    | Stop all motion on the controller            |
| `set_position(device_key, axis, position)`   | Move an axis to a position                   |
| `set_named_position(device_key, axis, name)` | Save a position under a named label          |
| `go_to_named_position(name)`                 | Move to a previously saved named position    |
| `disconnect_device(device_key)`              | Disconnect a single device                   |
| `disconnect_all()`                           | Disconnect all devices                       |


## Logging
By default, the controller logs info and error messages to the console. You can suppress logs (except warnings/errors) by passing quiet=True:
```python
controller = PIControllerBase(quiet=True)
```

## 🧪 Testing
Unit tests are located in `tests/` directory and use `pytest` with `unittest.mock` to simulate hardware behavior — no physical PI controller is required.

To run all tests from the project root:

```bash
pytest tests/
```