# systemd

Everything needed to run the HISPEC daemons as systemd services.

**Usage, deployment and troubleshooting are documented at
[Running the HISPEC Daemons with systemd][ops].** That page is the one to read
and the one to send people to; this file only describes what is in this
directory.

[ops]: https://caltechopticalobservatories.github.io/hispec/operations/systemd.html

| Path | What it is |
| --- | --- |
| `hispec@.service` | The template unit. One file runs every daemon; `hispec@<name>` is an instance of it. Installed to `/etc/systemd/system/`. |
| `instances/<name>.env` | Per-instance settings: `HISPEC_DAEMON` (script, relative to `daemons/`) and `HISPEC_CONFIG` (deployed config path). Deployed to `/etc/hispec/instances/`. |
| `polkit/49-hispec.rules` | Lets `hispec-ops` members start/stop/restart `hispec@*` without sudo. Installed to `/etc/polkit-1/rules.d/`. |
| `bin/hispec-fei-start` | Start every deployed `hsfei_*` daemon. Installed to `/usr/local/bin/`. |
| `bin/hispec-fei-stop` | Stop them, in reverse order. Installed to `/usr/local/bin/`. |
| `bin/hispec-doctor` | Diagnose a host or an account. Run this first when something does not work. Installed to `/usr/local/bin/`. |
| `bin/hispec-enable` | Enable/disable instances at boot without a password prompt, which `systemctl enable` cannot be granted per-unit. Installed to `/usr/local/sbin/`, invoked via `sudo` by a NOPASSWD drop-in. |
| `install.sh` | Idempotent host setup: users, groups, directories, venv, and all of the above. Run as root. |

## Quick reference

```bash
sudo ./systemd/install.sh alice bob   # host setup, enrolling two operators

systemctl start hispec@hsfei_adc      # no sudo, once you are in hispec-ops
journalctl -u hispec@hsfei_adc -f
hispec-fei-start                      # the whole FEI subsystem
hispec-doctor                         # why isn't it working?
```

Each of `bin/*` also responds to `--help`.

## Adding an instance

1. Add the config at `config/<subsystem>/<name>.yaml`.
2. Add `instances/<name>.env` naming the daemon script and the deployed config
   path.
3. Add the row to the instance table in [the operations page][ops] and to the
   inventory in `docs/architecture/daemons.md`.

Running two of the same hardware model (two Lakeshores, five filter wheels) is
two `.env` files pointing at the same script with different configs, not new
code.
