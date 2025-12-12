# Xeryon Motion Controller Library

This module provides a Python interface to communicate with and control Xeryon precision stages. It supports serial communication, axis movement, settings management, and safe handling of errors and edge cases.

## Features
- Serial or TCP/IP communication with Xeryon controllers
- Multi-axis system support
- Configurable stage settings from a file
- Blocking/non-blocking movement
- Real-time data logging and error monitoring
- Configurable output via logger

---

## Folder Structure
```
xeryon/
├── __init__.py
├── axis.py             # Axis class abstraction
├── communication.py    # Low-level serial communication logic
├── config.py           # Centralized constants and flags
├── controller.py       # XeryonController high-level interface
├── stage.py            # Stage definitions (e.g. XLS, XLA, XRTU)
├── units.py            # Unit definitions and conversion
├── utils.py            # Logging, time utilities, formatting helpers
├── settings_default.txt
└── tests/
    ├── test_axis.py
    ├── test_communication.py
    ├── test_controller.py
    └── test_utils.py
```

---

## Getting Started
### Prerequisites
- Python 3.7+
- Xeryon controller connected via serial
- `pyserial` library


### Example Usage
#### Serial Connection
```python
from xeryon.controller import XeryonController
from xeryon.stage import Stage

# Initialize controller
controller = XeryonController(COM_port="/dev/ttyUSB0")
controller.addAxis(Stage.XLS_312, "X")
controller.start()

# Move axis
x_axis = controller.getAxis("X")
x_axis.setDPOS(1000)  # Move to position 1000 in current units

controller.stop()
```
#### TCP/IP Connection
```python
from xeryon.controller import XeryonController
from xeryon.stage import Stage

# Initialize controller via TCP/IP (e.g., through a terminal server)
controller = XeryonController(
    connection_type="tcp",
    tcp_host="192.168.1.100",
    tcp_port=12345
)
controller.add_axis(Stage.XLS_312, "X")
controller.start()

# Move axis
x_axis = controller.get_axis("X")
x_axis.set_DPOS(1000)

controller.stop()
```

---

## Settings File
Place a `settings_default.txt` file in the config directory. Format:
```txt
X:LLIM=0
X:HLIM=100000
X:SSPD=2000
POLI=5
```
Each line sets a controller or axis setting.

---

## Logging
The `utils.py` module provides a `output_console` function with logger integration. Messages can be printed to stdout or stderr depending on severity.

---

## 🧪 Testing
Tests are written using `pytest`. Run with:
```bash
pytest
```


