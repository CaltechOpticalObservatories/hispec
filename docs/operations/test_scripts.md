# Writing Test Scripts

Test scripts drive the instrument through **libby keywords**, the same named
values the `libby` command reads and writes. Each piece of hardware is owned
by a daemon. When your script goes through the daemon, it gets the daemon's
soft limits and error reporting, and every move is recorded in the telemetry
(Grafana). A script that talks to the hardware directly gets none of that,
and it can fight the daemon for the connection. The
[command and control](../architecture/command_and_control.md) page describes
the keyword model in full.

## Start a new script

Start from the template, and put your script in the folder for the part of
the instrument it tests (`scripts/fei/`, `scripts/cal/`, ...):

```bash
cd scripts          # in the hispec checkout
cp TEMPLATE_libby_test.py fei/My_Test_Name.py
```

The template is the same whichever subsystem you test; only the keywords
change.

Fill in the three parts marked **EDIT HERE**: the description at the top,
the settings (which stages, which targets), and `run_test()`, the steps.
The template already connects, checks that everything is ready, stops
stages on Ctrl-C or an error, and prints PASSED or FAILED.
`scripts/fei/PSF_Check_LibbyElements.py` is a complete example built the
same way.

Run it on a machine where the `libby` command works:

```bash
./My_Test_Name.py
```

The template takes no command-line options. If your test needs some, such as
a target or a repeat count, add them with Python's `argparse`;
`PSF_Check_LibbyElements.py` shows how, including a `--move-mode` option that
asks before each move.

## Finding keywords

A keyword is `<group>.<daemon>.<keyword>`, for example
`hsfei.atcl.positionvalue` or `hscal.yjettherm.t2A_blue_etalon`. The group is
the subsystem: `hsfei` (front end), `hscal` (calibration), `hspower` (power
distribution) and so on. Daemons with two axes add the axis name to the
end: `hsfei.ms.positionvalueh` and `hsfei.ms.positionvaluev`.

```bash
libby list hsfei.ms.%                         # every keyword the MS daemon has
libby describe hsfei.ms.positionvalueh        # type, units, read/write
libby show hsfei.ms.positionvalueh            # current value
libby show hsfei.ms.lasterror                 # the daemon's most recent error
```

The [daemon inventory](../architecture/daemons.md) lists every daemon in
every subsystem and what it controls.

## In your script

| To | Write |
|---|---|
| Read a value | `client.get("hscal.yjettherm.t2A_blue_etalon")` |
| Write a value | `client.set("hsfei.atcfw.positionnamed", "OD1")` |
| Wait for a condition (up to 30 s) | `client.wait_for("$hsfei.atcl.ismoving == false", 30)` |
| Describe a stage | `ATCL = Stage("hsfei.atcl")`, or `Stage("hsfei.ms", "h")` for one axis of a two-axis daemon |
| Move a stage, wait, and check it arrived | `move_and_verify(client, ATCL, 7.15)` |
| Check where a stage is | `in_position, position = at_target(client, ATCL, 7.15)` |

A `Stage` works for any motion daemon that has the usual `positionvalue`,
`ismoving` and `isreferenced` keywords; check with `libby list`. For a daemon
without `ismoving` or `isreferenced`, such as a filter wheel, say so:
`Stage("hsfei.atcfw", tolerance=0, has_ismoving=False, has_isreferenced=False)`.

Some subsystems have their stages ready-made. The FEI ones are in `hispec.fei`
(`from hispec.fei import ATCL`): `MS_H`, `MS_V`, `LSM_H`, `LSM_V`, `ATCP`,
`ATCL` and `ATCFW`.

## Rules

- **Do** list every stage you might move in `STAGES`, so it is checked before
  the test and halted if the test stops early.
- **Do** use `move_and_verify` for stages rather than `client.set` on a
  position, so the script waits for the move and confirms it.
- **Don't** import from `hispec.driver`, `pipython`, `serial` or any other
  hardware library, and don't put IP addresses or `/dev/tty...` ports in a
  script.
- **Don't** add `time.sleep()` to wait for hardware; wait on a keyword.

Some hardware has no daemon yet, for example the FEI's ILS source stage,
FSM and red power meter. Tests that need them cannot follow these rules until those
daemons exist; talk to the software team before writing one.

## When it fails

| Message | Meaning | What to do |
|---|---|---|
| `not ready to move: ... isconnected is False` | The daemon has lost its controller | Check the hardware is powered; `libby modify <group>.<daemon>.isconnected true` |
| `not ready to move: ... isreferenced... is False` | The stage has not been homed | Home it: `libby modify <group>.<daemon>.isreferenced true` |
| `could not read (...)` | The daemon did not answer | Check it is running: `hispec status` (see [systemd](systemd.md)) |
| `move to ... refused: ... softmax ...` | The target is outside the stage's limits | Check the target value and units |
| `still moving after ...s; halted` | The move took too long and was stopped | Check the stage; look at `lasterror` |
| `stopped at ..., not within ...` | The stage stopped in the wrong place | The message includes the daemon's `lasterror` |

Nothing moves when a `not ready` check fails.
