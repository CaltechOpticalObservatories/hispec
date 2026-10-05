"""``hispec doctor``: check this host's setup and say what is wrong.
"""
from __future__ import annotations

import argparse
import filecmp
import grp
import os
import pwd
import socket
import stat
from pathlib import Path

from . import instances as inst
from . import units
from .instances import Paths
from .output import paint

UNIT_FILE = Path("/etc/systemd/system/hispec@.service")
OLD_UNIT_FILE = Path("/etc/systemd/system/hispec-daemon@.service")
POLKIT_RULE = Path("/etc/polkit-1/rules.d/49-hispec.rules")
OLD_POLKIT_RULE = Path("/etc/polkit-1/rules.d/49-hispec-daemons.rules")
SUDOERS = Path("/etc/sudoers.d/hispec-ops")


class Report:
    """Collects ok/FAIL/warn lines; FAILs decide the exit status."""

    def __init__(self) -> None:
        self.problems = 0

    @staticmethod
    def section(title: str) -> None:
        """Start a group of checks."""
        print()
        print(title)

    @staticmethod
    def ok(text: str) -> None:
        """A check that passed."""
        print(f"  {paint('ok', '32')}    {text}")

    def bad(self, text: str) -> None:
        """A check that failed: something an operator needs is missing."""
        print(f"  {paint('FAIL', '31')}  {text}")
        self.problems += 1

    @staticmethod
    def warn(text: str) -> None:
        """Worth knowing, but not broken."""
        print(f"  {paint('warn', '33')}  {text}")

    @staticmethod
    def hint(text: str) -> None:
        """The command that fixes the line above."""
        print(f"        → {text}")


def _my_groups() -> set:
    names = set()
    for gid in os.getgroups():
        try:
            names.add(grp.getgrgid(gid).gr_name)
        except KeyError:
            pass
    return names


def _group_exists(name: str) -> bool:
    try:
        grp.getgrnam(name)
        return True
    except KeyError:
        return False


def _owner(path: Path) -> str:
    st = path.stat()
    try:
        user = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        user = str(st.st_uid)
    try:
        group = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        group = str(st.st_gid)
    return f"{user}:{group} {stat.S_IMODE(st.st_mode):o}"


def _version_tuple(text: str) -> tuple:
    try:
        return tuple(int(p) for p in text.split("."))
    except ValueError:
        return ()


def _account(r: Report) -> None:
    r.section("Your account")
    me = pwd.getpwuid(os.geteuid()).pw_name
    groups = _my_groups()
    if os.geteuid() == 0:
        r.warn("running as root, so the permission checks below say nothing about operators")
        r.hint("re-run as your own user: hispec doctor")
    if not _group_exists("hispec-ops"):
        r.bad("group hispec-ops does not exist")
        r.hint("an admin needs to run systemd/install.sh on this host")
    elif "hispec-ops" in groups:
        r.ok("you are in hispec-ops")
    else:
        r.bad("you are NOT in hispec-ops — this is why systemctl asks for a password")
        r.hint(f"admin: sudo /opt/hispec/app/systemd/install.sh {me}")
        r.hint("then log out and back in (or run: newgrp hispec-ops)")
    if "systemd-journal" in groups:
        r.ok("you are in systemd-journal (can read other units' logs)")
    else:
        r.warn("you are not in systemd-journal; hispec logs will be empty")
        r.hint(f"admin: sudo usermod -aG systemd-journal {me}")


def _install_hint(paths: Paths) -> str:
    return f"admin: sudo {paths.repo}/systemd/install.sh"


def _unit_and_polkit(r: Report, paths: Paths) -> None:
    install = _install_hint(paths)
    r.section("Unit and polkit")
    repo_unit = paths.repo / "systemd" / "hispec@.service"
    if UNIT_FILE.is_file():
        r.ok(f"{UNIT_FILE} installed")
        if repo_unit.is_file() and not filecmp.cmp(UNIT_FILE, repo_unit, shallow=False):
            r.warn(f"installed unit differs from {repo_unit}")
            r.hint(install)
    else:
        r.bad(f"{UNIT_FILE} is missing")
        r.hint(install)
    if OLD_UNIT_FILE.is_file():
        r.warn("the old hispec-daemon@.service is still installed")
        r.hint(f"{install}   # migrates instances to hispec@")
    if POLKIT_RULE.is_file():
        r.ok(f"{POLKIT_RULE} installed")
        if 'indexOf("hispec@")' not in POLKIT_RULE.read_text(encoding="utf-8"):
            r.bad("the installed polkit rule does not match hispec@ units")
            r.hint(f"it is probably the pre-rename copy; {install}")
    else:
        r.bad(f"{POLKIT_RULE} is missing — every start/stop will prompt")
        r.hint(install)
    if OLD_POLKIT_RULE.is_file():
        r.warn(f"the old {OLD_POLKIT_RULE.name} is still installed (harmless, matches nothing now)")
        r.hint(f"admin: sudo rm {OLD_POLKIT_RULE}")
    _polkit_daemon(r)


def _polkit_daemon(r: Report) -> None:
    proc = units.run(["pkaction", "--version"], capture=True)
    if proc.returncode == 127:
        r.warn("pkaction not found; cannot check the polkit version")
    else:
        version = (proc.stdout.split() or [""])[-1]
        # JavaScript .rules files need polkit 0.106+; older polkit ignores
        # them silently and every operator gets an auth prompt instead.
        if _version_tuple(version) >= (0, 106):
            r.ok(f"polkit {version} supports JavaScript .rules")
        else:
            r.bad(f"polkit {version or 'unknown'} is too old for .rules files (need 0.106+)")
            r.hint("the rule is ignored silently; operators will keep getting auth prompts")
    if any(units.run(["systemctl", "is-active", "--quiet", svc]).returncode == 0
           for svc in ("polkit.service", "polkitd.service")):
        r.ok("polkit is running")
    else:
        r.warn("polkit does not look like it is running")
        r.hint("admin: sudo systemctl start polkit")


