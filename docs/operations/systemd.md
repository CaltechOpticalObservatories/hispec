# Running the HISPEC Daemons with systemd

Every HISPEC hardware daemon on an instrument host runs as a systemd service.
This page is what you need to start, stop, watch and debug them. It assumes no
prior systemd knowledge.

If you only want the commands, jump to [Everyday commands](#everyday-commands).
To add a daemon to a host, see [Deploying an instance](#deploying-an-instance).
If something is broken, jump to [Troubleshooting](#troubleshooting).

Everything an operator does goes through one command, `hispec`. `hispec --help`
lists the subcommands and each takes `--help`. Setting a host up in the first
place is a separate, one-time job for an admin; see
[Host setup](#host-setup-admins).

## The idea in one minute

systemd is the thing on a Linux host that starts programs, keeps them running,
restarts them when they crash, and collects their logs. A program it manages is
called a **unit** (more precisely a *service unit*).

HISPEC does **not** have one unit per daemon. It has a single **template**
unit, `hispec@.service`, plus one small text file per daemon telling it what to
run. Each running daemon is an **instance** of that template, written
`hispec@<name>`, for example `hispec@hsfei_adc`. The `<name>` after the `@` is
the instance name, and it is the only thing that differs between them.

```
hispec@.service                     the template, installed once by an admin
  └─ hispec@hsfei_adc               instance: ADC rotators
  └─ hispec@hsfei_ms                instance: mask selector
  └─ hispec@hscal_hketatten         instance: etalon attenuator
```

An instance gets its identity from two files:

| File | What it says |
|---|---|
| `/etc/hispec/instances/<name>.env` | which daemon script to run (`HISPEC_DAEMON`) and which config to hand it (`HISPEC_CONFIG`) |
| `/etc/hispec/<name>.yaml` | the config itself: serial ports, addresses, limits, keyword names |

So running a second Lakeshore is not new code and not a new unit. It is a
second `.env` file pointing at the same daemon script with a different config.

### Two words that are easy to confuse

**start** and **enable** are different operations, and mixing them up is the
most common source of confusion here.

| | What it does | When it takes effect |
|---|---|---|
| `start` | runs the daemon now | immediately, until the host reboots or you stop it |
| `enable` | adds it to the set that comes up at boot | at the next boot; `enable` on its own starts nothing |

`enable --now` does both. You want `start` for day-to-day work. You want
`enable` once, when an instance is first deployed and should survive reboots;
`hispec deploy` does that for you.

## Everyday commands

None of these need `sudo`, as long as you are in the `hispec-ops` group. If you
are being asked for a password, see
[systemctl keeps asking for a password](#systemctl-keeps-asking-for-a-password).

The `hispec` command itself comes from
[instrumentctl](https://github.com/CaltechOpticalObservatories/instrumentctl),
a dependency shared with other instruments. What makes it speak HISPEC is
`src/hispec/cli/instrument.toml`, which names the unit, the ops group and the
`HISPEC_` variable prefix. So a bug in `deploy` or `doctor` is fixed there,
while anything naming HISPEC is fixed here.

```bash
hispec status                    # every deployed daemon: running? at boot? since when?
hispec status -v hsfei_adc       # in detail: its files, PID, exit code, last log lines
hispec start   hsfei_adc         # start it
hispec stop    hsfei_adc         # stop it
hispec restart hsfei_adc         # stop then start, e.g. after a config edit

hispec logs hsfei_adc -f         # follow the log live (Ctrl-C to quit)
hispec logs hsfei_adc -n 500     # the last 500 lines (default 100)
hispec logs hsfei_adc --since "1 hour ago"
```

`hispec status` looks like this:

```
INSTANCE        STATE         BOOT      SINCE                DAEMON
hsfei_adc       active        enabled   2026-09-21 09:14:02  hsfei/adc
hsfei_atcfw     failed        enabled   2026-09-21 09:20:41  generic/filterwheel
hsfei_ms        inactive      disabled                       hsfei/pi-daemon

20 more in the repo, not deployed here (hispec status --all; hispec deploy --new)
```

When something is `failed` or flapping, `hispec status -v hsfei_atcfw` says
why. For each instance it shows which daemon script it runs and which config
it reads, flagging a config that is missing or differs from the repo's copy,
then the full `systemctl status`: PID, memory, how the process last exited,
and the last 10 log lines (`-n 50` for more). See
[Reading `systemctl status`](#reading-systemctl-status) below.

These are wrappers around `systemctl` and `journalctl`, and the plain commands
still work if you prefer them: `systemctl start hispec@hsfei_adc`,
`journalctl -u hispec@hsfei_adc -f`, `systemctl list-units 'hispec@*'`.

### Starting and stopping a whole subsystem

Wherever `hispec` takes an instance name it also takes a subsystem, written
either in full or without the `hs`, or `all`:

```bash
hispec start fei                 # every deployed hsfei_* daemon
hispec stop fei                  # all of them, in reverse order
hispec restart cal               # every hscal_* daemon
hispec start power fei           # PDUs first, then the FEI
hispec stop power fei            # FEI first, then the PDUs
hispec start hsfei_adc hsfei_ms  # or name the ones you want
hispec start --dry-run fei       # print what it would do, do nothing
hispec status fei                # just the FEI
```

Names are matched against what is deployed in `/etc/hispec/instances/`, so
these stay correct as instances are added without anyone editing anything.
`start` leaves already-running daemons alone and `stop` skips stopped ones. If
any instance fails, both carry on with the rest and then exit non-zero, so they
are safe to use from another script. `start` goes in the order you name things;
`stop` goes in the reverse order, so a stop undoes a start.

### Reading `systemctl status`

```
● hispec@hsfei_adc.service - HISPEC hardware daemon (hsfei_adc)
     Loaded: loaded (/etc/systemd/system/hispec@.service; enabled)
     Active: active (running) since Mon 2026-09-21 09:14:02 HST; 2h 3min ago
```

- `Loaded: ... enabled` means the unit file was found and this instance is in
  the boot set. `disabled` here is fine for something you only run by hand.
- `Active: active (running)` means it is up.
- `Active: failed` means it died and systemd gave up restarting it. Look at the
  log.
- `Active: activating (auto-restart)` means it is crash-looping. The daemon
  starts, dies, and systemd restarts it every 5 s. After 5 failures in 60 s
  systemd stops trying and the state becomes `failed`.

`systemctl status` prints the last few log lines, which is usually enough. Use
`journalctl` when it is not.

## Logs

By default a daemon logs to stdout/stderr and systemd captures it into the
**journal**, which is what `journalctl` reads. Logs survive a restart of the
daemon; whether they survive a reboot depends on the host's journal
configuration.

```bash
hispec logs hsfei_adc -f                       # live
hispec logs hsfei_adc -p err                   # errors only
hispec logs fei -f                             # the whole FEI, interleaved
hispec logs all --since today                  # every HISPEC daemon at once
```

If a daemon's YAML config sets `logging.file`, that daemon writes to a file
under `/var/log/hispec/` instead, and the journal will be nearly empty for it.

Reading other users' journal entries requires being in the `systemd-journal`
group. If `hispec logs` prints nothing at all for a daemon you can see running,
that is the reason. Run `hispec doctor`.

## Deploying an instance

One command, no `sudo`, no `install.sh` and no `systemctl daemon-reload`:

```bash
hispec deploy hsfei_atcpress
```

```
hsfei_atcpress
  copied       /etc/hispec/instances/hsfei_atcpress.env
  copied       /etc/hispec/hsfei_atcpress.yaml
enabled at boot: hsfei_atcpress

hsfei_atcpress           started
```

That copies the instance's two files from the repo into `/etc/hispec`, adds it
to the boot set, and starts it. Deploy several at once by naming them, a whole
subsystem, or everything the repo defines that this host does not have yet:

```bash
hispec deploy hsfei_adc hsfei_ms
hispec deploy fei                # every hsfei_* the repo defines
hispec deploy all --no-start --no-enable   # refresh the files, change nothing else
hispec deploy --new              # e.g. after a git pull added instances
hispec deploy --new --dry-run    # see what that would do first
```

Unlike `start` and `status`, `deploy` matches its targets against the repo
rather than what is already on the host, since putting something new on a host
is the point.

A deployed config is never overwritten by default. Once it is on a host it
holds that host's real ports and addresses, so if it differs from the repo
copy, `deploy` keeps it and says so; `--force` replaces it. The `.env` instance
file is different. It only says which script to run and where the config is,
so it always follows the repo. If a daemon was already running when its files
changed, `deploy` prints the `hispec restart` that picks them up.

Two more options: `--no-start` copies and enables but does not start, for
example to fill in a config first. `--no-enable` starts the daemon without
adding it to the boot set.

Why no `daemon-reload`? `hispec@.service` is a template. systemd reads
`/etc/hispec/instances/<name>.env` when the instance starts, not when units are
loaded, so a new instance is just a new file. `daemon-reload` is only needed
when the template itself changes, and `install.sh` does it then.

### Boot set

```bash
hispec enable hsfei_adc hsfei_ms     # add to the boot set, don't start now
hispec enable --now hsfei_adc        # add to the boot set and start
hispec disable hsfei_adc             # remove from the boot set, leave it running
hispec disable --now hsfei_adc       # remove from the boot set and stop
```

Stopping and disabling are independent: `hispec stop` takes a daemon down
until you start it again or the host reboots; `hispec disable` keeps it from
coming back at boot. `enable` and `disable` go through a small root helper (see
[the note on enable/disable](#why-enable-is-a-helper-and-not-just-systemctl)),
which is why plain `systemctl enable` asks for a password and `hispec enable`
does not.

### Adding a daemon that has no instance file yet

In the repo, add the config under `config/<subsystem>/<name>.yaml` and write the
matching `systemd/instances/<name>.env`:

```sh
HISPEC_DAEMON=<path relative to daemons/, e.g. generic/inficon or hsfei/adc>
HISPEC_CONFIG=/etc/hispec/<name>.yaml
HISPEC_HOST=<the host that runs it, e.g. hispecserver or fei>
```

`HISPEC_HOST` is what stops an instance being deployed onto the wrong machine,
where two daemons would reach for one device and collide on the broker.
`hispec deploy` refuses a mismatch unless you pass `--any-host`, and `hispec
doctor` reports anything deployed somewhere it does not belong. A host learns
its own name from `/etc/hispec/host`, which the installer writes.

Also add the row to the table in [Deployed instances](#deployed-instances) and
to the inventory in {doc}`../architecture/daemons`. Commit, then on the host:

```bash
git -C /opt/hispec/app pull
hispec deploy <name>
```

### Secrets

Every unit reads `/etc/hispec/secrets.env` if it exists, and a credential goes
there because that file is not in git, unlike a config. It is `hispec-ops`
read/write (0660), so no `sudo` is needed:

```bash
cat >> /etc/hispec/secrets.env <<'EOF'
HISPEC_INFLUX_TOKEN=<InfluxDB write token>
EOF
hispec restart hispec_keygrabber
```

`hispec doctor` lists the variables this host needs and which daemon asks for
each, derived from the deployed configs, so there is no list to keep current.

`generic/keygrabber` and `hspower/pdu` need one. The nine PDU instances share
a single Telnet login, so two variables cover all of them:

```bash
sudo tee -a /etc/hispec/secrets.env <<'EOF'
HISPEC_PDU_USERNAME=<PDU login>
HISPEC_PDU_PASSWORD=<PDU password>
EOF
```

A config file names the variable it expects rather than holding the value, so
the value never reaches git. For the PDU that is `hardware.username_env` and
`hardware.password_env`; an instance with its own login just names different
variables. Inline `hardware.username` / `hardware.password` still work for a
bench test, but the daemon logs a warning against committing them.

`HispecDaemon` names the broker but holds no password, so every host supplies
one:

```bash
sudo tee -a /etc/hispec/secrets.env <<'EOF'
HISPEC_RABBITMQ_USER=<user>
HISPEC_RABBITMQ_PASSWORD=<password>
EOF
```

Without them a daemon is refused with `ACCESS_REFUSED ... mechanism PLAIN`.

Any top-level config key can also be replaced by a `LIBBY_<KEY>` variable, so
`LIBBY_RABBITMQ_URL` points one host at a different broker entirely. It
replaces the whole URL, credentials included, and wins over the two variables
above.

## Troubleshooting

Start here:

```bash
hispec doctor
```

It checks your group membership, the installed unit and polkit rule, whether
you can enable without a password, the directories, and every deployed
instance, and prints the exact command to fix whatever it finds. Run it as
yourself, not under `sudo`, which would hide the permission problems it is
looking for.

If `hispec` itself says the venv is missing, an admin needs to re-run
`install.sh`.

### systemctl keeps asking for a password

A prompt like

```
==== AUTHENTICATING FOR org.freedesktop.systemd1.manage-units ====
Authentication is required to start 'hispec@hsfei_adc.service'.
Authenticating as: root
Password:
```

means the polkit rule that should have let you through did not match. In order
of likelihood:

1. **You are not in `hispec-ops`.** Check with `id -nG | tr ' ' '\n' | grep
   hispec-ops`. An admin adds you with
   `sudo /opt/hispec/app/systemd/install.sh <your-username>`; you then have to
   log out and back in for it to take effect.
2. **You ran `systemctl enable`, not `start`.** `systemctl enable` and
   `disable` need a different permission that polkit cannot restrict to one
   unit, so they always prompt. Use `hispec enable` instead, which does not.
3. **The polkit rule is not installed**, or is the pre-rename copy that still
   matches `hispec-daemon@`. `hispec doctor` reports both; the fix is for an
   admin to re-run `install.sh`.
4. **The host's polkit is older than 0.106.** JavaScript `.rules` files are
   ignored silently by older versions: no error, just a prompt every time.
   `hispec doctor` checks the version.

You should never need `sudo` to start, stop, restart or look at a HISPEC
daemon. If you do, something in the list above is wrong; please fix it rather
than working around it with `sudo`, because a daemon started as root writes
root-owned log files that then break the next non-root start.

### The daemon will not start

```bash
systemctl status hispec@<name>
hispec logs <name>
```

Common causes, in the order they bite:

- **`Failed to load environment files`**: `/etc/hispec/instances/<name>.env`
  is missing or unreadable. The instance name in the command must match the
  file name exactly.
- **`No such file or directory`** on the config: `HISPEC_CONFIG` points
  somewhere that does not exist. The config has to be deployed to `/etc/hispec/`
  as well as the `.env`. `hispec deploy <name>` copies both; copying one by
  hand and forgetting the other is the usual mistake.
- **A serial port or USB error**: the device is unplugged, powered off, or
  claimed by another process. Two instances pointing at the same port will do
  this to each other, and so will a daemon left running from a manual test.
  `sudo lsof /dev/ttyUSB0` shows who has it.
- **A permission error on a device node**: the `hispec` user needs to be in
  whatever group owns the device (`dialout` for most serial adapters). This is
  a host setup problem; an admin has to fix it.
- **`ModuleNotFoundError`**: the venv is stale. An admin re-runs `install.sh`,
  which reinstalls it.

### It starts and then dies repeatedly

`Active: activating (auto-restart)` in a loop means the daemon is exiting on
its own. The journal has the traceback:

```bash
hispec logs <name> -n 200
```

After 5 failures in 60 seconds systemd stops retrying and leaves the unit
`failed`. Fix the cause, then:

```bash
systemctl reset-failed hispec@<name>
hispec start <name>
```

### A config change has not taken effect

The config is read at startup. Edit `/etc/hispec/<name>.yaml`, then
`hispec restart <name>`. Editing the copy in the repo under
`config/` changes nothing on a running host; the deployed copy under
`/etc/hispec/` is what the daemon reads.

### Picking up code changes

```bash
git -C /opt/hispec/app pull
hispec restart <name>                # or: hispec restart fei
hispec deploy --new                  # if the pull added instances
```

The venv install is editable, so a `pull` is enough, and it updates the
`hispec` command too. An admin only needs to re-run `install.sh` if
dependencies or `hispec@.service` changed. Pulling needs write access to
`/opt/hispec/app`, so either run as `hispec` or ask an admin.

## Deployed instances

| Instance | Host | Daemon | Config |
| --- | --- | --- | --- |
| `hscal_hkcalfwheel1` | `hispecserver` | `generic/filterwheel` | `config/hscal/hscal_hkcalfwheel1.yaml` |
| `hscal_hkcalfwheel2` | `hispecserver` | `generic/filterwheel` | `config/hscal/hscal_hkcalfwheel2.yaml` |
| `hscal_hkgcellfwheel` | `hispecserver` | `generic/filterwheel` | `config/hscal/hscal_hkgcellfwheel.yaml` |
| `hscal_yjcalfwheel1` | `hispecserver` | `generic/filterwheel` | `config/hscal/hscal_yjcalfwheel1.yaml` |
| `hscal_yjcalfwheel2` | `hispecserver` | `generic/filterwheel` | `config/hscal/hscal_yjcalfwheel2.yaml` |
| `hsfei_atcfw` | `hispecserver` | `generic/filterwheel` | `config/hsfei/hsfei_atcfw.yaml` |
| `hsfei_atcpress` | `hispecserver` | `generic/inficon` | `config/hsfei/hsfei_atcpress.yaml` |
| `hscal_gcellheater1` | `hispecserver` | `generic/lakeshore` | `config/hscal/hscal_gcellheater1.yaml` |
| `hscal_gcellheater2` | `hispecserver` | `generic/lakeshore` | `config/hscal/hscal_gcellheater2.yaml` |
| `hsfei_atctherm` | `hispecserver` | `generic/lakeshore` | `config/hsfei/hsfei_atctherm.yaml` |
| `hscal_hkettherm` | `hispecserver` | `generic/srsthermal` | `config/hscal/hscal_hkettherm.yaml` |
| `hscal_yjettherm` | `hispecserver` | `generic/srsthermal` | `config/hscal/hscal_yjettherm.yaml` |
| `hscal_hketatten` | `hispecserver` | `hscal/smc8_attenuator` | `config/hscal/hscal_hketatten.yaml` |
| `hsfei_adc` | `hispecserver` | `hsfei/adc` | `config/hsfei/hsfei_adc.yaml` |
| `hsfei_atccryo` | `hispecserver` | `hsfei/atccryo` | `config/hsfei/hsfei_atccryo.yaml` |
| `hsfei_atcl` | `hispecserver` | `hsfei/pi-daemon` | `config/hsfei/hsfei_atcl.yaml` |
| `hsfei_atcp` | `hispecserver` | `hsfei/pi-daemon` | `config/hsfei/hsfei_atcp.yaml` |
| `hsfei_feipo` | `hispecserver` | `hsfei/pi-daemon` | `config/hsfei/hsfei_feipo.yaml` |
| `hsfei_lsm` | `hispecserver` | `hsfei/pi-daemon` | `config/hsfei/hsfei_lsm.yaml` |
| `hsfei_ms` | `hispecserver` | `hsfei/pi-daemon` | `config/hsfei/hsfei_ms.yaml` |
| `hsfei_piaagimb` | `hispecserver` | `hsfei/piaa-gimbalmount` | `config/hsfei/hsfei_piaagimb.yaml` |
| `hsfei_piaagimr` | `hispecserver` | `hsfei/piaa-gimbalmount` | `config/hsfei/hsfei_piaagimr.yaml` |
| `hsfei_hkfam` | `hispecserver` | `hsfei/xeryon` | `config/hsfei/hsfei_hkfam.yaml` |
| `hsfei_piaadeploy` | `hispecserver` | `hsfei/xeryon` | `config/hsfei/hsfei_piaadeploy.yaml` |
| `hsfei_yjfam` | `hispecserver` | `hsfei/xeryon` | `config/hsfei/hsfei_yjfam.yaml` |
| `hispec_keygrabber` | `hispecserver` | `generic/keygrabber` | `config/hispec/hispec_keygrabber.yaml` |
| `hspower_fei1` | `hispecserver` | `hspower/pdu` | `config/hspower/hspower_fei1.yaml` |
| `hspower_fei2` | `hispecserver` | `hspower/pdu` | `config/hspower/hspower_fei2.yaml` |
| `hspower_cal1` | `hispecserver` | `hspower/pdu` | `config/hspower/hspower_cal1.yaml` |
| `hspower_cal2` | `hispecserver` | `hspower/pdu` | `config/hspower/hspower_cal2.yaml` |
| `hspower_cal3` | `hispecserver` | `hspower/pdu` | `config/hspower/hspower_cal3.yaml` |
| `hspower_cal4` | `hispecserver` | `hspower/pdu` | `config/hspower/hspower_cal4.yaml` |
| `hspower_fib1` | `hispecserver` | `hspower/pdu` | `config/hspower/hspower_fib1.yaml` |
| `hspower_bspec1` | `hispecserver` | `hspower/pdu` | `config/hspower/hspower_bspec1.yaml` |
| `hspower_rspec1` | `hispecserver` | `hspower/pdu` | `config/hspower/hspower_rspec1.yaml` |

The nine `hspower_*` instances are the Eaton PDUs, each named for where its
unit is: two in the FEI, four in the CAL, and one each in the FIB, BSPEC and
RSPEC. They all need the Telnet login in `/etc/hispec/secrets.env` (above)
before they can connect, and the ones whose address is not yet known carry a
TODO in their config — those start and serve their keywords, but report
`missing PDU connection parameters` until an address is filled in.

Some configs name further files. The `hsfei/xeryon` instances each point at
their controller's settings file, which the Xeryon Windows interface generates
and the daemon reads for unit conversion and travel limits. Those ship with the
driver at a path relative to the installed `hispec` package, so there is
nothing extra to deploy and nothing that depends on the unit's working
directory.

### The keyword archiver

`hispec_keygrabber` is the one instance that reads the other daemons rather
than any hardware, writing their keywords to InfluxDB for Grafana. It needs two
things the others do not: an optional dependency
(`/opt/hispec/venv/bin/pip install 'libby[influxdb]'`, run by an admin) and an
InfluxDB token in `/etc/hispec/secrets.env`.

It owns no hardware and can be restarted freely. Pausing it does not need a
restart at all:

```bash
libby modify hispec.keygrabber.enabled=false     # stop collecting, stay up
libby show   hispec.keygrabber.%                 # counters and health
libby show   hispec.keygrabber.%.%               # per-collection cadence
libby modify hispec.keygrabber.reload=1          # re-read the config file
```

## Host setup (admins)

This section is for whoever administers the host (IT / systems). It needs root.
Operators never need it to add, start or deploy daemons.

```bash
sudo git clone <repo-url> /opt/hispec/app
cd /opt/hispec/app && sudo git submodule update --init --recursive
sudo ./systemd/install.sh alice bob          # operator usernames
```

`install.sh` is idempotent. Re-run it:

- to enrol more operators (`sudo ./systemd/install.sh carol`);
- after a pull that changed dependencies in `pyproject.toml`, or
  `hispec@.service`, the polkit rule or `hispec-enable` under `systemd/`;
- to repair a host `hispec doctor` says is broken.

You do **not** need it to add a daemon or to pick up code changes;
[`hispec deploy`](#deploying-an-instance) and a `git pull` cover those. It:

- creates the `hispec-ops` group and the unprivileged `hispec` system user the
  daemons run as;
- adds each named operator to `hispec-ops` and `systemd-journal`;
- creates `/etc/hispec/{,instances/}` and `/var/log/hispec/`, group-owned by
  `hispec-ops` and setgid so files created by one operator stay readable by the
  rest;
- creates `/etc/hispec/secrets.env`, writable by `hispec-ops`;
- creates the venv at `/opt/hispec/venv` with the repo `pip install -e`'d into
  it, which also provides the `hispec` CLI;
- installs `hispec@.service` (then runs `daemon-reload`), the polkit rule, the
  sudoers drop-in, `/usr/local/bin/hispec` and `/usr/local/sbin/hispec-enable`;
- removes the retired `hispec-fei-start`, `hispec-fei-stop` and `hispec-doctor`
  scripts (now `hispec start fei`, `hispec stop fei` and `hispec doctor`);
- migrates any instance still running under the old `hispec-daemon@` name,
  preserving whether it was enabled and whether it was up;
- lists instances that are deployed but not set to start at boot.

`HISPEC_REPO_DIR` and `HISPEC_VENV_DIR` override the paths.

`/usr/local/bin/hispec` is a tiny wrapper that runs the CLI from the venv. The
commands come from `instrumentctl`; what stays here is
`src/hispec/cli/instrument.toml` and a few lines that pass it. Both are an
editable install, so `git pull` changes HISPEC's own configuration without a
reinstall, while updating the commands themselves means reinstalling the
dependency.

### What the unit does

`hispec@.service` runs the daemon as the unprivileged `hispec` user with
`NoNewPrivileges`, `ProtectSystem=full`, `ProtectHome` and `PrivateTmp`. It
restarts on failure with a 5 s delay, giving up after 5 failures in 60 s. The
working directory is `/var/log/hispec` because some drivers write a log file
next to it and the repo checkout is not writable by `hispec`. Loosen
`ProtectSystem` / `ProtectHome` if a driver needs to write outside `/etc/hispec`
and `/var/log/hispec`; device nodes under `/dev` are unaffected by both.

### Why `enable` is a helper and not just systemctl

Starting and stopping a unit is the polkit action
`org.freedesktop.systemd1.manage-units`, and systemd tells polkit which unit is
involved, so `systemd/polkit/49-hispec.rules` can allow it for `hispec@*` and
nothing else. Enabling and disabling is
`org.freedesktop.systemd1.manage-unit-files`, and systemd does **not** pass a
unit name with it. A polkit rule for it would grant `hispec-ops` enable/disable
on every unit on the host, which is too much.

So enable/disable goes through `/usr/local/sbin/hispec-enable` instead, a root
helper with a `NOPASSWD` sudoers entry scoped to that one path; `hispec enable`
and `hispec deploy` call it with `sudo -n`. The helper validates the instance
name against `^[a-z][a-z0-9_]*$` and requires a deployed instance file before
it will touch anything, which is the scoping polkit could not express.

The helper is a separate root-owned script rather than part of the `hispec`
CLI on purpose. The CLI runs from the venv, which the `hispec` user can write
to; if root ran it, anyone who could change the venv or the checkout would
have root.

The polkit `.rules` format needs polkit 0.106 or newer (Ubuntu 22.04 and
later). On an older host it is ignored silently, with no error, and operators
just get an auth prompt.
