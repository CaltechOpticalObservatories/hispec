# Architecture Evolution

The HISPEC control architecture has been rebuilt twice since the repository was
created in October 2024, each time moving closer to the COO command-and-control
model. Reading the tree today, that history is visible: directories from
earlier eras sit alongside current ones, and it is not obvious from the
filenames which are live.

This page records what changed and why, which parts of the tree are dead, and
where the next iteration goes. Knowing why a design was left behind is what
stops it being re-proposed — and the reasons are what justify the shape of the
architecture described in {doc}`overview`.

```{mermaid}
timeline
    title HISPEC ICS architecture eras
    section KROOT / KTL
        Oct 2024 : Keck KROOT tree imported
                 : XML keyword definitions, C/Python dispatchers
                 : Qt GUI scaffolding, init.d service scripts
    section Driver library
        Apr–Aug 2025 : Vendor drivers as COO-Utilities submodules
                     : pip-installable src/ layout
                     : Daemons hoisted to daemons/
    section Standalone daemons
        Nov–Dec 2025 : First per-mechanism daemons
                     : HispecDaemon base over libby transport
                     : YAML config ingestion
    section libby keywords
        2026 : Keyword registry replaces service dicts
             : HispecDaemon collapses onto LibbyDaemon
             : peer_id / group_id naming, systemd deployment
    section Next — additive
        Planned : Command traceability, daemon state, fault handling
                : Simulation backends
                : Procedures, algorithms, orchestration, GUIs
```

## Era 1 — KROOT / KTL (Oct 2024 – mid 2025)

HISPEC started as a Keck KROOT tree, the standard Keck instrument software
build. Control interfaces were declared as XML keyword definitions and `.defs`
files, compiled by KROOT `Makefile`s into dispatchers, with service directories
per subsystem and `init.d` scripts to start them.

The surviving artefacts are `daemons/hsowenv` (1-Wire environment),
`daemons/hsdewar` (Lakeshore dewar control), `daemons/hsssd`, plus `Makefile`,
`Mk.instrument`, `init.d/` and `qt/`. `daemons/hspower` was one of them until
its KROOT scaffolding was removed and the directory reused for the libby PDU
daemon.

**Why it moved on.** KROOT ties development to a summit-like environment: the
build needs `/kroot` and Keck-internal modules (`DFW`, `SerialStream`) that do
not exist on a developer laptop or a bare Ubuntu box. For an instrument being
built at Caltech and Palomar, years before summit integration, that made the
normal development loop — write code, run it against a controller on the bench —
unreasonably expensive. The `.sin` template and `Makefile` layer also meant that
adding a mechanism was a build-system change rather than a configuration change.

## Era 2 — the driver library (Apr – Aug 2025)

