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
| `bin/hispec` | Wrapper that runs the `hispec` CLI from the venv. Installed to `/usr/local/bin/`. |
| `bin/hispec-enable` | Root helper behind `hispec enable` / `hispec deploy`: enables/disables instances at boot, which `systemctl enable` cannot be granted per-unit. Installed to `/usr/local/sbin/`, invoked via `sudo -n` by a NOPASSWD drop-in. |
| `install.sh` | Host setup for admins / IT: users, groups, directories, venv, and all of the above. Idempotent, run as root. Not needed to add a daemon. |

## Quick reference

```bash
sudo ./systemd/install.sh alice bob   # admin, once per host: setup + two operators

# operators, no sudo, once in hispec-ops:
hispec deploy hsfei_adc               # copy files from the repo, enable, start
hispec deploy --new                   # everything the repo has that this host doesn't
hispec status
hispec start hsfei                    # the whole FEI subsystem
hispec logs hsfei_adc -f
hispec doctor                         # why isn't it working?
```

`hispec --help` lists every subcommand, and each takes `--help`.

## Adding an instance

1. Add the config at `config/<subsystem>/<name>.yaml`.
2. Add `instances/<name>.env` naming the daemon script and the deployed config
   path.
3. Add the row to the instance table in [the operations page][ops] and to the
   inventory in `docs/architecture/daemons.md`.
4. Commit; on the host, `git pull` then `hispec deploy <name>`. No `install.sh`
   and no `daemon-reload`.

Running two of the same hardware model (two Lakeshores, five filter wheels) is
two `.env` files pointing at the same script with different configs, not new
code.
