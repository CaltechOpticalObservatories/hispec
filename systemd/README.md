# Running daemons under systemd

One template unit, `hispec-daemon@.service`, runs any `daemons/**` script
that's a `HispecDaemon` subclass taking `-c <config.yaml>` and blocking in
`daemon.serve()` — the shared `daemons/generic/*` scripts (inficon,
lakeshore, filterwheel, ...) and the subsystem-specific ones
(`daemons/hsfei/*`, `daemons/hscal/*`).

Each running daemon is an instance, `hispec-daemon@<name>`, backed by an env
file at `/etc/hispec/instances/<name>.env`:

```sh
HISPEC_DAEMON=<path relative to daemons/, e.g. generic/inficon or hsfei/adc>
HISPEC_CONFIG=<absolute path to that instance's config.yaml>
```

## Setup

```bash
sudo git clone <repo-url> /opt/hispec/app
cd /opt/hispec/app && git submodule update --init --recursive
sudo ./systemd/install.sh
```

`install.sh` creates an unprivileged `hispec` user, a `hispec-ops` group,
`/etc/hispec/{,instances/}` and `/var/log/hispec/` (group-writable by
`hispec-ops`), a venv at `/opt/hispec/venv` with the repo `pip install -e`d
into it, installs `hispec-daemon@.service`, and installs a polkit rule
(`systemd/polkit/49-hispec-daemons.rules`) letting `hispec-ops` members
start/stop/restart `hispec-daemon@*` units without sudo. Override
`HISPEC_REPO_DIR` / `HISPEC_VENV_DIR` for different paths.

**No sudo day to day:** once an admin has run `install.sh` and added you —
`usermod -aG hispec-ops,systemd-journal <you>` (log out/in, or `newgrp
hispec-ops`, to pick it up) — you can create/edit files under `/etc/hispec/`
and control any `hispec-daemon@*` unit yourself. Only installing/updating
the unit file, the polkit rule, and `systemctl enable/disable` (which
changes boot behavior) still need an admin — see `install.sh`'s output.

## Deploying an instance

To bring one up (no sudo needed for these two once you're in `hispec-ops`):

```bash
cp config/hsfei/hsfei_atcpress.yaml /etc/hispec/hsfei_atcpress.yaml
cp systemd/instances/hsfei_atcpress.env /etc/hispec/instances/hsfei_atcpress.env
sudo systemctl enable --now hispec-daemon@hsfei_atcpress   # admin-only step
systemctl start hispec-daemon@hsfei_atcpress               # no sudo needed after that
```

For a new daemon/config not yet in the table, add its config under
`config/<subsystem>/`, write a matching `systemd/instances/<name>.env`
(`HISPEC_DAEMON=...`, `HISPEC_CONFIG=...`), deploy both the same way, then
have an admin `enable --now` it once. Running two instances of the same
daemon (e.g. two lakeshores) just means two env files with different
`HISPEC_CONFIG`s — see `hscal_gcellheater1`/`2` below.

| instance              | daemon                   | config                                  |
| --------------------- | ------------------------ | ---------------------------------------- |
| `hsfei_atcpress`      | `generic/inficon`        | `config/hsfei/hsfei_atcpress.yaml`      |
| `hsfei_atctherm`      | `generic/lakeshore`      | `config/hsfei/hsfei_atctherm.yaml`      |
| `hscal_gcellheater1`  | `generic/lakeshore`      | `config/hscal/hscal_gcellheater1.yaml`  |
| `hscal_gcellheater2`  | `generic/lakeshore`      | `config/hscal/hscal_gcellheater2.yaml`  |
| `hsfei_ATCFW`         | `generic/filterwheel`    | `config/hsfei/hsfei_ATCFW.yaml`         |
| `hscal_hkcalfwheel1`  | `generic/filterwheel`    | `config/hscal/hscal_hkcalfwheel1.yaml`  |
| `hscal_hkcalfwheel2`  | `generic/filterwheel`    | `config/hscal/hscal_hkcalfwheel2.yaml`  |
| `hscal_hkgcellfwheel` | `generic/filterwheel`    | `config/hscal/hscal_hkgcellfwheel.yaml` |
| `hscal_yjcalfwheel1`  | `generic/filterwheel`    | `config/hscal/hscal_yjcalfwheel1.yaml`  |
| `hscal_yjcalfwheel2`  | `generic/filterwheel`    | `config/hscal/hscal_yjcalfwheel2.yaml`  |
| `hsfei_adc`           | `hsfei/adc`              | `config/hsfei/hsfei_adc.yaml`           |
| `hsfei_atccryo`       | `hsfei/atccryo`          | `config/hsfei/hsfei_atccryo.yaml`       |
| `hsfei_atcpickoff`    | `hsfei/pi-daemon`        | `config/hsfei/hsfei_atcpickoff.yaml`    |
| `hsfei_focpupsel`     | `hsfei/pi-daemon`        | `config/hsfei/hsfei_focpupsel.yaml`     |
| `hsfei_msel`          | `hsfei/pi-daemon`        | `config/hsfei/hsfei_msel.yaml`          |
| `hsfei_pickoff`       | `hsfei/pi-daemon`        | `config/hsfei/hsfei_pickoff.yaml`       |
| `hsfei_rlight`        | `hsfei/pi-daemon`        | `config/hsfei/hsfei_rlight.yaml`        |
| `hsfei_PIAAgimb`      | `hsfei/piaa-gimbalmount` | `config/hsfei/hsfei_PIAAgimb.yaml`      |
| `hsfei_PIAAgimr`      | `hsfei/piaa-gimbalmount` | `config/hsfei/hsfei_PIAAgimr.yaml`      |
| `hscal_hketatten`     | `hscal/smc8_attenuator`  | `config/hscal/hscal_hketatten.yaml`     |

(`config/example/pdu.yaml` has no instance file yet — there's no
`daemons/generic/pdu` script to run it.)

## Day to day

No sudo needed for any of this once you're in `hispec-ops`:

```bash
systemctl status hispec-daemon@<name>
journalctl -u hispec-daemon@<name> -f
systemctl restart hispec-daemon@<name>
systemctl stop hispec-daemon@<name>
```

`systemctl disable --now hispec-daemon@<name>` (stop and don't start on
boot) still needs an admin, since polkit can't scope enable/disable to one
unit by name.

By default the daemon logs to stdout/stderr, which lands in the journal. If
a config sets `logging.file` instead, logs go there — `/var/log/hispec/` is
writable by `hispec` and readable by `hispec-ops`.

To pick up code changes: `git -C /opt/hispec/app pull` (needs write access
to `/opt/hispec/app`, so either run as `hispec` or have an admin do it),
then restart each running instance. The venv install is editable, so only
re-run `pip install` if dependencies changed.
