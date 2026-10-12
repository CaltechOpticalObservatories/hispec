# systemd

Everything needed to run the HISPEC daemons as systemd services.

**Usage, deployment and troubleshooting are documented at
[Running the HISPEC Daemons with systemd][ops].** That page is the one to read
and the one to send people to; this file only describes what is in this
directory.

[ops]: https://caltechopticalobservatories.github.io/hispec/operations/systemd.html

| Path | What it is |
| --- | --- |
| `instances/<name>.env` | Per-instance settings: `HISPEC_DAEMON` (script, relative to `daemons/`) and `HISPEC_CONFIG` (deployed config path). Deployed to `/etc/hispec/instances/`. |
| `install.sh` | Host setup for admins / IT. Bootstraps uv, builds the venv, then hands over to `hispec install`. Idempotent, run as root. Not needed to add a daemon. |

`hispec install` writes the rest, rendered from
`src/hispec/cli/instrument.toml`:

| Installed | What it is |
| --- | --- |
| `/etc/systemd/system/hispec@.service` | The template unit. One file runs every daemon; `hispec@<name>` is an instance of it. |
| `/etc/polkit-1/rules.d/49-hispec.rules` | Lets `hispec-ops` members start/stop/restart `hispec@*` without sudo. |
| `/usr/local/bin/hispec` | Wrapper that runs the CLI from the venv. |
| `/usr/local/sbin/hispec-enable` | Root helper behind `hispec enable` / `hispec deploy`: enables/disables instances at boot, which `systemctl enable` cannot be granted per-unit. Invoked via `sudo -n` by a NOPASSWD drop-in. |
| `/etc/sudoers.d/hispec-ops` | That drop-in. |

The templates live in
[instrumentctl](https://github.com/CaltechOpticalObservatories/instrumentctl),
so a change to the unit or the polkit rule is made there and reaches a host
through `install.sh`. `hispec doctor` compares what is installed against what
`install` would write now.

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
