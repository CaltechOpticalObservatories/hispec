#!/usr/bin/env bash
# One-time host setup for running the hispec daemons under systemd.
# Run as root. Safe to re-run: it converges the host onto the current repo.
#
#   sudo ./systemd/install.sh                    # set the host up
#   sudo ./systemd/install.sh alice bob          # ... and enrol two operators
#   sudo HISPEC_OPS_USERS="alice bob" ./systemd/install.sh   # same thing
#
# Operators named here are added to hispec-ops and systemd-journal, which is
# what lets them start/stop/restart daemons and read logs without a password.
# Skipping that step is the single most common reason systemctl keeps
# prompting. See docs/operations/systemd.md.

set -euo pipefail

REPO_DIR="${HISPEC_REPO_DIR:-/opt/hispec/app}"
VENV_DIR="${HISPEC_VENV_DIR:-/opt/hispec/venv}"
OPS_USERS="${HISPEC_OPS_USERS:-} $*"

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
# hispec@* units without sudo (see systemd/polkit/*.rules). The hispec system
# user joins it too, so it can read what operators write.
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

# Operators. Doing this here rather than printing advice at the end is
# deliberate: an operator who is not in hispec-ops gets a root password prompt
# from every systemctl call, and has no way to tell that group membership is
# the reason.
for user in $OPS_USERS; do
    if ! id "$user" &>/dev/null; then
        echo "warning: no such user '$user', skipping" >&2
        continue
    fi
    usermod -aG hispec-ops "$user"
    if getent group systemd-journal &>/dev/null; then
        usermod -aG systemd-journal "$user"
    fi
    echo "added '$user' to hispec-ops, systemd-journal (they must log out and back in)"
done

# Config/log directories. Setgid (2775/2750) so files created by any
# hispec-ops member keep the group, instead of the creating user's own.
install -d -o hispec -g hispec-ops -m 2775 /etc/hispec
install -d -o hispec -g hispec-ops -m 2775 /etc/hispec/instances
install -d -o hispec -g hispec-ops -m 2750 /var/log/hispec

# Shared secrets, read by every unit if present. Root-only on purpose: the
# instance files above are group-readable by hispec-ops, which is right for
# configs and wrong for a database token.
if [[ ! -e /etc/hispec/secrets.env ]]; then
    cat > /etc/hispec/secrets.env <<'EOF'
# Environment for every hispec@ instance. Root-only; keep secrets here rather
# than in /etc/hispec/instances/*.env, which operators can read.
#
# HISPEC_INFLUX_TOKEN=<InfluxDB write token, for generic/keygrabber>
EOF
    echo "created /etc/hispec/secrets.env"
fi
chown root:root /etc/hispec/secrets.env
chmod 0600 /etc/hispec/secrets.env

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
# hispec@* without sudo).
install -m 0644 "$REPO_DIR/systemd/hispec@.service" /etc/systemd/system/hispec@.service
[[ -d /etc/polkit-1/rules.d ]] || install -d -m 0750 /etc/polkit-1/rules.d
install -m 0644 "$REPO_DIR/systemd/polkit/49-hispec.rules" /etc/polkit-1/rules.d/49-hispec.rules

# Operator commands.
install -d -m 0755 /usr/local/bin /usr/local/sbin
install -m 0755 "$REPO_DIR/systemd/bin/hispec-fei-start" /usr/local/bin/hispec-fei-start
install -m 0755 "$REPO_DIR/systemd/bin/hispec-fei-stop"  /usr/local/bin/hispec-fei-stop
install -m 0755 "$REPO_DIR/systemd/bin/hispec-doctor"    /usr/local/bin/hispec-doctor
install -m 0755 "$REPO_DIR/systemd/bin/hispec-enable"    /usr/local/sbin/hispec-enable

# Passwordless enable/disable, scoped to that one helper. Polkit cannot scope
# manage-unit-files to a unit name, so `systemctl enable hispec@x` would
# otherwise prompt for a password every time an instance is deployed.
sudoers_tmp=$(mktemp)
cat > "$sudoers_tmp" <<'EOF'
# Installed by hispec systemd/install.sh. Lets hispec-ops members enable and
# disable hispec@<instance> units at boot without a password. The helper
# validates the instance name and refuses anything that is not a deployed
# hispec instance, so this does not grant control of other units.
%hispec-ops ALL=(root) NOPASSWD: /usr/local/sbin/hispec-enable
EOF
if visudo -cqf "$sudoers_tmp"; then
    install -m 0440 -o root -g root "$sudoers_tmp" /etc/sudoers.d/hispec-ops
else
    echo "warning: generated sudoers file failed validation, not installing" >&2
fi
rm -f "$sudoers_tmp"

systemctl daemon-reload

# Migration: the template unit used to be called hispec-daemon@.service. Move
# any instance that was enabled or running onto hispec@ and drop the old unit,
# preserving whether it was enabled and whether it was up.
if [[ -f /etc/systemd/system/hispec-daemon@.service ]]; then
    echo
    echo "migrating hispec-daemon@* instances to hispec@*"
    old_instances=$(
        {
            systemctl list-units --all --no-legend --plain 'hispec-daemon@*.service' 2>/dev/null |
                awk '{ print ($1 ~ /^hispec-daemon@/) ? $1 : $2 }'
            find /etc/systemd/system -name 'hispec-daemon@*.service' -not -name 'hispec-daemon@.service' \
                -printf '%f\n' 2>/dev/null
        } | sort -u
    )
    for old_unit in $old_instances; do
        name=${old_unit#hispec-daemon@}
        name=${name%.service}
        [[ -n $name ]] || continue
        was_active=no
        if systemctl is-active --quiet "$old_unit"; then was_active=yes; fi
        was_enabled=no
        if [[ $(systemctl is-enabled "$old_unit" 2>/dev/null) == enabled ]]; then was_enabled=yes; fi

        systemctl disable --now "$old_unit" >/dev/null 2>&1 || true
        if [[ $was_enabled == yes ]]; then systemctl enable "hispec@$name.service" >/dev/null; fi
        if [[ $was_active == yes ]]; then systemctl start "hispec@$name.service" || true; fi
        echo "  $name: enabled=$was_enabled active=$was_active -> hispec@$name"
    done
    rm -f /etc/systemd/system/hispec-daemon@.service
    rm -f /etc/polkit-1/rules.d/49-hispec-daemons.rules
    systemctl daemon-reload
    echo "  removed hispec-daemon@.service and its polkit rule"
fi

echo
echo "Host setup complete."

# Report deployed-but-not-enabled instances rather than enabling them: whether
# an instance should come up at boot is an operational decision, not ours.
pending=""
for env_file in /etc/hispec/instances/*.env; do
    [[ -f $env_file ]] || continue
    name=${env_file##*/}; name=${name%.env}
    if [[ $(systemctl is-enabled "hispec@$name.service" 2>/dev/null) == enabled ]]; then
        continue
    fi
    pending+=" $name"
done
if [[ -n $pending ]]; then
    echo
    echo "Deployed but not set to start at boot:$pending"
    echo "  hispec-enable --now$pending"
fi

cat <<EOF

Operators in hispec-ops can, with no password:
  - create/edit /etc/hispec/*.yaml and /etc/hispec/instances/*.env
  - systemctl start|stop|restart hispec@<name>, and hispec-fei-start/stop
  - hispec-enable [--now|--disable] <name>
  - journalctl -u hispec@<name>

To enrol more operators later:
  sudo $REPO_DIR/systemd/install.sh <username> ...

If systemctl still asks for a password, run 'hispec-doctor' as that user.
Full instructions: docs/operations/systemd.md
EOF
