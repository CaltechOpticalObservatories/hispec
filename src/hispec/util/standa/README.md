# Standa Controllers

Low-level Python or simplified wrapper modules to send commands to Standa controllers.

## Currently Supported Models
- 8SMC5 - smc8.py

## Features
- Connect to Standa Controllers
- Query state and parameters
- Move individual axes to absolute or relative positions

## Usage

### smc8.py Example
```python
    from util.smc8 import SMC

    # Open connection examples  
    dev = SMC(device_connection = "192.168.31.123/9219", connection_type = "xinet", log = False)
    dev = SMC(device_connection="/dev/ximc/00007DF6", connection_type = "serial",log = True)
    dev.open_connection()
    time.sleep(.25)
    #Populates dev with device info
    dev.get_info() 

    # checks status
    status = dev.status() 

    # Homes device
    dev.home() 
    time.sleep(5) #Give time for stage to move

    # Query Position
    pos = dev.get_position() # Query Position

    # Move Relative to its current position
    dev.move_rel(position = 5) #positive ot negative
    time.sleep(5)

    # Move to absolute position
    dev.move_abs(position = 10) 
    time.sleep(5)

    pos = dev.get_position()
    dev.home()
    time.sleep(5)
    #Close connection
    dev.close_connection()
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