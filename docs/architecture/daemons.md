# Daemon, Driver and Config Inventory

This page is the concrete inventory the COO specification asks each instrument
to provide: what daemons exist, what hardware each owns, which driver it uses,
and what it exposes. It describes the current `main` branch and needs updating
whenever a daemon is added.

## Daemon inventory

Daemons are split by reusability, not by subsystem. `daemons/generic/` holds
daemons whose behaviour is fully determined by config and which are therefore
shared across subsystems; `daemons/<subsystem>/` holds daemons tied to one
subsystem's hardware or to mechanism-specific logic.

| Daemon | Driver | Hardware | Deployed instances |
|---|---|---|---|
| `generic/filterwheel` | `thorlabs.fw102c` | Thorlabs FW102C filter wheel | `hsfei_atcfw`, `hscal_hkcalfwheel1/2`, `hscal_hkgcellfwheel`, `hscal_yjcalfwheel1/2` |
| `generic/lakeshore` | `lakeshore.lakeshore` | Lakeshore 336/224 temperature controller | `hsfei_atctherm`, `hscal_gcellheater1/2` |
| `generic/srsthermal` | `srs.ptc10` | SRS PTC10 thermal controller | `hscal_hkettherm`, `hscal_yjettherm` |
| `generic/inficon` | `inficon.inficonvgc502` | Inficon VGC502 vacuum gauge controller | `hsfei_atcpress` |
| `generic/pdu` | `pdu.src.emat08_10` | Eaton EMAT08-10 networked PDU | none yet (example config only) |
| `hsfei/pi-daemon` | `pi.PIControllerBase` | PI C-663 / C-863 / E-754 motion controllers | `hsfei_atcl`, `hsfei_atcp`, `hsfei_feipo`, `hsfei_lsm`, `hsfei_ms` |
| `hsfei/adc` | `newport.smc100pp` | Newport SMC100PP ADC prism rotators | `hsfei_adc` |
| `hsfei/atccryo` | `sunpower.sunpower_cryocooler` | Sunpower cryocooler | `hsfei_atccryo` |
| `hsfei/piaa-gimbalmount` | `thorlabs.ppc102` | Thorlabs PPC102 piezo gimbal mount | `hsfei_piaagimb`, `hsfei_piaagimr` |
| `hscal/smc8_attenuator` | `standa.smc8` | Standa SMC8 (libximc) attenuator | `hscal_hketatten` |

Twenty-two instances are currently defined under `systemd/instances/`, running
ten distinct daemon scripts — the config-driven design paying off directly.

## Subsystem view

### `hsfei` — Front End Instrument

The FEI is the most complete subsystem, covering the pickoff and acquisition
path, the ADC, the PIAA gimbal mounts, and the ATC (acquisition and tracking
camera) environment.

| Instance | Mechanism |
|---|---|
| `hsfei_feipo` | FEI pickoff |
| `hsfei_ms` | mask selector (two daisy-chained PI stages, H and V) |
| `hsfei_lsm` | lens selector mechanism |
| `hsfei_atcl` | ATC lens stage |
| `hsfei_atcp` | ATC pickoff stage |
| `hsfei_adc` | atmospheric dispersion corrector, two prism rotators |
| `hsfei_piaagimb` / `hsfei_piaagimr` | PIAA gimbal mounts, blue and red |
| `hsfei_atcfw` | ATC filter wheel |
| `hsfei_atctherm` | ATC temperature control |
| `hsfei_atcpress` | ATC vacuum pressure |
| `hsfei_atccryo` | ATC cryocooler |

### `hscal` — Calibration

The calibration unit covers the HK (red) and YJ (blue) calibration paths and
the gas cell.

| Instance | Mechanism |
|---|---|
| `hscal_hkcalfwheel1` / `2` | HK calibration filter wheels |
| `hscal_yjcalfwheel1` / `2` | YJ calibration filter wheels |
| `hscal_hkgcellfwheel` | gas cell filter wheel |
| `hscal_gcellheater1` / `2` | gas cell heaters |
| `hscal_hkettherm` / `hscal_yjettherm` | etalon thermal control |
| `hscal_hketatten` | HK etalon attenuator |

### Placeholder subsystems

`daemons/hscryo`, `daemons/hstt` and `daemons/hscam` exist as empty
placeholders for the cryostat, tip-tilt and detector subsystems. The
spectrograph itself has no daemon directory yet.

## Keyword inventory

### Keywords every daemon has

Inherited from `LibbyDaemon` and registered without the daemon asking:

| Keyword | Type | Access | Meaning |
|---|---|---|---|
| `uptime` | int | read | Whole seconds since the daemon started serving. |
| `lasterror` | string | read / clear | The most recent message passed to `logger.error()`. Write `null` to clear. Makes a locally-logged failure remotely visible. |
| `keys.list` | service | read | Registered keyword names, `%` wildcard supported. |
| `keys.describe` | service | read | Full metadata for one keyword: type, access, units, description, timeout. |

