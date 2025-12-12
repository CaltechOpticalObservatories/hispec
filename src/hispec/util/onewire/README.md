# Onewire Environmental Sensor

Low-level Python modules to communicate with Embedded Data Systems OW-SERVER device.
It supports reading temperature, humidity, dew point, humidex, heat index,
pressure, and illuminance from OW-ENV sensor (pressure and illuminance are only
available on supported sensors).

## Requirements

- Python 3.7+
- Install base class from https://github.com/COO-Utilities/hardware_device_base

### Running from a Python Terminal

```python
from onewire import ONEWIRE

ow = ONEWIRE()
ow.connect("192.168.29.154", 80)

ow.get_data()
print(ow.ow_data.read_sensors())
ow.get_data()
print(ow.ow_data.read_sensors())
```
### NOTE
The OneWire disconnects after each call to get_data(), but the host and port
are stored after the first connection, so subsequent calls to get_data() will
reconnect.