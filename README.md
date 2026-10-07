# hispec

HISPEC Instrument Control Software

## Documentation

Architecture, build notes and deployment references are published at
**<https://caltechopticalobservatories.github.io/hispec/>**.

Start with the [architecture overview][arch] for how the system fits together,
or the [daemon inventory][inventory] to find a specific mechanism.

If you are running the instrument, see [running the daemons with
systemd][systemd-ops].

[arch]: https://caltechopticalobservatories.github.io/hispec/architecture/overview.html
[inventory]: https://caltechopticalobservatories.github.io/hispec/architecture/daemons.html
[systemd-ops]: https://caltechopticalobservatories.github.io/hispec/operations/systemd.html

## Structure

| Path | Contents |
| --- | --- |
| `daemons/` | Deployable device daemons. `generic/` are config-driven and shared across subsystems; `hsfei/`, `hscal/` are subsystem-specific. `generic/keygrabber` is the exception that drives no hardware: it records the other daemons' keywords into InfluxDB for Grafana. |
| `config/` | One YAML file per deployed daemon instance, organised by subsystem. |
| `src/hispec/` | Installable package: the `HispecDaemon` base class and the `driver/` submodules. |
| `systemd/` | Template unit, per-instance env files, operator commands and installer. See [Running the daemons with systemd][systemd-ops]. |
| `docs/` | Sphinx documentation sources. |
| `tests/` | Driver unit tests. |
| `etc/` | Vendored externals: `camera-interface`, `PIPython`. |
| `scripts/` | Engineering and performance-analysis scripts. |

`Makefile`, `Mk.instrument`, `init.d/`, `qt/` and `daemons/hs{owenv,dewar,power,ssd}/`
are from the original KROOT/KTL build and are no longer used; see
[Architecture Evolution][evolution].

[evolution]: https://caltechopticalobservatories.github.io/hispec/architecture/evolution.html

## Quick start

```bash
# 1) Clone
git clone <repo-url>
cd hispec

# 2) Make sure submodule URLs are in sync and check out pinned SHAs (includes nested)
git submodule sync --recursive
git submodule update --init --recursive

# 3) Create the environment and install, editable
uv sync --all-packages
```

That builds `.venv` on the Python named in `.python-version` and installs this
package plus every vendor driver editable, so a `git pull` changes behaviour
without reinstalling. Run commands through `uv run <command>`, or activate
`.venv` if you prefer.

`--all-packages` matters: the drivers under `src/hispec/driver/` are uv
workspace members, and a plain `uv sync` installs only this package's own
dependencies, leaving theirs out.

`uv.lock` is not committed while the git dependencies deliberately track their
default branches. It still records which commit of libby, bamboo and the rest
your checkout resolved to, which is how to tell what you are running. `uv sync`
reuses that lock once it exists, so pick up a merged dependency change with:

```bash
uv lock --upgrade && uv sync --all-packages
```

## Submodules

Every vendor driver is a git submodule under `src/hispec/driver/`, sourced from
the [COO-Utilities](https://github.com/COO-Utilities) organisation. A checkout
without `--recursive` builds a package missing every `hispec.driver.*` module,
so always initialise them.

### Pull the submodules

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

### Update to the latest on a tracked branch (e.g., `main`)

> Only do this if you **intend** to move submodule pointers and commit them.

```bash
# Option A: one-off refresh to submodules’ tracked branches
git submodule update --remote --merge --recursive

# Record updated pointers in parent repo
git add .gitmodules .
git commit -m "Update submodules to latest on main"
```

## Testing
Unit tests are located in `*/tests/` directories.

To run all tests from the project root:

```bash
pytest
```

## Contributing

1. Create a feature branch.
2. Include tests for new behavior.
3. Run `pytest` before opening a PR.
