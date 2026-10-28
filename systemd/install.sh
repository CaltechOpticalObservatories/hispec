#!/usr/bin/env bash
# Host setup for running the hispec daemons under systemd. For admins / IT.
# Run as root. Safe to re-run: it converges the host onto the current repo.
#
#   sudo ./systemd/install.sh                    # set the host up
#   sudo ./systemd/install.sh alice bob          # ... and enrol two operators
#   sudo HISPEC_OPS_USERS="alice bob" ./systemd/install.sh   # same thing
#   sudo ./systemd/install.sh --extra atcam      # ... with the tracking camera
#
# Extras are recorded in /etc/hispec/extras, and every later run syncs them
# again, so a plain re-run keeps a camera host's camera module.
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
EXTRAS_FILE="${HISPEC_ETC_DIR:-/etc/hispec}/extras"
DEPLOY_KEY="${HISPEC_ETC_DIR:-/etc/hispec}/deploy-key"
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

# --extra is ours; everything else goes to `hispec install`
read -ra INSTALL_ARGS <<<"${HISPEC_OPS_USERS:-}"
EXTRAS=()
if [[ -f "$EXTRAS_FILE" ]]; then
    mapfile -t EXTRAS <"$EXTRAS_FILE"
fi
while (($#)); do
    case $1 in
        --extra) EXTRAS+=("$2"); shift 2 ;;
        *) INSTALL_ARGS+=("$1"); shift ;;
    esac
done
if ((${#EXTRAS[@]})); then
    mapfile -t EXTRAS < <(printf '%s\n' "${EXTRAS[@]}" | sort -u)
fi
EXTRA_FLAGS=()
for extra in "${EXTRAS[@]}"; do
    EXTRA_FLAGS+=(--extra "$extra")
done

# uv lock resolves every extra on every host, including the private camera repo
if [[ -f "$DEPLOY_KEY" ]]; then
    export GIT_SSH_COMMAND="ssh -i $DEPLOY_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
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
    "$UV_BIN" sync --all-packages "${EXTRA_FLAGS[@]}"
)

# Only once the sync accepted them, so a mistyped extra is not kept
if ((${#EXTRAS[@]})); then
    mkdir -p "$(dirname "$EXTRAS_FILE")"
    printf '%s\n' "${EXTRAS[@]}" >"$EXTRAS_FILE"
fi

exec "$VENV_DIR/bin/hispec" install "${INSTALL_ARGS[@]}"
