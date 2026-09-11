#!/usr/bin/env bash
# One-time host setup for running daemons/generic/* daemons under systemd.
# Run as root.

set -euo pipefail

REPO_DIR="${HISPEC_REPO_DIR:-/opt/hispec/app}"
VENV_DIR="${HISPEC_VENV_DIR:-/opt/hispec/venv}"

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

# hispec-ops: humans in this group can edit configs and start/stop/restart
# hispec-daemon@* units without sudo (see systemd/polkit/*.rules). The
# hispec system user joins it too, so it can read what operators write.
if ! getent group hispec-ops &>/dev/null; then
    groupadd --system hispec-ops
    echo "created group 'hispec-ops'"
fi

# System user the daemons run as.
if ! id hispec &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin -G hispec-ops hispec
    echo "created system user 'hispec'"
else
    usermod -aG hispec-ops hispec
fi

# Config/log directories. Setgid (2775/2750) so files created by any
# hispec-ops member keep the group, instead of the creating user's own.
install -d -o hispec -g hispec-ops -m 2775 /etc/hispec
install -d -o hispec -g hispec-ops -m 2775 /etc/hispec/instances
install -d -o hispec -g hispec-ops -m 2750 /var/log/hispec

# Python environment (editable install so `git pull` picks up code changes
# without reinstalling).
if [[ ! -x "$VENV_DIR/bin/python3" ]]; then
    python3 -m venv "$VENV_DIR"
    echo "created venv at $VENV_DIR"
fi
"$VENV_DIR/bin/pip" install -U pip
"$VENV_DIR/bin/pip" install -e "$REPO_DIR"
chown -R hispec:hispec "$VENV_DIR"

# Unit file + polkit rule (grants hispec-ops members start/stop/restart on
# hispec-daemon@* without sudo; enable/disable still needs an admin).
install -m 0644 "$REPO_DIR/systemd/hispec-daemon@.service" /etc/systemd/system/hispec-daemon@.service
install -m 0644 "$REPO_DIR/systemd/polkit/49-hispec-daemons.rules" /etc/polkit-1/rules.d/49-hispec-daemons.rules
systemctl daemon-reload

cat <<EOF

Host setup complete.

Add each operator to the right groups (they'll need to log out/in, or run
'newgrp hispec-ops', for it to take effect):
  usermod -aG hispec-ops,systemd-journal <username>

Once in hispec-ops, they can — without sudo:
  - create/edit /etc/hispec/*.yaml and /etc/hispec/instances/*.env
  - systemctl start|stop|restart hispec-daemon@<name>
  - journalctl -u hispec-daemon@<name>

For each daemon instance you want to run (see systemd/README.md for the
full list already wired up under config/hsfei/ and config/hscal/):
  1. Copy its config, e.g. config/hsfei/<name>.yaml, into /etc/hispec/<name>.yaml,
     and fill in real hardware values.
  2. Copy the matching systemd/instances/<name>.env to
     /etc/hispec/instances/<name>.env.
  3. systemctl enable --now hispec-daemon@<name>   # enable still needs an admin

See systemd/README.md for details.
EOF
