# pi_controller

Low-level Python library to control PI 863 and PI 663 motion controllers using the [pipython](https://pypi.org/project/pipython/) library.

## Features
- Connect to a single PI controller over TCP/IP
- Connect to a TCP/IP-based daisy chain via a terminal server
- Automatically detect and select connected devices in a daisy chain
- Switch between multiple controllers in the same daisy chain
- Log controller actions and errors (with optional quiet mode)
- Store and recall named positions per controller
- Query servo and motion status
- Emergency halt of motion
- Structured error handling via `pipython.GCSError`

## Example Usage
```python
    from hispec.util import PIControllerBase
    
    # Connect to a Single Controller
    controller = PIControllerBase()
    controller.connect_tcp('192.168.0.100')

    print(controller.get_idn())

    
    # Connect to a Daisy Chain
    controller = PIControllerBase()
    controller.connect_tcpip_daisy_chain("192.168.29.100", 10005)
    
    # List available devices
    devices = controller.list_devices_on_chain("192.168.29.100", 10005)
    for device_id, desc in devices:
        print(f"Device {device_id}: {desc}")
    
    # Switch to another device
    controller.select_device_on_chain("192.168.29.100", 10005, 2)
    print("Now on device 2:", controller.get_idn())
    
    
    # Move axis 1 to position 12.0
    controller.set_position('1', 12.0)

    # Save current position as "home"
    controller.set_named_position('1', 'home')

    # Later on, move back to "home" position
    controller.go_to_named_position('home')

    controller.disconnect()
```

## API Summary
| Method                                        | Description                                  |
| --------------------------------------------- | -------------------------------------------- |
| `connect_tcp(ip, port)`                       | Connect to a single PI controller            |
| `connect_tcpip_daisy_chain(ip, port)`         | Open a TCP-based daisy chain                 |
| `select_device_on_chain(ip, port, device_id)` | Select a device from an active chain         |
| `list_devices_on_chain(ip, port)`             | Return list of connected devices for a chain |
| `get_idn()`                                   | Get the controller identification string     |
| `get_serial_number()`                         | Get the serial number from the IDN           |
| `get_axes()`                                  | Return available axes                        |
| `get_position(axis_index)`                    | Get current position of axis by index        |
| `servo_status(axis)`                          | Check if the servo on an axis is enabled     |
| `get_error_code()`                            | Get the controller's last error code         |
| `halt_motion()`                               | Stop all motion on the controller            |
| `set_position(axis, position)`                | Move an axis to a position                   |
| `set_named_position(axis, name)`              | Save a position under a named label          |
| `go_to_named_position(name)`                  | Move to a previously saved named position    |


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