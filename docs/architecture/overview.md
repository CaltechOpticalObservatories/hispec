# Architecture Overview

## Scope

HISPEC is a high-resolution near-infrared spectrograph for the W. M. Keck
Observatory. This repository holds its Instrument Control System: the software
that owns instrument hardware, exposes it for command and monitoring, and runs
as a set of long-lived services on instrument hosts.

In scope:

- device drivers for every controller in the instrument
- device daemons that own that hardware at runtime
- per-instance configuration for those daemons
- deployment units that run them on instrument hosts

Planned for this repository, not yet built: the procedure and algorithm
library, an orchestration layer, operator GUIs, and published telemetry — see
[Where the architecture is heading](#where-the-architecture-is-heading).

Out of scope: science data reduction, archive interfaces, and the Keck facility
interfaces. Detector
readout is adjacent — it is present as the vendored
[`camera-interface`](https://github.com/CaltechOpticalObservatories/camera-interface)
submodule under `etc/`, but it is a separate C++ service with its own
architecture and is not part of the keyword daemon layer described here.

## Architectural principles

HISPEC follows the COO command-and-control model: **every piece of hardware is
owned by exactly one stateful daemon, and everything else talks to that daemon
through a uniform keyword interface.** No client — GUI, CLI, script or
engineer — touches a controller directly.

Four rules follow from that and are visible throughout the code:

**One daemon owns one controller.** A daemon holds the only connection to its
controller. If two things need the same hardware, they share the daemon, not
the serial port. Two physical units of the same model are two daemon
instances, not one daemon with two connections.

**Daemons are thin; drivers are dumb.** A daemon binds the transport, registers
keywords, validates writes, and delegates. A driver speaks the vendor protocol
and nothing else. Neither holds instrument-level workflow logic.

**Behaviour is configuration, not code.** The daemon that runs a filter wheel in
the FEI is the same file that runs one in the calibration unit. What differs —
address, limits, named positions, units, log destination — is a YAML file.
Adding a mechanism of an already-supported type requires no new Python.

**A daemon starts even when its hardware does not.** Keywords register before
the hardware connection is attempted, so an unreachable controller yields a
running, inspectable daemon reporting `isconnected = false` rather than a crash
loop. This is a deliberate AIT-driven choice, discussed under
[Degraded operation](#degraded-operation).

## The layers

```{mermaid}
flowchart TB
    subgraph clients["Clients"]
        CLI["libby CLI<br/>show / modify / waitfor"]
        SCRIPT["Python scripts<br/>libby Client"]
        GUI["engineering GUIs"]
    end

    subgraph transport["Transport"]
        RMQ["RabbitMQ broker<br/>topic routing on group.peer"]
    end

    subgraph daemonlayer["daemons/ — device daemons"]
        GEN["generic/<br/>filterwheel, lakeshore,<br/>inficon, srsthermal, pdu"]
        FEI["hsfei/<br/>pi-daemon, adc, atccryo,<br/>piaa-gimbalmount"]
        CAL["hscal/<br/>smc8_attenuator"]
    end

    subgraph pkg["src/hispec — installable package"]
        BASE["HispecDaemon<br/>transport + discovery policy"]
        DRV["driver/ — 14 vendor driver submodules"]
    end

    subgraph fw["libby — messaging framework"]
        LD["LibbyDaemon<br/>lifecycle, RPC, keywords"]
        KR["KeywordRegistry<br/>typed keywords, keys.list/describe"]
        BAM["bamboo<br/>envelope + protocol"]
    end

    CONF["config/ — per-instance YAML"]
    HW["instrument hardware<br/>PI, Thorlabs, Newport, Standa,<br/>Lakeshore, SRS, Inficon, Sunpower, Eaton"]

    CLI --> RMQ
    SCRIPT --> RMQ
    GUI --> RMQ
    RMQ --> GEN
    RMQ --> FEI
    RMQ --> CAL

    GEN --> BASE
    FEI --> BASE
    CAL --> BASE
    GEN --> DRV
    FEI --> DRV
    CAL --> DRV

    BASE --> LD
    LD --> KR
    LD --> BAM
    DRV --> HW

    CONF -.-> GEN
    CONF -.-> FEI
    CONF -.-> CAL
```

Reading the stack from the bottom:

**libby** ([repo](https://github.com/CaltechOpticalObservatories/libby)) is the
COO messaging framework, shared with other instruments. It provides
`LibbyDaemon` (process lifecycle, transport binding, RPC dispatch, pub/sub
hooks), the `KeywordRegistry` (typed keywords with getters, setters,
validators, units, descriptions and timeouts), a `Client` for scripts, and the
`libby` CLI. Underneath it, `bamboo` implements the wire envelope and protocol.

**`src/hispec`** is the installable Python package. It contributes two things:
`HispecDaemon`, a four-line subclass of `LibbyDaemon` that fixes the
instrument-wide transport policy, and `hispec.driver`, the namespace under
which every vendor driver is vendored as a git submodule.

```{literalinclude} ../../src/hispec/daemon.py
:language: python
:caption: src/hispec/daemon.py — the entire instrument-specific base class
```

Every HISPEC daemon inherits from this, so the transport decision is made once
for the instrument rather than per daemon.

**`daemons/`** holds the deployable services. Each is a single executable
Python file taking `-c <config.yaml>` and blocking in `daemon.serve()`. They
are grouped by ownership: `generic/` for daemons driven entirely by config and
reusable across subsystems, and `hsfei/` / `hscal/` for daemons tied to one
subsystem's hardware.

**`config/`** holds one YAML file per deployed instance, organised by
subsystem.

## Drivers

Every vendor driver is a git submodule from the
[COO-Utilities](https://github.com/COO-Utilities) organisation, mounted under
`src/hispec/driver/`. Fourteen are currently vendored:

| Submodule | Hardware |
|---|---|
| `pi` | Physik Instrumente motion controllers (C-663, C-863, E-754) |
| `thorlabs` | FW102C filter wheels, PPC102 piezo controllers |
| `newport` | SMC100PP stage controllers |
| `standa` | SMC8 / libximc motion controllers |
| `xeryon` | Xeryon piezo stages |
| `lakeshore` | Lakeshore 336 / 224 temperature controllers |
| `srs` | SRS PTC10 thermal controllers |
| `inficon` | VGC502 vacuum gauge controllers |
| `gammavac` | Gamma Vacuum ion pump controllers |
| `sunpower` | Sunpower cryocoolers |
| `onewire` | 1-Wire environmental sensors |
| `ozoptics` | OZ Optics fiber components |
| `pdu` | Eaton networked power distribution units |
| `hispec-fiber-switcher` | HISPEC fiber switcher |

Keeping drivers as separate repositories is deliberate: the same controller
models appear across COO instruments, and a driver fix benefits all of them
without a copy. The cost is submodule discipline — a checkout without
`--recursive` builds a package missing every `hispec.driver.*` module, which is
why both the build workflow and the nightly submodule-update workflow pin them
explicitly.

## Naming and addressing

Every daemon instance has two identifiers, both set in its config file:

- **`group_id`** — the subsystem: `hsfei`, `hscal`, and in future `hsspec`,
  `hstt`, `hscryo`, `hscam`.
- **`peer_id`** — the mechanism acronym: `atcfw`, `ms`, `piaagimb`,
  `hketatten`.

libby joins them into the wire identity `<group_id>.<peer_id>`, lowercased on
both sides so addressing is case-insensitive. A keyword is then addressed as:

```text
<group>.<peer>.<keyword>        e.g.  hsfei.atcfw.positionnamed
```

The short `peer_id` is only unique within its group; the joined form is what
routes. Peer IDs were renamed to lowercase module acronyms matching the Jira
mechanism names so that the software name, the drawing name and the ticket name
for a mechanism are the same string.

## Runtime and deployment view

```{mermaid}
flowchart LR
    subgraph host["instrument host"]
        direction TB
        UNIT["hispec-daemon@.service<br/>one systemd template unit"]
        I1["hispec-daemon@hsfei_atcfw"]
        I2["hispec-daemon@hsfei_ms"]
        I3["hispec-daemon@hscal_hketatten"]
        IN["..."]
        UNIT -.instantiates.-> I1
        UNIT -.instantiates.-> I2
        UNIT -.instantiates.-> I3
        UNIT -.instantiates.-> IN
    end

    subgraph etc["/etc/hispec"]
        ENV["instances/&lt;name&gt;.env<br/>HISPEC_DAEMON, HISPEC_CONFIG"]
        YML["&lt;name&gt;.yaml<br/>deployed config"]
    end

    ENV --> I1
    YML --> I1
    I1 --> BROKER["RabbitMQ broker"]
    I2 --> BROKER
    I3 --> BROKER
    I1 --> JOURNAL["journald / /var/log/hispec"]
```

One systemd template unit, `hispec-daemon@.service`, runs every daemon. An
instance `hispec-daemon@<name>` reads `/etc/hispec/instances/<name>.env`, which
names the daemon script (`HISPEC_DAEMON`, relative to `daemons/`) and its config
(`HISPEC_CONFIG`). Running a second unit of the same hardware model — two
Lakeshores, five filter wheels — is two env files pointing at the same script
with different configs.

The unit runs as an unprivileged `hispec` user with `NoNewPrivileges`,
`ProtectSystem=full`, `ProtectHome` and `PrivateTmp`, restarts on failure, and
logs to the journal unless a config sets `logging.file`. A polkit rule grants
the `hispec-ops` group start/stop/restart on `hispec-daemon@*` without sudo, so
day-to-day operation needs no root.

Full deployment instructions, including the instance table, are in
[`systemd/README.md`](https://github.com/CaltechOpticalObservatories/hispec/blob/main/systemd/README.md).

Host build procedures are documented separately under
{doc}`../build_notes/host_machine_build_notes` and
{doc}`../build_notes/fei_buildnote`; the FEI server runs a `PREEMPT_RT` kernel
with core shielding for the detector readout loop, which is why its build is
documented as its own recipe.

## Configuration model

A config file is the complete description of one deployed instance. The common
shape:

```yaml
peer_id: atcfw                 # mechanism acronym
group_id: hsfei                # subsystem

hardware:                      # how to reach the controller
  ip_address: 192.168.29.100
  tcp_port: 10010
  units: filter_pos
  timeout_s: 30.0

limits:                        # soft limits enforced by the daemon;
  soft_min: 1                  # hard limits reported from the controller
  soft_max: 6
  hard_min: 1
  hard_max: 6

named_positions:               # operator-facing names for positions
  empty: 1
  OD1: 2

logging:
  level: INFO
  file: /tmp/atcfw.log
```

Three config idioms recur and are worth naming:

**Named positions** turn a raw number into instrument vocabulary. An operator
writes `positionnamed = OD1` rather than knowing that OD1 is slot 2. The daemon
validates the name against the configured set and reports the current position
by name when it matches one.

**Soft versus hard limits.** Soft limits come from config and are enforced by
the daemon's validator before any motion command is issued. Hard limits are
read from the controller and exposed read-only, so a client can see the
difference between "the software won't let me" and "the hardware can't".

**Config-declared keywords.** Some daemons generate their keyword set from
config rather than hardcoding it. The Lakeshore and SRS PTC10 daemons register
one keyword per entry in `sensors:` and `heaters:`, named by the config:

```yaml
sensors:
  - channel: 2A
    keyword: t2A_red_etalon
heaters:
  - id: Out 1
    keyword: Out1_red_etalon
```

This is what lets `hscal_hkettherm` and `hscal_yjettherm` — the same PTC10
daemon watching different etalons — present channel names that mean something
to the person reading them.

Configs in `config/` are the versioned source of truth; deployment copies them
to `/etc/hispec/`. The two can drift, and nothing currently detects that — see
{doc}`conformance`.

## Degraded operation

HISPEC daemons are built to stay up when hardware is absent. `on_start`
registers keywords first, then attempts the hardware connection; a failure is
logged and recorded in the `error` keyword, and the daemon continues serving.
Every hardware-touching method re-checks the connection and returns a structured
error rather than raising through the transport.

This is a deliberate trade for an instrument in AIT, where controllers are
routinely unplugged, on a bench at a different site, or out for RMA. It means
`libby show hsfei.atcfw.isconnected` answers truthfully instead of timing out
against a dead process, and a systemd restart loop does not mask the fact that
someone simply unplugged a box.

The trade-off is that "daemon running" does not imply "mechanism available", so
readiness must be read from the keywords, not from `systemctl is-active`. The
one recent tightening of this rule: as of #206, a *commanded* connection
(writing `isconnected = true`) raises on failure rather than reporting success,
because a client explicitly asking to connect needs to know it did not work.

## Where the architecture is heading

The layers described above — drivers, daemons, config, transport — are the
foundation, and they are in place. The COO reference architecture puts three
more layers above them, and HISPEC is being built toward that shape.

```{mermaid}
flowchart TB
    SEQ["sequencer / orchestration<br/><i>planned</i>"]
    PROC["procedures — operational workflows<br/><i>planned</i>"]
    ALG["algorithms — decisions and fits<br/><i>planned</i>"]
    GUI["operator and engineering GUIs<br/><i>planned</i>"]
    KW["keyword interface — in place"]
    DAE["device daemons — in place"]
    DRV["drivers — in place"]
    HW["hardware"]

    SEQ --> PROC
    PROC --> ALG
    PROC --> KW
    SEQ --> KW
    GUI --> KW
    KW --> DAE
    DAE --> DRV
    DRV --> HW

    classDef planned stroke-dasharray: 5 5
    class SEQ,PROC,ALG,GUI planned
```

The load-bearing decision has already been made, and it is what makes the rest
additive: **every layer above the daemons reaches hardware through the same
keyword interface.** A sequencer, a GUI and an engineer at a CLI are all
ordinary clients. Nothing added above gets a private control path, so nothing
added above can bypass a daemon's validation, limits or logging.

**Procedures and algorithms.** The COO model separates the two — *algorithms
decide, procedures do*. An algorithm computes a best-focus fit or a pointing
correction; a procedure moves the stage, triggers the exposure, calls the
algorithm and commands the result. HISPEC has neither yet: every daemon is a
leaf, and `src/hispec/api/` is the placeholder where this library will live.
The rule being adopted with it is that reusable behaviour belongs in the
library, not inside a daemon entrypoint — which is why daemons are kept thin
now, before there is pressure to embed workflow logic in them.

**Orchestration.** Multi-subsystem workflows — configure for a target, run a
calibration sequence, start and end of night — become procedures called by an
orchestration daemon. Per the specification, it will use the same keyword
contract as every other client.

**Operator and engineering GUIs.** Built as keyword clients. The KTL-era `qt/`
tree is not the starting point for this; see {doc}`evolution`.

**Published telemetry.** Daemons currently expose state for polling. The
direction is to publish slow-changing engineering telemetry — thermal, vacuum,
power — on a cadence over libby's pub/sub, which exists and is unused, and to
give it a storage destination. Polling stays the right answer for on-demand
diagnostics and expensive queries.

**Simulation.** Each daemon is to support a simulated backend behind the same
keyword interface, so GUI and sequencer development is not gated on hardware
availability. This is a precondition for building the layers above, not a
testing nicety.

**Remaining subsystems.** `daemons/hscryo`, `daemons/hstt` and `daemons/hscam`
are placeholders for the cryostat, tip-tilt and detector subsystems, and the
spectrograph has no daemon directory yet. These follow the established pattern
as hardware arrives — for mechanisms whose controller type is already
supported, that is a config file rather than new code.

{doc}`conformance` tracks each of these against the specification and puts them
in priority order.
