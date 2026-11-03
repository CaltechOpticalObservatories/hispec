# fib

Drivers for the HISPEC FIB PCBs. Every board runs the
[hispec-tib](https://github.com/COO-Utilities/hispec-tib) firmware and is reached through the
MQTT 5 broker by its device name; the board strap selects the profile (`hsfib-tib` for the
trunk interface box).

## Read only

The driver can only send queries. `FibPcbClient` publishes an allowlisted key with no payload,
or `status` with its `ip`, `lasers` and `attens` flags, and raises `FibRefusedError` for anything
else before it reaches the broker. Nothing under `laser`, `atten`, `measure_throughput` or `reboot`
can be sent, and under `pd` only `pd/settings/yj|hk`, so the driver cannot turn on a laser, power
the laser bank or a photodiode, or move a switch.

## Usage

```python
from hispec.driver.fib import TrunkInterfaceBox

tib = TrunkInterfaceBox()
tib.connect("hsfib-tib", "hispec.caltech.edu")
tib.board_status()     # firmware, boots, ambient temperature, last command
tib.mems()             # MEMS switch states by name
tib.active_routes()    # inputs routed to each output
tib.temps()            # ambient, laser bank and per-laser TEC temperatures
tib.lasers()           # compact per-laser state
tib.attenuations_db()  # applied attenuation per laser
tib.photodiode_settings("yj")  # photodiode relay intent and auto-off
tib.disconnect()
```

`connect` fails if the board at that device name reports another profile. Each query blocks
until its reply arrives, matched by MQTT 5 correlation data, and raises `FibTimeoutError` after
`timeout_s` (5 s by default) or `FibCommandError` when the board replies with an error. Board
warnings and watchdog reboots are logged and passed to `on_warning` and `on_boot` when set.

## Tests

`tests/util/fib/` runs against a fake MQTT client, so no broker or board is needed:

```bash
python -m pytest tests/util/fib
```
