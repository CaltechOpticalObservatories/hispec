# Software Architecture

This section describes the software architecture of the HISPEC Instrument
Control System (ICS): the design the instrument is being built toward, the
COO specifications it follows, and how far each part of it has been realised.

It is written to answer four questions:

1. **What is the shape of the system, and where is it going?** — see
   {doc}`overview`.
2. **What does it consist of?** — every daemon, driver, config and keyword is
   enumerated in {doc}`daemons`.
3. **What is the contract a client can rely on?** — see
   {doc}`command_and_control`.
4. **How did the design get here?** — see {doc}`evolution`.

{doc}`conformance` then tracks HISPEC against the
[COO Command-and-Control Design Specification][ics-spec] and the
[Message Envelope and Payload Design][envelope-spec], recording what is in
place, what is adapted to the instrument, and what is planned next.

## Reference specifications

HISPEC does not define its own control architecture from scratch. It is an
instrument-specific expansion of the COO specifications:

| Specification | Role for HISPEC |
|---|---|
| [Command-and-Control Design Specification][ics-spec] | The architectural spine: stateful device daemons own hardware, a shared command contract, explicit lifecycles, locally enforced safety, command logging. |
| [Message Envelope and Payload Design][envelope-spec] | The wire protocol. HISPEC inherits it through libby → bamboo rather than implementing it directly. |

## How this document is written

HISPEC's control architecture has been developed iteratively. It has been
redesigned twice since the repository was created in October 2024 — from the
Keck KROOT/KTL build, through a first generation of standalone daemons, to the
current libby keyword architecture — and each iteration moved the instrument
closer to the COO command-and-control model. That history is documented in
{doc}`evolution`, because knowing why a design was left behind is what stops it
being re-proposed.

This document states the architecture HISPEC is building toward, not a
snapshot. The COO specifications define the target; these pages describe how
HISPEC realises them for this instrument, and the direction of travel for the
parts still being built.

Because the instrument is in Assembly, Integration and Test, that direction
matters more than any single point along it. Implementation status is therefore
marked per element rather than assumed:

| Marker | Meaning |
|---|---|
| **In place** | Implemented and deployed. |
| **Partial** | Implemented for some daemons or some of the contract. |
| **Planned** | Design decided, not yet built. Listed with its place in the roadmap. |
| **Adapted** | HISPEC deliberately differs from the specification; the reason is given. |

Nothing described as Planned should be read as existing. Coverage across
subsystems is uneven by design: the FEI (`hsfei`) and calibration (`hscal`)
subsystems have deployed daemons and are where the architecture is being
proven, while the spectrograph, tip-tilt, cryostat and detector subsystems
follow the same pattern as their hardware arrives.

```{toctree}
:maxdepth: 2

overview
daemons
command_and_control
evolution
conformance
```

[ics-spec]: https://caltechopticalobservatories.github.io/coo-software-architecture/ics_cmd_ctrl.html
[envelope-spec]: https://caltechopticalobservatories.github.io/coo-software-architecture/message_envelope_and_payload_design.html