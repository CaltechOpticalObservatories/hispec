#!/usr/bin/env bash
# Host setup for running the hispec daemons under systemd. For admins / IT.
# Run as root. Safe to re-run: it converges the host onto the latest release.
#
#   sudo ./systemd/install.sh                    # set the host up
#   sudo ./systemd/install.sh alice bob          # ... and enrol two operators
#   sudo HISPEC_OPS_USERS="alice bob" ./systemd/install.sh   # same thing
#   sudo ./systemd/install.sh --extra scripts    # ... with an optional extra
#   sudo ./systemd/install.sh --ref main         # install a branch or tag instead
#   sudo ./systemd/install.sh --local            # install the checkout as it is
#
# A release is an annotated hispec-X.Y tag. The checkout moves to the newest
# one, and the venv is synced from that release's uv.lock, so every git
# dependency is the exact commit the release pinned.
#
# Extras are recorded in /etc/hispec/extras, and every later run syncs them
# again. Some follow the host role: feiserver always gets atcam, the tracking
# camera module, which any other role is refused; feiserver and hispecserver
# always get atlas, the viewer.
#
# --local leaves the hispec checkout to whoever develops on this host: no
# fetch, pull, checkout or submodule update, and edits are allowed. It installs
# whatever is checked out, dependencies from that checkout's uv.lock. It is
# recorded in /etc/hispec/source, so later runs stay local until one passes
# --ref. See docs/install.md.
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
ORIGINAL_ARGS=("$@")

REPO_DIR="${HISPEC_REPO_DIR:-/opt/hispec/app}"
VENV_DIR="${HISPEC_VENV_DIR:-/opt/hispec/venv}"
EXTRAS_FILE="${HISPEC_ETC_DIR:-/etc/hispec}/extras"
HOST_FILE="${HISPEC_ETC_DIR:-/etc/hispec}/host"
SOURCE_FILE="${HISPEC_ETC_DIR:-/etc/hispec}/source"
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
REF=""
LOCAL_ARG=""
while (($#)); do
    case $1 in
        --extra) EXTRAS+=("$2"); shift 2 ;;
        --local) LOCAL_ARG=1; shift ;;
        --ref) REF=$2; shift 2 ;;
        --ref=*) REF=${1#*=}; shift ;;
        --host-role) ROLE_ARG=$2; INSTALL_ARGS+=("$1" "$2"); shift 2 ;;
        --host-role=*) ROLE_ARG=${1#*=}; INSTALL_ARGS+=("$1"); shift ;;
        *) INSTALL_ARGS+=("$1"); shift ;;
    esac
done

# Local source: asked for now, or recorded by an earlier --local run. An
# explicit --ref goes back to installing releases.
if [[ -n ${HISPEC_LOCAL_SOURCE:-} ]]; then
    LOCAL_ARG=1
fi
if [[ -n $LOCAL_ARG && -n $REF ]]; then
    echo "error: --local installs the checkout as it is; it cannot be combined with --ref." >&2
    exit 1
fi
LOCAL=""
if [[ -n $LOCAL_ARG ]]; then
    LOCAL=1
elif [[ -z $REF && -f $SOURCE_FILE && $(tr -d '[:space:]' <"$SOURCE_FILE") == local ]]; then
    LOCAL=1
fi

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

# Fetching the release and syncing the lock reach the private camera repo
if [[ -f "$DEPLOY_KEY" ]]; then
    export GIT_SSH_COMMAND="ssh -i $DEPLOY_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
fi

if [[ -n $LOCAL ]]; then
    # The developer owns the checkout: no git command here changes it
    LOCAL_DESC=$(git -C "$REPO_DIR" symbolic-ref --short -q HEAD ||
        git -C "$REPO_DIR" rev-parse --short HEAD)
    if [[ -n $(git -C "$REPO_DIR" status --porcelain --untracked-files=no) ]]; then
        LOCAL_DESC+=", modified"
    fi
    echo "installing local checkout $REPO_DIR ($LOCAL_DESC); not pulling, that is up to you"
else
    # Refuse to move a checkout with edits in it: checking out the release would
    # carry them along or stop halfway. `hispec hotfix` saves them first.
    if [[ -n $(git -C "$REPO_DIR" status --porcelain --untracked-files=no) ]]; then
        echo "error: $REPO_DIR has uncommitted edits:" >&2
        git -C "$REPO_DIR" status --short --untracked-files=no >&2
        echo 'Save them with: hispec hotfix "what you fixed"   (or discard: hispec hotfix --undo)' >&2
        exit 1
    fi
    git -C "$REPO_DIR" fetch --quiet --tags --force origin
    if [[ -z $REF ]]; then
        REF=$(git -C "$REPO_DIR" tag --list 'hispec-*' --sort=-version:refname | head -n1)
        if [[ -z $REF ]]; then
            echo "error: no hispec-* release tag yet; pass --ref main to install the branch." >&2
            exit 1
        fi
    fi
    if git -C "$REPO_DIR" show-ref --verify --quiet "refs/remotes/origin/$REF"; then
        # A branch: follow its tip on origin, refusing rather than dropping local commits
        git -C "$REPO_DIR" checkout --quiet "$REF"
        git -C "$REPO_DIR" merge --quiet --ff-only "origin/$REF"
    else
        git -C "$REPO_DIR" checkout --quiet --detach "$REF"
    fi
    git -C "$REPO_DIR" submodule update --quiet --init --recursive
    # The checkout may have replaced this very script; carry on in the release's copy
    if [[ -z ${HISPEC_INSTALL_CHECKED_OUT:-} ]]; then
        HISPEC_INSTALL_CHECKED_OUT=1 exec "$REPO_DIR/systemd/install.sh" "${ORIGINAL_ARGS[@]}" --ref "$REF"
    fi
    echo "installing $REF ($(git -C "$REPO_DIR" rev-parse --short HEAD))"
fi

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
# Remembered so a later plain run (enrolling an operator, say) stays local
if [[ -n $LOCAL ]]; then
    mkdir -p "$(dirname "$SOURCE_FILE")"
    echo local >"$SOURCE_FILE"
else
    rm -f "$SOURCE_FILE"
fi

exec "$VENV_DIR/bin/hispec" install "${INSTALL_ARGS[@]}"
