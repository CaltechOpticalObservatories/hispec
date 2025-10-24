# hispec

HISPEC Instrument Control Software

## Structure
- Each mKTL service has a directory
- Additional directories include etc, qt, util, init.d

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

This repo uses nested submodules under `util/` and possibly within service directories.

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