def _sudo(r: Report, paths: Paths) -> None:
    install = _install_hint(paths)
    if not SUDOERS.is_file():
        r.warn(f"no {SUDOERS}; enabling an instance at boot needs an admin")
        r.hint(install)
    elif os.geteuid() != 0 and "hispec-ops" in _my_groups():
        if units.run(["sudo", "-n", "-l", units.ENABLE_HELPER], capture=True).returncode == 0:
            r.ok("you can run hispec enable without a password")
        else:
            r.bad("sudo will not run hispec-enable for you without a password")
            r.hint(f"{SUDOERS} or {units.ENABLE_HELPER} is out of date; {install}")
    else:
        r.ok(f"{SUDOERS} installed (passwordless hispec enable)")


def _paths(r: Report, paths: Paths) -> None:
    install = _install_hint(paths)
    r.section("Paths")
    for directory in (paths.etc, paths.instances, Path("/var/log/hispec")):
        if directory.is_dir():
            r.ok(f"{directory} exists ({_owner(directory)})")
        else:
            r.bad(f"{directory} is missing")
            r.hint(install)
    if paths.repo.is_dir():
        r.ok(f"{paths.repo} checked out")
    else:
        r.bad(f"{paths.repo} is missing")
    if (paths.venv / "bin" / "python3").exists():
        r.ok(f"{paths.venv} venv present")
    else:
        r.bad(f"{paths.venv}/bin/python3 is missing")
        r.hint(install)


def _deployed(r: Report, paths: Paths) -> None:
    r.section("Deployed instances")
    names = inst.deployed(paths)
    if not names:
        r.warn(f"no instance files in {paths.instances} — nothing is deployed on this host")
        r.hint("hispec deploy <name>   # or: hispec deploy --new")
        return
    state = units.states(names)
    for name in names:
        env_file = paths.instances / f"{name}.env"
        env = inst.read_env(env_file)
        script = env.get("HISPEC_DAEMON", "")
        config = env.get("HISPEC_CONFIG", "")
        repo_env = paths.repo_instances / f"{name}.env"
        if not script:
            r.bad(f"{name}: {env_file} sets no HISPEC_DAEMON")
        elif not (paths.repo / "daemons" / script).is_file():
            r.bad(f"{name}: daemon script {paths.repo}/daemons/{script} does not exist")
        elif not config or not Path(config).is_file():
            r.bad(f"{name}: config {config or '<unset>'} does not exist")
            r.hint(f"hispec deploy {name}")
        elif state[name].active == "active":
            r.ok(f"{name}: running")
        else:
            r.warn(f"{name}: {state[name].active}")
            r.hint(f"hispec start {name}")
            r.hint(f"hispec logs {name}")
        if repo_env.is_file() and not filecmp.cmp(env_file, repo_env, shallow=False):
            r.warn(f"{name}: deployed instance file differs from {repo_env}")
            r.hint(f"hispec deploy {name}   # updates the instance file, keeps the config")
        elif not repo_env.is_file():
            r.warn(f"{name}: deployed here but not defined in {paths.repo_instances}")


def _secrets(r: Report, paths: Paths) -> None:
    r.section("Credentials")
    needed = inst.required_secrets(paths)
    present = inst.secrets_set(paths)
    if present is None:
        r.warn(f"cannot read {paths.secrets}, so the credentials below are unchecked")
        r.hint("sudo hispec doctor")
        return
    for variable in sorted(needed):
        if present.get(variable):
            r.ok(f"{variable} is set")
        else:
            r.bad(f"{variable} is unset, needed by {'; '.join(needed[variable])}")
            r.hint(f"add {variable}=<value> to {paths.secrets}, then restart that daemon")


def _placement(r: Report, paths: Paths) -> None:
    """Flag instances running on the wrong host, or claiming no host at all.

    Only looks at what is deployed: which of the repo's instances a host runs
    is an operational decision, and ``hispec status`` already lists the rest.
    """
    r.section("Host assignment")
    role = inst.host_role(paths)
    r.ok(f"this host is '{role}'")
    unassigned = []
    for name in inst.deployed(paths):
        claimed = inst.assigned_host(paths.instances / f"{name}.env")
        if claimed is None:
            unassigned.append(name)
        elif claimed != role:
            r.bad(f"{name}: deployed here but assigned to '{claimed}'")
    if unassigned:
        r.warn(f"no {inst.HOST_KEY}, so nothing says where they belong: "
               f"{' '.join(unassigned)}")


def doctor(paths: Paths, _args: argparse.Namespace) -> int:
    """Run every check and exit 1 if any FAILed."""
    me = pwd.getpwuid(os.geteuid()).pw_name
    print(f"hispec doctor: {socket.gethostname()}, running as {me}")
    r = Report()
    _account(r)
    _unit_and_polkit(r, paths)
    _sudo(r, paths)
    _paths(r, paths)
    _deployed(r, paths)
    _placement(r, paths)
    _secrets(r, paths)
    print()
    if r.problems == 0:
        print("No problems found.")
        return 0
    print(f"{r.problems} problem(s) found — see the FAIL lines above.")
    return 1
