# Conformance and Roadmap

The COO [Command-and-Control Design Specification][ics-spec] and
[Message Envelope and Payload Design][envelope-spec] define the architecture
HISPEC is building toward. This page tracks the instrument against them,
requirement by requirement: what is in place, what HISPEC adapts to its own
needs, and what is planned next.

It is maintained as a working tracker rather than a one-off audit. Each
iteration of the architecture (see {doc}`evolution`) has closed items on this
page, and the order of the roadmap at the end reflects what the next one should
close.

Legend: **In place** · **Partial** · **Planned** · **Adapted** (deliberate
instrument-specific difference, with the reason given).

## Summary

The specification's foundation is in place, and it is the part that matters
most during AIT: hardware is owned by daemons, the command interface is uniform
and self-describing, safety is enforced next to the hardware, and configuration
is data. HISPEC built these first deliberately, because they are the
requirements that are expensive to retrofit.

What remains concerns *operating the instrument at scale* — command
traceability, published status, daemon readiness, ownership. None of it has
been exercised yet, because the clients that need it (a sequencer, a GUI) are
themselves planned rather than built. The architectural priority is to put
these in place **before** those clients exist, since each one changes the
contract they would be written against.

The next item to close is **command traceability**: the transport already
carries a transaction ID, and surfacing it costs little compared to what it
returns.

## Required components (§5)

