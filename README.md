# hispec

HISPEC Instrument Control Software

## Documentation

Architecture, build notes and deployment references are published at
**<https://caltechopticalobservatories.github.io/hispec/>**.

Start with the [architecture overview][arch] for how the system fits together,
or the [daemon inventory][inventory] to find a specific mechanism.

[arch]: https://caltechopticalobservatories.github.io/hispec/architecture/overview.html
[inventory]: https://caltechopticalobservatories.github.io/hispec/architecture/daemons.html

## Structure

| Path | Contents |
| --- | --- |
| `daemons/` | Deployable device daemons. `generic/` are config-driven and shared across subsystems; `hsfei/`, `hscal/` are subsystem-specific. |
| `config/` | One YAML file per deployed daemon instance, organised by subsystem. |
| `src/hispec/` | Installable package: the `HispecDaemon` base class and the `driver/` submodules. |
| `systemd/` | Template unit, per-instance env files and installer. See [systemd/README.md](systemd/README.md). |
| `docs/` | Sphinx documentation sources. |
| `tests/` | Driver unit tests. |
| `etc/` | Vendored externals: `camera-interface`, `PIPython`. |
| `scripts/` | Engineering and performance-analysis scripts. |

`Makefile`, `Mk.instrument`, `init.d/`, `qt/` and `daemons/hs{owenv,dewar,power,ssd}/`
are from the original KROOT/KTL build and are no longer used — see
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

# 3) (Recommended) Create a Python env
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 4) Install package(s) for development
pip install -U pip
pip install -e ".[dev]"    # falls back to requirements.txt if no pyproject
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
