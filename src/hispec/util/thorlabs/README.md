# Thorlabs_controllers

Low-level Python modules to send commands to Thorlabs motion controllers.

## Currently Supported Models
- FW102C - fw102c.py
- PPC102 - ppc102.py

## Features
- Connect to Thorlabs controllers over serial through a terminal server
- Query state and parameters
- Move individual axes to absolute or relative positions

## Usage

### FW102C Example
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

### PPC102 Example
```python
    from hispec.util.thorlabs.ppc102 import PPC102_Coms

    # log = false will now print to command line
    dev =  PPC102_Coms(ip="",port="",log=False)

    #Open connection
    dev.open()

    # set voltage on channel 1 and get result (open loop control)
    dev.set_output_volts(channel=1,volts=100)
    res = dev.get_output_volts(channel=1)

    # switch channels to closed loop
    dev.set_loop(channel=1,loop=2)
    dev.set_loop(channel=2,loop=2)

    # set positions on channel 1 or 2 and get result
    dev.set_position(channel=1,pos=5.0)
    dev.set_position(channel=2,pos=-5.0)
    cur_pos1 = dev.get_position(channel=1)
    cur_pos2 = dev.get_position(channel=2)

    # switch channels to open loop
    dev.set_loop(channel=1,loop=1)
    dev.set_loop(channel=2,loop=1)

    #Set voltages to zero
    dev.set_output_volts(channel=1,volts=0)
    dev.set_output_volts(channel=2,volts=0)

    # close socket connection
    dev.close()
```

## 🧪 Testing
Unit tests are located in `tests/` directory.

TODO: Make "Mock test" for PPC102 get_position and get_status which threw errors and was removed. 
    Assumed to be due to the byte and int convertion

To run tests from the project root based on what you need:
Software check:
```bash
pytest -m unit
```
Connection Test:
```bash
pytest -m default
```
Functionality Test:
```bash
pytest -m functional
```