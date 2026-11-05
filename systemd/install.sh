#!/usr/bin/env bash
# Host setup for running the hispec daemons under systemd. For admins / IT.
# Run as root. Safe to re-run.
#
#   sudo ./systemd/install.sh                    # set the host up
#   sudo ./systemd/install.sh alice bob          # ... and enrol two operators
#   sudo HISPEC_OPS_USERS="alice bob" ./systemd/install.sh   # same thing
#   sudo ./systemd/install.sh --extra scripts    # ... with an optional extra
#
# It installs /opt/hispec/app as it is, edits included, and never changes it:
# pulling is up to whoever runs it. The venv is synced from the checkout's
# uv.lock, so every git dependency is the exact commit the lock records.
#
# Extras are recorded in /etc/hispec/extras, and every later run syncs them
# again. Some follow the host role: feiserver always gets atcam, the tracking
# camera module, which any other role is refused; feiserver and hispecserver
# always get atlas, the viewer.
#
# A clone in /opt/hispec/extra/ replaces the GitHub build of its extra, for
# changing that code on this host; see docs/install.md. Remove the clone and
# re-run to go back.
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
HOST_FILE="${HISPEC_ETC_DIR:-/etc/hispec}/host"
CAMERA_EXTRA=atcam
CAMERA_ROLE=feiserver
VIEWER_EXTRA=atlas
VIEWER_ROLES=(feiserver hispecserver)
EXTRA_DIR="${HISPEC_EXTRA_DIR:-/opt/hispec/extra}"
INSTRUMENT_SRC="$EXTRA_DIR/hispec-tracking-camera-instrument"
CORE_SRC="$EXTRA_DIR/camera-interface"
VIEWER_SRC="$EXTRA_DIR/atlas"
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
ROLE_ARG=""
while (($#)); do
    case $1 in
        --extra) EXTRAS+=("$2"); shift 2 ;;
        --host-role) ROLE_ARG=$2; INSTALL_ARGS+=("$1" "$2"); shift 2 ;;
        --host-role=*) ROLE_ARG=${1#*=}; INSTALL_ARGS+=("$1"); shift ;;
        *) INSTALL_ARGS+=("$1"); shift ;;
    esac
done

# Same precedence as `hispec install`, which never overwrites a recorded role
ROLE=""
if [[ -f "$HOST_FILE" ]]; then
    ROLE=$(tr -d '[:space:]' <"$HOST_FILE")
fi
ROLE=${ROLE:-${ROLE_ARG:-$(hostname -s)}}

if [[ $ROLE == "$CAMERA_ROLE" ]]; then
    EXTRAS+=("$CAMERA_EXTRA")
elif printf '%s\n' "${EXTRAS[@]}" | grep -qx "$CAMERA_EXTRA"; then
    echo "error: the $CAMERA_EXTRA extra is for $CAMERA_ROLE only; this host is '$ROLE'." >&2
    echo "Drop --extra $CAMERA_EXTRA, or remove it from $EXTRAS_FILE." >&2
    exit 1
fi
if printf '%s\n' "${VIEWER_ROLES[@]}" | grep -qx "$ROLE"; then
    EXTRAS+=("$VIEWER_EXTRA")
fi

has_extra() {
    printf '%s\n' "${EXTRAS[@]}" | grep -qx "$1"
}

# A clone only replaces an extra this host installs; checked before syncing
for source in "$INSTRUMENT_SRC:$CAMERA_EXTRA" "$CORE_SRC:$CAMERA_EXTRA" "$VIEWER_SRC:$VIEWER_EXTRA"; do
    if [[ -d ${source%:*} ]] && ! has_extra "${source#*:}"; then
        echo "error: ${source%:*} is for the ${source#*:} extra, which this host ('$ROLE') does not install." >&2
        exit 1
    fi
done
if [[ -d $CORE_SRC && ! -d $INSTRUMENT_SRC ]]; then
    echo "error: $CORE_SRC is only built through $INSTRUMENT_SRC, which is missing." >&2
    exit 1
fi

if ((${#EXTRAS[@]})); then
    mapfile -t EXTRAS < <(printf '%s\n' "${EXTRAS[@]}" | sort -u)
fi
EXTRA_FLAGS=()
for extra in "${EXTRAS[@]}"; do
    EXTRA_FLAGS+=(--extra "$extra")
done

# Syncing the lock reaches the private camera repo
if [[ -f "$DEPLOY_KEY" ]]; then
    export GIT_SSH_COMMAND="ssh -i $DEPLOY_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
fi

CHECKOUT_DESC=$(git -C "$REPO_DIR" symbolic-ref --short -q HEAD ||
    git -C "$REPO_DIR" rev-parse --short HEAD)
if [[ -n $(git -C "$REPO_DIR" status --porcelain --untracked-files=no) ]]; then
    CHECKOUT_DESC+=", modified"
fi
echo "installing $REPO_DIR ($CHECKOUT_DESC) as it is; pulling is up to you"

# Pinned, so re-running the installer cannot resolve with a different uv
if [[ "$("$UV_BIN" --version 2>/dev/null)" != "uv $UV_VERSION"* ]]; then
    curl -LsSf "https://astral.sh/uv/$UV_VERSION/install.sh" |
        env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh
    echo "installed uv $UV_VERSION at $UV_BIN"
fi

# The virtualenv has to exist before the rest, since `hispec install` lives in
# it. --locked installs exactly the committed lock, and fails rather than
# re-resolving if the lock no longer matches pyproject.toml.
(
    cd "$REPO_DIR"
    # --all-packages installs the vendored drivers too; plain sync covers only
    # the root project and leaves their dependencies out
    "$UV_BIN" sync --locked --all-packages "${EXTRA_FLAGS[@]}"
)

# Local clones go in after the sync, which installs every extra from GitHub
LOCAL_FLAGS=(--python "$VENV_DIR/bin/python" --no-deps --reinstall --no-cache)
if [[ -d $INSTRUMENT_SRC ]]; then
    CORE_FLAGS=()
    if [[ -d $CORE_SRC ]]; then
        CORE_FLAGS=(-C "cmake.define.FETCHCONTENT_SOURCE_DIR_CAMERA_INTERFACE=$CORE_SRC")
    fi
    "$UV_BIN" pip install "${LOCAL_FLAGS[@]}" "${CORE_FLAGS[@]}" "$INSTRUMENT_SRC"
    echo "local source: $INSTRUMENT_SRC${CORE_FLAGS:+, against $CORE_SRC}"
fi
if [[ -d $VIEWER_SRC ]]; then
    # Editable, so a Python edit takes effect the next time atlas starts
    "$UV_BIN" pip install "${LOCAL_FLAGS[@]}" --editable "$VIEWER_SRC"
    echo "local source: $VIEWER_SRC"
fi

# Only once the sync accepted them, so a mistyped extra is not kept
if ((${#EXTRAS[@]})); then
    mkdir -p "$(dirname "$EXTRAS_FILE")"
    printf '%s\n' "${EXTRAS[@]}" >"$EXTRAS_FILE"
fi
exec "$VENV_DIR/bin/hispec" install "${INSTALL_ARGS[@]}"
