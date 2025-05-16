# InficonVGC502 

A Python 3 module to communicate with an INFICONVGC502 controller over TCP. It supports reading pressure values from one or more gauges using an easy-to-use `async with` interface.

## 🛠️ Requirements

- Python 3.7+
- No third-party packages required (pure standard library)


### 🧪 Running from a Python Terminal

You can also use the `INFICON` module interactively from a Python terminal or script:

```python
import asyncio
from hispec.util.inficon import InficonVGC502

async def test_read():
    async with InficonVGC502("127.0.0.1", 8000) as inficon:
        pressure = await inficon.read_pressure(gauge=1)
        print(f"Pressure: {pressure} Torr")

asyncio.run(test_read())
```
