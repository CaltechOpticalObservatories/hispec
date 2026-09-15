# Command and Control

This page describes the contract between a HISPEC daemon and anything that
talks to it. It is the instrument-specific expansion of the COO
[Command-and-Control Design Specification][ics-spec].

## The keyword model

HISPEC has no separate "command" concept. Everything — reading a temperature,
moving a stage, homing an axis, stopping a daemon — is a **keyword**: a typed,
named value with a uniform two-shape payload convention.

```text
{}                  → show:   return the current value
{"value": V}        → modify: apply V, then return it
```

A keyword is read-only, write-only or read-write depending on whether it was
registered with a getter, a setter, or both. Triggers are write-only keywords
whose value is irrelevant — firing is the point.

Each keyword carries metadata that clients can query rather than hardcode:
type, access mode, `units`, a human `description`, a `validator`, and
`timeout_s` for operations too slow for the default RPC deadline. The CLI uses
`timeout_s` to extend its own deadline when it modifies a slow keyword, so
homing a stage does not time out on the client side while succeeding on the
hardware.

Two meta-services are auto-registered on every daemon, which makes a daemon
self-describing:

```bash
libby list hsfei.atcfw.%              # every keyword this daemon serves
libby describe hsfei.atcfw.positionvalue
```

### Why keywords rather than commands

This inherits Keck's KTL keyword model, and it is the reason the migration
described in {doc}`evolution` was tractable: operators, scripts and
documentation at Keck already think in terms of keywords, and a keyword-shaped
interface over a new transport preserves that vocabulary. The cost is that
HISPEC gets no free command lifecycle — the spec's `accepted` / `running` /
`completed` progression has no direct representation. See
{doc}`conformance`.

## Addressing

```text
<group>.<peer>.<keyword>
```

Group and scope must both be explicit; `%` wildcards are allowed in the keyword
name for `list`, not in the group or peer. Names are matched case-insensitively
because both client and daemon normalise through the same function.

## Client surfaces

**CLI** — for interactive work and shell scripts:

```bash
libby show    hsfei.ms.positionnamed
libby modify  hsfei.ms.positionnamed keck_mask
libby list    hsfei.ms.%
libby waitfor hsfei.ms.ismoving == false
```

`waitfor` is libby's equivalent of `ktl.waitFor`: it blocks until a keyword
satisfies a condition, which is how a script sequences a move without polling.

**Python** — `libby.Client` is a long-lived in-process handle for reading and
writing keywords and for `wait_for`. This is the supported path for engineering
scripts.

**Direct RPC** — `libby.rpc(peer, key, payload)` underneath both of the above.

There is no GUI client at present.

## Validation and safety

Safety is enforced in the daemon, next to the hardware, as the specification
requires. A client may pre-validate for usability but is never the only check.

The enforcement points, in the order a write passes through them:

1. **Type coercion** — the keyword's declared type rejects a value that cannot
   be coerced.
2. **Validator** — a per-keyword callable returning an error string. Motion
   keywords use it for soft limits (`_check_soft_limits`) and named-position
   keywords for membership in the configured set (`_check_named`), which is
   also where the error message lists the available names.
3. **Connection check** — every hardware-touching method verifies the
   connection first and returns `{"ok": False, "error": ...}` rather than
   calling into a dead driver.
4. **Daemon-specific interlocks** — the clearest example is the PI daemon's
   `shutdown`, which refuses while any stage is moving: stopping a daemon
   mid-motion would abandon a moving stage with no owner.

Soft limits are re-checked inside `set_pos` as well as in the validator. The
duplication is deliberate — the method is reachable from paths that do not go
through keyword validation.

### Safe-state behaviour

`halt` stops motion on every axis a daemon owns and is safe to repeat. `on_stop`
disconnects from the hardware on the way down.

