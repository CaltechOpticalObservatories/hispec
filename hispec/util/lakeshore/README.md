# lakeshore_controller

Low-level Python modules to send commands to Lakeshore 224 or 336 controllers.

## Currently Supported Models
- 224 & 336 - lakeshore.py

## Features
- Connect to Lakeshore controllers over ethernet
- Query sensor values
- For model 336, query status and parameters of heaters

## Usage

```python
from hispec.util import lakeshore

controller = lakeshore.LakeshoreController()    # defaults to 336
controller.set_connection(ip='192.168.29.104', port=7777)
controller.connect()

# Initialize controller
controller.initialize(celsius=False)    # print temperatures in Kelvin

# Print heater 1 status
print(controller.get_heater_status('1'))

# Print sensor A temperature
print(controller.get_temperature('a'))

# Print heater 2 output
print(controller.get_heater_output('2'), controller.outputs['2']['htr_display'])

# For a comprehensive list of classes and methods, use the help function
help(lakeshore)

```

## 🧪 Testing
Unit tests are located in `tests/` directory.

To run all tests from the project root:

```bash
pytest
```