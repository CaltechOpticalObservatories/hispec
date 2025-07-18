# PTC10 Python Interface

A low level library for communicating with the **Stanford Research Systems PTC10 Programmable Temperature Controller** via RS-232, USB, or Ethernet.

## Features

- Query identification string
- Read the current value of a specific sensor or output channel
- Read all channel values in a single query
- Retrieve names of all active channels
- Return values as a dictionary mapping channel name to current value
- Compatible with both serial and Ethernet connections

## Requirements

- Python 3.8+
- `pyserial` (only required for serial communication)

## Getting Started

### Project Structure

```
ptc10/
├── __init__.py
├── ptc10_connection.py
├── ptc10.py
└── README.md
```

### Basic Usage

```python
from hispec.util PTC10, PTC10Connection

# Ethernet example
conn = PTC10Connection(method='ethernet', host='192.168.29.150', tcp_port=23)
ptc = PTC10(conn)

# Identify controller
print("Device ID:", ptc.identify())

# Read a specific channel
print("Temp at 3A:", ptc.get_channel_value("3A"))

# Read all values
print("All values:", ptc.get_all_values())

# Channel name to value map
print("Named outputs:", ptc.get_named_output_dict())

conn.close()
```

## API Reference

### `PTC10Connection`

```python
PTC10Connection(
    method='serial' or 'ethernet',
    port='/dev/ttyUSB0',       # for serial
    host='192.168.29.150',     # for ethernet
    tcp_port=23                # optional, default depends on method
)
```

Handles low-level I/O with the controller. Use `'serial'` for RS-232 and `'ethernet'` for TCP/IP.

---

### `PTC10`

#### `identify() -> str`
Returns the device identification string.

#### `get_channel_value(channel: str) -> float`
Queries the most recent value of a single channel. Example: `"3A"`, `"Out1"`.

#### `get_all_values() -> List[float]`
Returns a list of values for all available channels. Sensors out of range return `float('nan')`.

#### `get_channel_names() -> List[str]`
Returns the channel names in the same order as `get_all_values()`.

#### `get_named_output_dict() -> Dict[str, float]`
Returns a dictionary mapping each channel name to its latest value.

---

## Notes

- All messages must end in `\n` (linefeed). This is handled automatically by the connection class.
- Commands like `3A?`, `Out1?`, `getOutput?`, and `getOutputNames?` follow the PTC10 manual.
- Invalid channels or disconnected sensors will return `NaN`.
