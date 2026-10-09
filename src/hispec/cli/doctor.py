"""``doctor``: check this host's setup and say what is wrong.
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
from typing import Optional

from . import instances as inst
from . import units
from .instances import Paths
from .output import paint

LOG_DIR_TEMPLATE = "/var/log/{name}"


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


def _is_file(path: Optional[Path]) -> bool:
    """Whether path is a file, treating one we may not stat as absent."""
    if path is None:
        return False
    try:
        return path.is_file()
    except OSError:
        return False


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


def _account(r: Report, paths: Paths) -> None:
    product = paths.product
    group = product.ops_group
    r.section("Your account")
    me = pwd.getpwuid(os.geteuid()).pw_name
    groups = _my_groups()
    if os.geteuid() == 0:
        r.warn("running as root, so the permission checks below say nothing about operators")
        r.hint(f"re-run as your own user: {product.name} doctor")
    if not _group_exists(group):
        r.bad(f"group {group} does not exist")
        r.hint("an admin needs to run systemd/install.sh on this host")
    elif group in groups:
        r.ok(f"you are in {group}")
    else:
        r.bad(f"you are NOT in {group}, which is why systemctl asks for a password")
        r.hint(f"admin: sudo {paths.repo}/systemd/install.sh {me}")
        r.hint(f"then log out and back in (or run: newgrp {group})")
    if "systemd-journal" in groups:
        r.ok("you are in systemd-journal (can read other units' logs)")
    else:
        r.warn(f"you are not in systemd-journal; {product.name} logs will be empty")
        r.hint(f"admin: sudo usermod -aG systemd-journal {me}")


def _install_hint(paths: Paths) -> str:
    return f"admin: sudo {paths.repo}/systemd/install.sh"


def _unit_and_polkit(r: Report, paths: Paths) -> None:
    product = paths.product
    install = _install_hint(paths)
    unit_file = product.unit_template
    polkit_rule = product.polkit_rule
    r.section("Unit and polkit")
    repo_unit = paths.repo / "systemd" / unit_file.name
    if unit_file.is_file():
        r.ok(f"{unit_file} installed")
        if repo_unit.is_file() and not filecmp.cmp(unit_file, repo_unit, shallow=False):
            r.warn(f"installed unit differs from {repo_unit}")
            r.hint(install)
    else:
        r.bad(f"{unit_file} is missing")
        r.hint(install)
    if _is_file(product.legacy_unit_path):
        r.warn(f"the old {product.legacy_unit} is still installed")
        r.hint(f"{install}   # migrates instances to {product.name}@")
    try:
        rule = polkit_rule.read_text(encoding="utf-8")
    except FileNotFoundError:
        r.bad(f"{polkit_rule} is missing, so every start/stop will prompt")
        r.hint(install)
    except OSError:
        # rules.d is 0750 root:polkitd on some hosts, so an operator cannot
        # even stat inside it; unreadable means unknown, not missing
        r.warn(f"cannot read {polkit_rule}, so the polkit rule is unchecked")
        r.hint(f"sudo {product.name} doctor")
    else:
        r.ok(f"{polkit_rule} installed")
        if f'indexOf("{product.name}@")' not in rule:
            r.bad(f"the installed polkit rule does not match {product.name}@ units")
            r.hint(f"it is probably the pre-rename copy; {install}")
    legacy_rule = product.legacy_polkit_path
    if _is_file(legacy_rule):
        r.warn(f"the old {legacy_rule.name} is still installed "
               "(harmless, matches nothing now)")
        r.hint(f"admin: sudo rm {legacy_rule}")
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
    product = paths.product
    install = _install_hint(paths)
    sudoers, helper = product.sudoers, str(product.enable_helper)
    if not sudoers.is_file():
        r.warn(f"no {sudoers}; enabling an instance at boot needs an admin")
        r.hint(install)
    elif os.geteuid() != 0 and product.ops_group in _my_groups():
        if units.run(["sudo", "-n", "-l", helper], capture=True).returncode == 0:
            r.ok(f"you can run {product.name} enable without a password")
        else:
            r.bad(f"sudo will not run {helper} for you without a password")
            r.hint(f"{sudoers} or {helper} is out of date; {install}")
    else:
        r.ok(f"{sudoers} installed (passwordless {product.name} enable)")


def _paths(r: Report, paths: Paths) -> None:
    install = _install_hint(paths)
    r.section("Paths")
    log_dir = Path(LOG_DIR_TEMPLATE.format(name=paths.product.name))
    for directory in (paths.etc, paths.instances, log_dir):
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
        r.hint(f"{paths.product.name} deploy <name>   "
               f"# or: {paths.product.name} deploy --new")
        return
    product = paths.product
    state = units.states(product, names)
    for name in names:
        env_file = paths.instances / f"{name}.env"
        env = inst.read_env(env_file)
        script = env.get(product.env_key("DAEMON"), "")
        config = env.get(product.env_key("CONFIG"), "")
        repo_env = paths.repo_instances / f"{name}.env"
        if not script:
            r.bad(f"{name}: {env_file} sets no {product.env_key('DAEMON')}")
        elif not (paths.repo / "daemons" / script).is_file():
            r.bad(f"{name}: daemon script {paths.repo}/daemons/{script} does not exist")
        elif not config or not Path(config).is_file():
            r.bad(f"{name}: config {config or '<unset>'} does not exist")
            r.hint(f"{product.name} deploy {name}")
        elif state[name].active == "active":
            r.ok(f"{name}: running")
        else:
            r.warn(f"{name}: {state[name].active}")
            r.hint(f"{product.name} start {name}")
            r.hint(f"{product.name} logs {name}")
        if repo_env.is_file() and not filecmp.cmp(env_file, repo_env, shallow=False):
            r.warn(f"{name}: deployed instance file differs from {repo_env}")
            r.hint(f"{product.name} deploy {name}   "
                   "# updates the instance file, keeps the config")
        elif not repo_env.is_file():
            r.warn(f"{name}: deployed here but not defined in {paths.repo_instances}")


def _secrets(r: Report, paths: Paths) -> None:
    r.section("Credentials")
    needed = inst.required_secrets(paths)
    present = inst.secrets_set(paths)
    if present is None:
        r.warn(f"cannot read {paths.secrets}, so the credentials below are unchecked")
        r.hint(f"sudo {paths.product.name} doctor")
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
    is an operational decision, and ``status`` already lists the rest.
    """
    r.section("Host assignment")
    role = inst.host_role(paths)
    r.ok(f"this host is '{role}'")
    unassigned = []
    for name in inst.deployed(paths):
        claimed = inst.assigned_host(paths.product, paths.instances / f"{name}.env")
        if claimed is None:
            unassigned.append(name)
        elif claimed != role:
            r.bad(f"{name}: deployed here but assigned to '{claimed}'")
    if unassigned:
        r.warn(f"no {paths.product.env_key('HOST')}, so nothing says where they belong: "
               f"{' '.join(unassigned)}")


def doctor(paths: Paths, _args: argparse.Namespace) -> int:
    """Run every check and exit 1 if any FAILed."""
    me = pwd.getpwuid(os.geteuid()).pw_name
    print(f"{paths.product.name} doctor: {socket.gethostname()}, running as {me}")
    r = Report()
    _account(r, paths)
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
