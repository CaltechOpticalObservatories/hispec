# Onewire Environmental Sensor

Low-level Python modules to communicate with Embedded Data Systems OW-SERVER device.
It supports reading temperature, humidity, dew point, humidex, heat index, pressure, and illuminance from OW-ENV sensor (pressure and illuminance are only available on supported sensors).
It uses `async with` interface

## Requirements

- Python 3.7+
- No third-party packages required (pure standard library)

### Running from a Python Terminal

```python
import asyncio
from hispec.util.inficon import ONEWIRE, ONEWIREDATA

async def test_read():
    async with ONEWIRE("127.0.0.1") as ow:
        await ow.get_data()

    return ow.ow_data

ow_data = asyncio.run(test_read())
print(ow_data.read_sensors())
```