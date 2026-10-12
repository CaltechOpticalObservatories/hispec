#!/usr/bin/env bash
# Host setup for running the hispec daemons under systemd. For admins / IT.
# Run as root. Safe to re-run: it converges the host onto the current repo.
#
#   sudo ./systemd/install.sh                    # set the host up
#   sudo ./systemd/install.sh alice bob          # ... and enrol two operators
#   sudo HISPEC_OPS_USERS="alice bob" ./systemd/install.sh   # same thing
#
# Re-run it to enrol operators, after a dependency change, or to repair a host.
# It is NOT part of adding a daemon: once a host is set up, operators do that
# themselves with `hispec deploy <name>`, no root needed.
#
# Operators named here are added to hispec-ops and systemd-journal, which is
# what lets them start/stop/restart daemons and read logs without a password.
# Skipping that step is the single most common reason systemctl keeps
# prompting. See docs/operations/systemd.md.
#
# Everything past the virtualenv is `hispec install`, which lives in
# instrumentctl and is shared with other instruments.

set -euo pipefail

REPO_DIR="${HISPEC_REPO_DIR:-/opt/hispec/app}"
VENV_DIR="${HISPEC_VENV_DIR:-/opt/hispec/venv}"
OPS_USERS="${HISPEC_OPS_USERS:-} $*"
UV_VERSION="${HISPEC_UV_VERSION:-0.12.23}"
# Its own copy rather than whatever uv is on PATH, since a snap refreshes
# itself and would unpin the resolver
UV_BIN=/usr/local/bin/uv

# Keeps uv out of .venv and on the path every unit already references
export UV_PROJECT_ENVIRONMENT="$VENV_DIR"

# The daemons run as `hispec`, and this script runs as root, so a uv-managed
# interpreter would land under root's home where they could not read it. Use
# the system Python.
export UV_NO_MANAGED_PYTHON=1

if [[ $EUID -ne 0 ]]; then
    echo "Run as root (sudo)." >&2
    exit 1
fi

if [[ ! -d "$REPO_DIR" ]]; then
    echo "error: REPO_DIR $REPO_DIR does not exist." >&2
    echo "Clone the hispec repo there first, e.g.:" >&2
    echo "  git clone <repo-url> $REPO_DIR" >&2
    echo "  cd $REPO_DIR && git submodule update --init --recursive" >&2
    exit 1
fi

# Pinned, so re-running the installer cannot resolve with a different uv
if [[ "$("$UV_BIN" --version 2>/dev/null)" != "uv $UV_VERSION"* ]]; then
    curl -LsSf "https://astral.sh/uv/$UV_VERSION/install.sh" |
        env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh
    echo "installed uv $UV_VERSION at $UV_BIN"
fi

# The virtualenv has to exist before the rest, since `hispec install` lives in
# it. Upgrade the lock first: the git dependencies track their default branch
# deliberately, and a reinstall is how a merged libby fix reaches a host.
(
    cd "$REPO_DIR"
    "$UV_BIN" lock --upgrade
    # --all-packages installs the vendored drivers too; plain sync covers only
    # the root project and leaves their dependencies out
    "$UV_BIN" sync --all-packages
)

# shellcheck disable=SC2086  # OPS_USERS is a deliberately word-split list
exec "$VENV_DIR/bin/hispec" install $OPS_USERS