| Requirement | Status | Detail |
|---|---|---|
| §5.1 Device daemons own hardware | **In place** | One daemon per controller, sole owner of the connection. No client path bypasses a daemon. |
| §5.1 Daemons validate against state and limits | **In place** | Per-keyword validators, soft-limit checks, connection checks before every hardware call. |
| §5.1 Daemons publish status and telemetry | **Partial** | Status is *available* as keywords, but nothing is published — all monitoring is polled. |
| §5.1 Daemons report command completion or failure | **Partial** | A modify returns the applied value or raises. There is no distinct completion event for a long-running operation; a move reports through `ismoving`, which the client must poll or `waitfor`. |
| §5.1 Daemons enter fault or safe states | **Planned** | No fault state. A daemon that has recorded an error will accept the next command. |
| §5.2 Command transport | **In place** | RabbitMQ, brokered, uniform across the instrument. |
| §5.2 Associate replies and events with a command identifier | **Planned** | See [Command identity](#command-identity-64). |
| §5.3 Status and event transport independent of replies | **Planned** | libby supports pub/sub; HISPEC uses none of it. |
| §5.3 Minimum published status (heartbeat, state, mode, readiness, fault) | **Planned** | Of the required set, only liveness (`uptime`) and connection state exist, and both are polled. No daemon state, mode, readiness or fault keyword. |
| §5.4 Configuration and limits as structured data | **In place** | Per-instance YAML, versioned in `config/`. Hardware limits, software limits, named positions, timeouts all declared. |
| §5.4 Named operating modes | **Planned** | No mode concept at all — no science/calibration/engineering/safe mode. |
| §5.5 Command and event logging | **Partial** | Everything is logged to journald with a timestamp and daemon identity. Of the specification's minimum command-log fields, the ones that identify a *command* — command ID, requester, parameters, accept/reject, start/end, duration, final result — are absent. |

## Command contract (§6)

| Requirement | Status | Detail |
|---|---|---|
| Uniform command envelope | **Adapted** | HISPEC has no command envelope because it has no commands. Everything is a keyword `show`/`modify` with a `{}` / `{"value": V}` payload. |
| Request fields (`command_name`, `requester`, `timeout`, …) | **Adapted** | The keyword name and target are carried in the routing key; `timeout_s` is declared per keyword rather than per request. `requester` and `priority_or_mode` have no equivalent. |
| Response fields (`accepted`, `status`, `error_code`, …) | **Partial** | Success returns the value; failure raises with a message. No `accepted` distinct from `completed`, and no `error_code` — errors are strings. |
| Completion fields (`start_time`, `duration`, `final_status`) | **Planned** | Not produced. |

### Command identity (§6.4)

The specification is unambiguous here: *"A command shall not disappear into the
system without a traceable identifier."*

The transport already complies. `bamboo`'s envelope carries `transid`, a UUID
reused across the ACK and response of one transaction. What is missing is
everything above it: libby does not pass the transaction ID to the keyword
handler, HISPEC daemons never see it, and nothing writes it to a log line.

The practical consequence: given a failure report of the form "the mask selector
didn't move last Tuesday", there is no way to find which client asked, what it
asked for, whether the daemon accepted it, or how long it ran. The journal shows
what the daemon did, not what it was asked to do or by whom.

Closing this needs work in libby, not in HISPEC — surfacing `transid` in the
handler context, and logging one structured line per keyword modify with the
transaction ID, the requester, the keyword, the value, the outcome and the
duration. It is first in the [Roadmap](#roadmap) for that reason: a small
change with disproportionate operational value, and cheaper to make before the
sequencer exists than after.

## State models (§7)

| Requirement | Status | Detail |
|---|---|---|
| §7.1 Command lifecycle (`requested` → `accepted` → `running` → `completed`/`failed`/`cancelled`) | **Planned** | No representation. A modify is synchronous from the client's perspective; a long operation is tracked through a separate `ismoving` keyword rather than through the command's own state. There is no cancellation, only `halt`, which is a separate command. |
| §7.2 Daemon lifecycle (`offline`/`starting`/`initializing`/`idle`/`busy`/`ready`/`fault`) | **Planned** | Not exposed. A client infers liveness from `uptime` and hardware availability from `isconnected`, and cannot distinguish "busy" from "idle" or see "fault" at all. |

Of the two, the daemon lifecycle is the one to build first. "Are all required
daemons ready?" is the precondition a sequencer asks before it does anything
else, and it is inexpensive to expose, since every daemon already tracks the
answer internally — it simply has no keyword to report it through.

The command lifecycle follows from the keyword model and needs more thought.
HISPEC's `show`/`modify` contract has no natural place for `accepted` versus
`running`, so representing a long-running operation properly means either a
split-phase keyword convention or per-operation state keywords. The current
approach — a separate `ismoving` keyword plus `waitfor` — covers motion, and
generalising it is the open design question.

## Safety (§8)

| Requirement | Status | Detail |
|---|---|---|
| §8.1 Local safety enforcement | **In place** | Soft limits, named-position validation, type coercion and connection checks all run in the daemon. Clients are never the only check. |
| §8.1 Reject commands while in fault state | **Planned** | No fault state to reject from. |
| §8.1 Reject commands from unauthorised clients | **Planned** | No authorisation — see §9. |
| §8.2 Defined safe state per subsystem | **Partial** | `halt` stops motion and `on_stop` disconnects, but no daemon defines or can enter a parked, drive-disabled safe state, and none is documented per subsystem. |
| §8.3 Fault handling (inhibit, enter fault state, publish, require explicit recovery) | **Planned** | A fault is logged and recorded in `error`/`lasterror`. Nothing is inhibited, nothing is published, and no explicit recovery action is required before the next command. |

One interlock does exist and is worth noting as the pattern to generalise: the
PI daemon refuses `shutdown` while a stage is moving.

## Ownership and authority (§9)

**Planned**, in full. There are no read-only, operator, sequencer, engineering
or administrative roles yet. Any client that can reach the broker can command
any mechanism, there is no engineering mode, and no notion of a long-running
command owning a device for its duration — two clients can command the same
stage concurrently, and the second write simply wins.

Today this is held by network topology and by there being few clients, all
operated by the same small team. That holds for AIT and stops being adequate
the moment a sequencer runs alongside an engineer with a CLI — which is the
deadline for this work. The minimum to adopt first is a read-only role and
device ownership for the duration of a long-running command; the full role
model can follow.

## Sequencer (§10)

**Planned.** The sequencer, the procedure library and the orchestration layer
are the next major architectural addition; `src/hispec/api/` is the placeholder
reserved for them. The shape is set by the COO model and sketched in
{doc}`overview` — procedures coordinate, algorithms decide, and the daemons
stay thin.

The groundwork for it is already done, and deliberately so: because every
daemon is reachable through the same keyword contract, a sequencer needs no new
control path. The specification's rule that sequencers use the same API as
other clients is satisfied by construction — there is no private path for one
to take.

## Simulation (§11)

**Planned.** No daemon supports a simulated backend yet; hardware-free testing
is limited to `tests/util/`, which covers drivers rather than daemons.

The degraded-start behaviour is not a substitute. A daemon with no hardware
reports `isconnected = false` and refuses operations, which exercises the error
paths but cannot exercise a successful move, a completing home or a stable
temperature. That makes simulation a dependency of the layers above rather than
a testing refinement: a GUI and a sequencer cannot be meaningfully developed
until it exists, which is why it is placed ahead of them in the roadmap.

## Design rules (§14) and anti-patterns (§15)

| Rule | Status |
|---|---|
| Hardware is owned by daemons, not GUIs | **In place** |
| Commands must be traceable | **Planned** |
| Status published independently of replies | **Planned** |
| Safety checks belong near the hardware | **In place** |
| Sequencers use the same API as other clients | **In place by construction** — there is no private path a sequencer could take |
| Configuration should be data, not hidden code | **In place** |
| Simulation should use the same interfaces | **Planned** |

Against the specification's anti-pattern list, HISPEC has avoided the ones
that are structural and hard to undo: the GUI does not control hardware, status
is not GUI-local text, there is a shared state model for keywords,
configuration is not hardcoded, and there are no private control paths. Those
were the expensive ones to get right, and the iterations described in
{doc}`evolution` are what bought them.

Four remain on the list — *commands have no IDs*, *no standard error model*,
*no ownership rules*, *no simulator*. Each is additive rather than structural,
which is why they can be sequenced deliberately in the roadmap below instead of
forcing a redesign.

## Message envelope conformance

HISPEC inherits the envelope through libby → bamboo rather than implementing
it, so conformance is bamboo's. Field-by-field against the specification:

| Spec field | bamboo `Envelope` | Note |
|---|---|---|
| `version` | `version` | ✅ |
| `msg_type` | `type` | Name differs. Values `REQ`/`RESP`/`ACK`/`PUB`/`HELLO`/`CONFIG`/`SUBSCRIBE` — the spec also lists `ERROR` and `HEARTBEAT`, which bamboo does not define. |
| `trans_id` | `transid` | Name differs. |
| `key` | `key` | ✅ |
| `src_id` / `dest_id` | `sourceid` / `destid` | Names differ. |
| `timestamp` | `time` | Name differs; string rather than numeric epoch. |
| `qos` | — | Not implemented. |
| `delivery_policy` | — | Not implemented. |
| `payload` | `payload` | ✅ |
| `binary` | `Message.binary` | Carried on the message rather than in the envelope. |

Structurally conformant; the naming differs throughout and two QoS fields are
absent. Since no HISPEC code constructs envelopes, renaming is a libby/bamboo
concern and invisible to this repository. It only becomes a problem if another
COO system implements the specification literally and expects to interoperate on
the wire — worth resolving in bamboo before that happens.

The one behavioural difference to resolve is `ERROR`: bamboo has no error message type, which
is consistent with HISPEC having no structured error model. Failures travel as
raised exceptions rather than as typed error messages.

## Roadmap

The order below is the intended sequence of work, chosen by leverage rather
than by severity. It is grouped by what each stage unlocks.

### Stage 1 — make the control layer observable

These change the contract that every future client is written against, so they
come before the clients.

1. **Surface and log the transaction ID.** The transport already carries it.
   One structured log line per keyword modify — transaction ID, requester,
   keyword, value, outcome, duration — turns the journal from a record of what
   daemons did into a record of what they were asked to do. Requires a libby
   change; highest leverage item on this list.
2. **Add a daemon state keyword.** `starting` / `idle` / `busy` / `ready` /
   `fault`, exposed like any other keyword. Each daemon already tracks its
   state; this publishes it. Precondition for any readiness check and for the
   sequencer.
3. **Add a fault state that inhibits commands.** Once (2) exists, a faulted
   daemon should refuse non-recovery commands until explicitly cleared, rather
   than accepting the next write as if nothing happened.
4. **Adopt structured error codes.** A small enumeration —
   `NOT_CONNECTED`, `LIMIT_EXCEEDED`, `INVALID_NAME`, `HARDWARE_ERROR`,
   `BUSY` — lets a client branch on a failure instead of matching strings.

### Stage 2 — make the instrument developable without hardware

5. **Add a simulation backend, starting with one daemon.** The filter wheel is
   the natural first: small keyword set, five deployed instances, and it proves
   the pattern for the rest. Everything in Stage 3 is gated on this.

### Stage 3 — build the layers above

6. **Define ownership before the sequencer exists.** The minimum — a read-only
   role, and a long-running command owning its device for its duration — is far
   cheaper to adopt now than to retrofit around an operating sequencer.
7. **Build the procedure and algorithm library**, then the orchestration daemon
   that calls it. Reusable behaviour goes in the library; daemons stay thin.
8. **Build the operator and engineering GUIs** as keyword clients.

### Ongoing

9. **Publish telemetry rather than polling it.** Thermal and vacuum keywords
   are the first candidates: slow-changing, many potential consumers, and no
   path to archiving them today.
10. **Detect config drift.** `config/` is the versioned source of truth,
    `/etc/hispec/` is what runs, and nothing compares them. A daemon reporting
    the checksum of its loaded config as a keyword would make drift visible.
11. **Reconcile envelope field naming with the specification** in bamboo,
    before another COO system implements it literally and expects to
    interoperate on the wire.

Stage 1 is the current priority. Each item there is small on its own, and
together they are what turn a set of working daemons into an instrument that
can be operated and diagnosed by someone who was not in the room when it was
built.

[ics-spec]: https://caltechopticalobservatories.github.io/coo-software-architecture/ics_cmd_ctrl.html
[envelope-spec]: https://caltechopticalobservatories.github.io/coo-software-architecture/message_envelope_and_payload_design.html
