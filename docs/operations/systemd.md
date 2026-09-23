# Running the HISPEC Daemons with systemd

Every HISPEC hardware daemon on an instrument host runs as a systemd service.
This page is what you need to start, stop, watch and debug them. It assumes no
prior systemd knowledge.

If you only want the commands, jump to [Everyday commands](#everyday-commands).
If something is broken, jump to [Troubleshooting](#troubleshooting).

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
`enable` once, when an instance is first deployed and should survive reboots.

## Everyday commands

None of these need `sudo`, as long as you are in the `hispec-ops` group. If you
are being asked for a password, see
[systemctl keeps asking for a password](#systemctl-keeps-asking-for-a-password).

```bash
systemctl status  hispec@hsfei_adc     # is it up? what was the last log line?
systemctl start   hispec@hsfei_adc     # start it
systemctl stop    hispec@hsfei_adc     # stop it
systemctl restart hispec@hsfei_adc     # stop then start, e.g. after a config edit

journalctl -u hispec@hsfei_adc -f      # follow the log live (Ctrl-C to quit)
journalctl -u hispec@hsfei_adc -n 100  # the last 100 lines
journalctl -u hispec@hsfei_adc --since "1 hour ago"
```

To see everything at once:

```bash
systemctl list-units 'hispec@*'            # all currently loaded instances
systemctl list-units 'hispec@*' --failed   # only the broken ones
systemctl list-unit-files 'hispec@*'       # which are set to start at boot
```

### Starting and stopping the FEI as a group

The FEI has a dozen daemons and you rarely want just one of them. Two scripts
wrap the whole subsystem:

```bash
hispec-fei-start                       # start every deployed hsfei_* daemon
hispec-fei-stop                        # stop them all, in reverse order
hispec-fei-start hsfei_adc hsfei_ms    # or name the ones you want
hispec-fei-start --dry-run             # print what it would do, do nothing
```

They work off whatever is deployed in `/etc/hispec/instances/`, so they stay
correct as instances are added without anyone editing the scripts. Instances
that are already in the desired state are skipped rather than restarted, and
both scripts exit non-zero (after trying every instance) if any of them
failed, so they are safe to use from another script.

There is no equivalent for `hscal` yet; the same scripts will do it with
`HISPEC_PREFIX=hscal_ hispec-fei-start`, which is a stopgap rather than a
feature.

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
journalctl -u hispec@hsfei_adc -f              # live
journalctl -u hispec@hsfei_adc -p err          # errors only
journalctl -u 'hispec@*' --since today         # every HISPEC daemon at once
```

If a daemon's YAML config sets `logging.file`, that daemon writes to a file
under `/var/log/hispec/` instead, and the journal will be nearly empty for it.

Reading other users' journal entries requires being in the `systemd-journal`
group. If `journalctl -u hispec@...` prints nothing at all for a daemon you can
see running, that is the reason. Run `hispec-doctor`.

## Deploying an instance

Two files, then one enable. The first two steps need no `sudo`:

```bash
# 1. the config, with real hardware values filled in
cp /opt/hispec/app/config/hsfei/hsfei_atcpress.yaml /etc/hispec/hsfei_atcpress.yaml

# 2. the instance file that points the template at that config
cp /opt/hispec/app/systemd/instances/hsfei_atcpress.env \
   /etc/hispec/instances/hsfei_atcpress.env

# 3. start it now and at every boot
hispec-enable --now hsfei_atcpress
```

`hispec-enable` is a small helper that exists because `systemctl enable` cannot
be granted per-unit (see [the note on
enable/disable](#why-enable-is-a-helper-and-not-just-systemctl)). It refuses
any name that does not already have an instance file deployed.

```bash
hispec-enable hsfei_adc hsfei_ms     # add to the boot set, don't start now
hispec-enable --now hsfei_adc        # add to the boot set and start
hispec-enable --disable hsfei_adc    # remove from the boot set, leave it running
```

Stopping and disabling are independent: `systemctl stop` takes a daemon down
until you start it again or the host reboots; `hispec-enable --disable` keeps
it from coming back at boot.

### Adding a daemon that has no instance file yet

Add the config under `config/<subsystem>/` in the repo, write the matching
`systemd/instances/<name>.env`:

```sh
HISPEC_DAEMON=<path relative to daemons/, e.g. generic/inficon or hsfei/adc>
HISPEC_CONFIG=/etc/hispec/<name>.yaml
```

commit both, then deploy them as above. Also add the row to the table in
[Deployed instances](#deployed-instances) and to the inventory in
{doc}`../architecture/daemons`.

### Secrets

`/etc/hispec/instances/*.env` is readable by every `hispec-ops` member, which
is right for configs and wrong for a credential. Every unit also reads
`/etc/hispec/secrets.env` if it exists, which is root-only (0600), so a secret
goes there:

```bash
sudo tee -a /etc/hispec/secrets.env <<'EOF'
HISPEC_INFLUX_TOKEN=<InfluxDB write token>
EOF
systemctl restart hispec@hispec_keygrabber
```

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

## Troubleshooting

Start here:

```bash
hispec-doctor
```

It checks your group membership, the installed unit and polkit rule, the
directories, and every deployed instance, and prints the exact command to fix
whatever it finds. Run it as yourself, not under `sudo`, which would hide the
permission problems it is looking for.

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
2. **You ran `enable`, not `start`.** `systemctl enable` and `disable` need a
   different permission that polkit cannot restrict to one unit, so they always
   prompt. Use `hispec-enable` instead, which does not.
3. **The polkit rule is not installed**, or is the pre-rename copy that still
   matches `hispec-daemon@`. `hispec-doctor` reports both; the fix is for an
   admin to re-run `install.sh`.
4. **The host's polkit is older than 0.106.** JavaScript `.rules` files are
   ignored silently by older versions: no error, just a prompt every time.
   `hispec-doctor` checks the version.

You should never need `sudo` to start, stop, restart or look at a HISPEC
daemon. If you do, something in the list above is wrong; please fix it rather
than working around it with `sudo`, because a daemon started as root writes
root-owned log files that then break the next non-root start.

### The daemon will not start

```bash
systemctl status hispec@<name>
journalctl -u hispec@<name> -n 50
```

Common causes, in the order they bite:

- **`Failed to load environment files`**: `/etc/hispec/instances/<name>.env`
  is missing or unreadable. The instance name in the command must match the
  file name exactly.
- **`No such file or directory`** on the config: `HISPEC_CONFIG` points
  somewhere that does not exist. The config has to be deployed to `/etc/hispec/`
  separately from the `.env`; copying one and forgetting the other is the usual
  mistake.
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
journalctl -u hispec@<name> -n 200 --no-pager
```

After 5 failures in 60 seconds systemd stops retrying and leaves the unit
`failed`. Fix the cause, then:

```bash
systemctl reset-failed hispec@<name>
systemctl start hispec@<name>
```

### A config change has not taken effect

The config is read at startup. Edit `/etc/hispec/<name>.yaml`, then
`systemctl restart hispec@<name>`. Editing the copy in the repo under
`config/` changes nothing on a running host; the deployed copy under
`/etc/hispec/` is what the daemon reads.

### Picking up code changes

```bash
git -C /opt/hispec/app pull
systemctl restart hispec@<name>      # or hispec-fei-start after a stop
```

The venv install is editable, so a `pull` is enough unless dependencies
changed, in which case an admin re-runs `install.sh`. Pulling needs write
access to `/opt/hispec/app`, so either run as `hispec` or ask an admin.

## Deployed instances

| Instance | Daemon | Config |
| --- | --- | --- |
| `hscal_hkcalfwheel1` | `generic/filterwheel` | `config/hscal/hscal_hkcalfwheel1.yaml` |
| `hscal_hkcalfwheel2` | `generic/filterwheel` | `config/hscal/hscal_hkcalfwheel2.yaml` |
| `hscal_hkgcellfwheel` | `generic/filterwheel` | `config/hscal/hscal_hkgcellfwheel.yaml` |
| `hscal_yjcalfwheel1` | `generic/filterwheel` | `config/hscal/hscal_yjcalfwheel1.yaml` |
| `hscal_yjcalfwheel2` | `generic/filterwheel` | `config/hscal/hscal_yjcalfwheel2.yaml` |
| `hsfei_atcfw` | `generic/filterwheel` | `config/hsfei/hsfei_atcfw.yaml` |
| `hsfei_atcpress` | `generic/inficon` | `config/hsfei/hsfei_atcpress.yaml` |
| `hscal_gcellheater1` | `generic/lakeshore` | `config/hscal/hscal_gcellheater1.yaml` |
| `hscal_gcellheater2` | `generic/lakeshore` | `config/hscal/hscal_gcellheater2.yaml` |
| `hsfei_atctherm` | `generic/lakeshore` | `config/hsfei/hsfei_atctherm.yaml` |
| `hscal_hkettherm` | `generic/srsthermal` | `config/hscal/hscal_hkettherm.yaml` |
| `hscal_yjettherm` | `generic/srsthermal` | `config/hscal/hscal_yjettherm.yaml` |
| `hscal_hketatten` | `hscal/smc8_attenuator` | `config/hscal/hscal_hketatten.yaml` |
| `hsfei_adc` | `hsfei/adc` | `config/hsfei/hsfei_adc.yaml` |
| `hsfei_atccryo` | `hsfei/atccryo` | `config/hsfei/hsfei_atccryo.yaml` |
| `hsfei_atcl` | `hsfei/pi-daemon` | `config/hsfei/hsfei_atcl.yaml` |
| `hsfei_atcp` | `hsfei/pi-daemon` | `config/hsfei/hsfei_atcp.yaml` |
| `hsfei_feipo` | `hsfei/pi-daemon` | `config/hsfei/hsfei_feipo.yaml` |
| `hsfei_lsm` | `hsfei/pi-daemon` | `config/hsfei/hsfei_lsm.yaml` |
| `hsfei_ms` | `hsfei/pi-daemon` | `config/hsfei/hsfei_ms.yaml` |
| `hsfei_piaagimb` | `hsfei/piaa-gimbalmount` | `config/hsfei/hsfei_piaagimb.yaml` |
| `hsfei_piaagimr` | `hsfei/piaa-gimbalmount` | `config/hsfei/hsfei_piaagimr.yaml` |
| `hsfei_hkfam` | `hsfei/xeryon` | `config/hsfei/hsfei_hkfam.yaml` |
| `hsfei_piaadeploy` | `hsfei/xeryon` | `config/hsfei/hsfei_piaadeploy.yaml` |
| `hsfei_yjfam` | `hsfei/xeryon` | `config/hsfei/hsfei_yjfam.yaml` |
| `hispec_keygrabber` | `generic/keygrabber` | `config/hispec/hispec_keygrabber.yaml` |
| `hspower_fei1` | `hspower/pdu` | `config/hspower/hspower_fei1.yaml` |
| `hspower_fei2` | `hspower/pdu` | `config/hspower/hspower_fei2.yaml` |
| `hspower_cal1` | `hspower/pdu` | `config/hspower/hspower_cal1.yaml` |
| `hspower_cal2` | `hspower/pdu` | `config/hspower/hspower_cal2.yaml` |
| `hspower_cal3` | `hspower/pdu` | `config/hspower/hspower_cal3.yaml` |
| `hspower_cal4` | `hspower/pdu` | `config/hspower/hspower_cal4.yaml` |
| `hspower_fib1` | `hspower/pdu` | `config/hspower/hspower_fib1.yaml` |
| `hspower_bspec1` | `hspower/pdu` | `config/hspower/hspower_bspec1.yaml` |
| `hspower_rspec1` | `hspower/pdu` | `config/hspower/hspower_rspec1.yaml` |

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

```bash
sudo git clone <repo-url> /opt/hispec/app
cd /opt/hispec/app && sudo git submodule update --init --recursive
sudo ./systemd/install.sh alice bob          # operator usernames
```

`install.sh` is idempotent. Re-run it after a repo update, to enrol more
operators, or to repair a host. It:

- creates the `hispec-ops` group and the unprivileged `hispec` system user the
  daemons run as;
- adds each named operator to `hispec-ops` and `systemd-journal`;
- creates `/etc/hispec/{,instances/}` and `/var/log/hispec/`, group-owned by
  `hispec-ops` and setgid so files created by one operator stay readable by the
  rest;
- creates a root-only `/etc/hispec/secrets.env`;
- creates the venv at `/opt/hispec/venv` with the repo `pip install -e`'d into
  it;
- installs `hispec@.service`, the polkit rule, the sudoers drop-in, and the
  `hispec-fei-start` / `hispec-fei-stop` / `hispec-doctor` / `hispec-enable`
  commands;
- migrates any instance still running under the old `hispec-daemon@` name,
  preserving whether it was enabled and whether it was up;
- lists instances that are deployed but not set to start at boot.

`HISPEC_REPO_DIR` and `HISPEC_VENV_DIR` override the paths.

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
helper with a `NOPASSWD` sudoers entry scoped to that one path. The helper
validates the instance name against `^[a-z][a-z0-9_]*$` and requires a deployed
instance file before it will touch anything, which is the scoping polkit could
not express.

The polkit `.rules` format needs polkit 0.106 or newer (Ubuntu 22.04 and
later). On an older host it is ignored silently, with no error, and operators
just get an auth prompt.