Beyond that, safe-state handling is still being built out: HISPEC has no
instrument-wide safe state, no park positions, and no fault state that inhibits
further commands — a daemon that has recorded an error will still accept the
next write. The direction is for each daemon to define what safe state means
for its own subsystem and to refuse non-recovery commands once faulted; see
Stage 1 of the {doc}`roadmap <conformance>`.

## Error reporting

A HISPEC daemon reports failure through three channels, which is more than the
specification requires but less coherent than it asks for:

| Channel | Shape | Who sees it |
|---|---|---|
| Raised exception | RPC error back to the caller | the client that made the failing call |
| `error` keyword | last error string in the daemon's own state | any client that reads it |
| `lasterror` keyword | last `logger.error()` message, clearable | any client that reads it |
| Log | journald, or `logging.file` if configured | whoever is on the host |

Internally, daemon methods return `{"ok": bool, ...}` dicts, and a
`keyword_wrapper` helper converts a non-ok result into a `RuntimeError` at the
keyword boundary so the failure reaches the client rather than being swallowed.

There is no structured error model — no error codes, no machine-readable
categories. Errors are strings.

## Daemon lifecycle

```{mermaid}
stateDiagram-v2
    [*] --> Starting: systemd ExecStart
    Starting --> Registering: from_config_file() + serve()
    Registering --> Serving: keywords registered
    Serving --> Connected: hardware connect succeeds
    Serving --> Degraded: hardware connect fails
    Degraded --> Connected: write isconnected = true
    Connected --> Degraded: connection lost / isconnected = false
    Connected --> Stopping: shutdown trigger or SIGTERM
    Degraded --> Stopping: shutdown trigger or SIGTERM
    Stopping --> [*]: on_stop() disconnects
```

The sequence in `on_start` is load config → register keywords → attempt
hardware connection. Keywords come first so the daemon is inspectable even when
the connection fails; `Degraded` above is a description of observable behaviour,
not a state the daemon names or publishes.

Shutdown has two paths: SIGTERM from systemd, and the `shutdown` keyword, which
lets an engineer stop a daemon over the same interface used for everything else
rather than needing host access. Both land in `on_stop`, which disconnects the
hardware.

The states in this diagram are **not** exposed as a keyword. A client infers
them from `uptime` and `isconnected`.

## Transport

RabbitMQ, brokered, set once instrument-wide by `HispecDaemon`. libby
discovery is disabled because the broker provides its own; a daemon is
reachable as soon as it binds, without a discovery handshake.

The wire envelope comes from `bamboo` and carries protocol version, message
type (`REQ`/`RESP`/`ACK`/`PUB`/`HELLO`/`CONFIG`/`SUBSCRIBE`), a transaction ID,
the key, source and destination IDs, a timestamp, and the JSON payload with
optional binary attachment. HISPEC does not construct envelopes itself and does
not surface the transaction ID to daemon code — see {doc}`conformance` for what
that costs.

Pub/sub exists in libby and is unused by HISPEC: no daemon publishes telemetry
or events. All monitoring is polled.

## Idempotency

The specification asks each command to declare whether repeated invocation is
safe. For HISPEC's keyword set this follows from the keyword kind:

| Keyword kind | Idempotent | Note |
|---|---|---|
| Any read (`show`) | yes | No side effects. |
| `positionvalue`, `positionnamed` | yes, w.r.t. destination | Re-commanding the same target is safe; commanding a new one during a move is not guarded. |
| `softmin`, `softmax`, setpoints, PID terms | yes | Absolute values. |
| `isconnected` | yes | Writing `true` while connected is a no-op. |
| `isreferenced` | no | Writing `true` re-runs the homing sequence. |
| `halt` | yes | Safe to repeat, by design. |
| `shutdown` | yes | Second call has nothing to stop. |
| `resetstatistics<n>` (PDU) | no | Destroys accumulated counters. |

This table is documentation of current behaviour, not an enforced contract;
nothing in the code marks a keyword idempotent.

[ics-spec]: https://caltechopticalobservatories.github.io/coo-software-architecture/ics_cmd_ctrl.html
