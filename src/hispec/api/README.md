# `hispec.api` — subsystem API layer

A layer above the daemons. Daemons own hardware and publish keywords; drivers
talk to devices. This package holds the operations that compose keywords and
devices into something worth a name — the code that otherwise lives in a
one-off script, gets copied, and carries its bugs along.

One subpackage per subsystem. Only the FEI exists so far.

```python
from hispec.api.fei import FEI

with FEI() as fei:                      # connects using ~/.libby/cli_config.yaml
    print(fei.status())                 # snapshot: connectivity, positions, ATC
    fei.stage("ms_h").move_named("slot_1")
    fei.move_adc(10.0, -10.0)           # both prisms together, then wait
    print(fei.temperatures())
```

## What belongs here

- Anything that touches more than one keyword or more than one device.
- Anything with a "wait until done, then check it actually got there" shape.
- Anything an engineer would otherwise paste between scripts.

What does not: hardware protocol details (that's `hispec.driver`) and keyword
definitions or hardware state (that's the daemon).

## Layout

| File | Holds |
| --- | --- |
| `base.py` | `SubsystemAPI`: the libby client, keyword addressing, tolerant bulk reads |
| `motion.py` | `Stage`: one motion axis — move, wait, home, halt |
| `errors.py` | `MoveTimeout`, `PositionError` |
| `fei/devices.py` | HSFEI peer ids, axes and sensor keywords, mirroring `config/hsfei/*.yaml` |
| `fei/fei.py` | `FEI`: the subsystem's procedures |

## Adding a procedure

Add a method to the subsystem class. Address keywords through `self.get`,
`self.set`, `self.trigger` and `self.wait_for` — they take the device
(a daemon's `peer_id`) and the bare keyword, so no code assembles
`"hsfei.adc.positionvalue1"` by hand. Reach for `Stage` for anything that
moves.

Two conventions worth keeping:

- **Wait, then verify.** A write returns as soon as the daemon accepts it. If
  an operation is not complete until hardware settles, wait for that and
  confirm it, as `Stage.move` does.
- **Raise on a single operation, tolerate on a sweep.** `move` raises;
  `status` and `home_all` collect failures so one dead controller does not
  cost the caller the whole read.

## Adding a subsystem

```python
# src/hispec/api/hscal/hscal.py
from ..base import SubsystemAPI

class HSCal(SubsystemAPI):
    group_id = "hscal"          # the group_id in config/hscal/*.yaml
```

Export it from the subpackage's `__init__.py`, and from `hispec/api/__init__.py`.

## Connecting

`FEI()` builds its own libby client from `~/.libby/cli_config.yaml`; pass
`config_path=` for a different one. To share one connection across subsystems,
or to test without a bus, pass a client in: `FEI(client)`. An API only closes
the client it created itself.

## Tests

`tests/api/` runs against a `FakeClient` (in `conftest.py`) rather than a live
bus, so procedures are testable without hardware:

```
pytest tests/api
```