Before the control architecture was settled, the hardware layer was. Through
2025, low-level drivers were written for each controller — Sunpower, PI,
Newport, Xeryon, Inficon, Lakeshore, Standa, Thorlabs — and pulled out into
their own repositories under the
[COO-Utilities](https://github.com/COO-Utilities) organisation, vendored back
as git submodules.

Two restructures in this period (#6, #14) moved the repository to a `src/`
layout so it became a normal pip-installable Python package, and #73 in August
2025 hoisted the service directories to a top-level `daemons/`.

This era's output is the part of the architecture that has survived both
rewrites unchanged. Drivers are the stable layer precisely because they know
nothing about the control architecture above them: the same
`hispec.driver.thorlabs.fw102c` served the KTL dispatcher and serves the libby
daemon.

In February 2026 the package namespace was renamed `hispec.util` →
`hispec.driver` (#127), making the layer's role explicit.

## Era 3 — standalone daemons (Nov – Dec 2025)

The first daemons that owned their own hardware and process appeared in
November 2025: `calyjrack`, then `atcpress`. In December, the pattern was
generalised — #113 added a `HispecDaemon` base class (a ~220-line class over
`libby.Libby`, handling signals, lifecycle and a `services` dict of RPC
handlers), and #115 added YAML config ingestion.

This is the era that set the durable shape of the system: one executable per
mechanism type, `-c config.yaml`, a base class that owns the transport, and
configuration rather than code as the way to add a mechanism.

**Why it moved on.** The `services` dict was a bag of named RPC handlers with no
type information, no units, no declared access mode and no discoverability — a
client had to read the daemon source to know what it served. That is
serviceable for one daemon and unworkable for twenty-two instances across two
subsystems.

## Era 4 — libby keywords (2026 – present)

The current architecture. Three changes, in order:

**Keywords replace service dicts** (April 2026, #135, first in the PI daemon).
libby's `KeywordRegistry` gave typed keywords with getters, setters,
validators, units, descriptions and timeouts, plus auto-generated
`keys.list` / `keys.describe`. A daemon became self-describing, and the
instrument regained the Keck keyword vocabulary on a new transport.

**`HispecDaemon` collapses onto `LibbyDaemon`** (July–August 2026, #152). The
local base class shrank from ~220 lines to four: everything it did was now in
libby, shared with other COO instruments, and all HISPEC needed to say was
"RabbitMQ, discovery off".

**Naming, aggregation and deployment are standardised** (September 2026). The
`-d/daemon-id` flag was dropped in favour of `peer_id` + `group_id` in config
(#174); peer IDs were renamed to lowercase module acronyms matching the Jira
mechanism names (#186); multi-stage daemons gained consolidated whole-mechanism
keywords (#189, #205); a `shutdown` keyword was added so daemons can be stopped
over the same interface as everything else (#195); and systemd template units
made deployment reproducible (#198).

The through-line of all three is the same: make the interface uniform enough
that a client can be written against the instrument rather than against a
particular daemon.

## What is legacy

These directories are from Era 1, are not built, and are not run:

| Path | Was | Status |
|---|---|---|
| `daemons/hsowenv` | KTL 1-Wire environment service | Dead. Last touched Aug 2025 as part of a directory move. |
| `daemons/hsdewar` | KTL Lakeshore dewar dispatcher | Dead. Superseded by `daemons/generic/lakeshore`. |
| `daemons/hsssd` | KTL spectrograph service | Dead. |
| `Makefile`, `Mk.instrument` | KROOT build | Dead. Still references KPF in a comment. |
| `init.d/` | KTL service startup | Dead. Superseded by `systemd/`. |
| `qt/` | KTL-era Qt GUI scaffolding | Dead. Untouched since Oct 2024. Not a starting point for a libby GUI. |

They have been left in place rather than deleted because the XML keyword
definitions still document the intended keyword sets for subsystems whose libby
daemons have not been written — `hsssd` in particular describes the
spectrograph. Treat them as design reference, not as code.

`daemons/hspower` is the one that has been through this: its KTL power service
— `Makefile`, `Mk.service`, the `.conf.in` configs and the `.xml.in` keyword
templates — is gone, and the directory now holds the libby `pdu` daemon,
`pdu_capabilities.py` and `pdu_models/` instead. The old templates are still in
git history if the strip- and outlet-level keyword names are ever wanted.

Two other stale references worth knowing about: `pyproject.toml` still ignores
the Keck-internal `DFW` and `SerialStream` modules for pylint's benefit, and the
root `README.md` described the layout as "each mKTL service has a directory" —
mKTL was evaluated and is not what HISPEC uses.

## In progress

Not yet on `main`, but shaping the next change:

- **Ansible provisioning** (`pgupta/playbook`) — turning the host build notes
  into a playbook, so instrument hosts are provisioned reproducibly rather than
  by following an RST document by hand.
- **Fiber switcher driver** (`pgupta/add_fiber_drivers`) — the
  `hispec-fiber-switcher` submodule is vendored but has no daemon yet.

## Era 5 — the direction

The next iteration is already scoped, and unlike the previous two it is
additive rather than a redesign. The keyword contract, the transport and the
daemon layer stay as they are; what gets built sits above them.

In order: make the control layer observable (command traceability, daemon
state, fault handling, structured errors), then make it developable without
hardware (simulation), then build the layers the COO model puts on top —
procedures, algorithms, orchestration and GUIs.

The sequencing is deliberate. Each of those first items changes the contract
that a GUI or sequencer would be written against, so they are cheaper to adopt
before those clients exist than to retrofit around them. {doc}`conformance`
holds the detail and the priority order; {doc}`overview` sketches the target
shape.

That the next era is additive is the return on the two rewrites. Era 1 ended
because the build system dictated where you could develop; Era 3 ended because
untyped service dicts could not scale past a handful of daemons. Both were
structural limits that no amount of incremental work could relieve. The current
architecture has no equivalent limit in view — the remaining work is a list of
things to add, not a reason to start again.