Registered by HISPEC daemons themselves, by near-universal convention:

| Keyword | Type | Access | Meaning |
|---|---|---|---|
| `isconnected` | bool | read / write | Whether the daemon holds a live connection to its controller. Writing `true`/`false` connects or disconnects. |
| `error` | string | read | Last error string recorded by the daemon's own error state. |
| `shutdown` | trigger | write | Stop this daemon gracefully. |

### Per-daemon keywords

**Motion daemons** (`pi-daemon`, `adc`, `filterwheel`, `smc8_attenuator`)
share a vocabulary:

| Keyword | Meaning |
|---|---|
| `positionvalue` | Current position in the mechanism's configured units. Writable to move. |
| `positionnamed` | Current position as a configured name; writable to move to a named position. |
| `ismoving` | Motion in progress. |
| `isreferenced` | Stage has been homed. Writable to home. |
| `isloopclosed` | Servo loop closed. Writable. |
| `softmin` / `softmax` | Daemon-enforced limits, writable at runtime. |
| `hardmin` / `hardmax` | Controller limits, read-only. |
| `halt` | Trigger — stop motion on all axes. |

**Multi-axis daemons suffix the per-axis keywords and add an aggregate.** A
mechanism with more than one stage registers `positionvalue<suffix>`,
`ismoving<suffix>` and so on — the PI daemon uses the stage name from config
(`positionvalueh`, `positionvaluev` for the mask selector), the ADC uses the
stage number (`positionvalue1`, `positionvalue2`). Alongside those, the daemon
registers unsuffixed consolidated keywords covering the whole mechanism:
`isreferenced` is true when *all* stages are referenced and writing it homes
every stage, `ismoving` is true when *any* stage is moving, `isloopclosed`
aggregates likewise and one write closes every loop. A single-stage config
registers the bare names directly, so a client that only cares about the
mechanism as a whole uses the same keyword either way.

**Thermal daemons** (`lakeshore`, `srsthermal`) generate their keywords from
config. Each entry in `sensors:` produces one read-only temperature keyword
under the name the config chose; each entry in `heaters:` produces a writable
setpoint plus, for the Lakeshore, `<name>_output`, `<name>_status` and one
keyword per PID term.

**`atccryo`** exposes cryocooler state — `cold_head_temp`, `reject_temp`,
`target_temp`, `measured_power`, `commanded_power`, `control_mode`,
`cooler_error` — plus `pid_<term>` keywords for the control loop.

**`inficon`** exposes `pressure1`, `pressure2`, `temperature`, `units` and
`units_code`.

**`piaa-gimbalmount`** carries the largest keyword set: X/Y positions in both
position and voltage units, per-axis and combined loop-closed state, and a full
soft/hard limit matrix in both units — `softmaxx`, `softminvolty`, `hardmaxx`
and so on.

**`pdu`** registers device-level keywords (`model`, `manufacturer`, `firmware`,
`serial`, `outletcount`, `status`) plus a per-outlet block —
`outletstate<n>`, `outletname<n>`, `outletcurrent<n>`, `outletpower<n>`,
`outletenergy<n>`, `outletautorestart<n>`, `outletswitchable<n>`,
`resetstatistics<n>` — with the set of outlets and their capabilities read from
`pdu_models/*.yaml`.

## Config inventory

`config/<subsystem>/<instance>.yaml`, one file per instance, twenty-two files
at present — one for each deployed systemd instance. `config/example/` holds
templates for daemons not yet deployed.

Config is the source of truth for:

| Parameter group | Owner | Runtime mutability |
|---|---|---|
| `peer_id`, `group_id` | config only | fixed at startup |
| `hardware.*` (address, port, units, step size) | config only | fixed at startup |
| `limits.soft_*` | config, overridable | writable via `softmin`/`softmax` keywords; **not persisted** |
| `limits.hard_*` | controller, or config where the controller cannot report them | read-only |
| `named_positions` | config only | fixed at startup |
| `sensors` / `heaters` / `stages` | config only | fixed at startup; determines which keywords exist |
| `logging.level`, `logging.file` | config only | fixed at startup |

The one writable-at-runtime group is soft limits. A runtime change to
`softmin`/`softmax` lives only in the daemon process and is lost on restart,
which is worth knowing before relying on one during AIT.

## Adding a daemon

The mechanics, in the order they are done:

1. Add the vendor driver as a submodule under `src/hispec/driver/` if it is not
   already vendored.
2. If an existing daemon covers the hardware, skip to step 4 — most new
   mechanisms need no new Python.
3. Otherwise write `daemons/<subsystem>/<name>`: subclass `HispecDaemon`,
   register keywords in `on_start`, disconnect in `on_stop`, and give it an
   `argparse` `-c/--config` entry point that calls `from_config_file(...)` then
   `serve()`.
4. Add `config/<subsystem>/<instance>.yaml`.
5. Add `systemd/instances/<instance>.env` naming the script and the deployed
   config path.
6. Add the row to the instance table in `systemd/README.md` and to the daemon
   inventory above.
