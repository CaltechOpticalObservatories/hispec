"""The operator subcommands: deploy, start/stop/restart, enable/disable,
status and logs. ``doctor`` is in its own module."""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple

from . import instances as inst
from . import units
from .instances import Paths, TargetError
from .output import paint


def _err(message: str) -> None:
    print(f"hispec: {message}", file=sys.stderr)


def _resolve(paths: Paths, targets: List[str], names: List[str]) -> Optional[List[str]]:
    """Expand targets, explaining a miss. None means an error was printed."""
    try:
        return inst.resolve(targets, names)
    except TargetError as exc:
        target = str(exc)
        if target in inst.in_repo(paths):
            _err(f"{target} is not deployed on this host; deploy it with: hispec deploy {target}")
        else:
            _err(f"no deployed instance or subsystem matches '{target}' (see: hispec status --all)")
        return None


def _install_file(src: Path, dst: Path, overwrite: bool, dry_run: bool) -> str:
    """Copy src to dst, replacing a different dst only if ``overwrite``.

    Returns what happened, for printing.
    """
    if dst.exists():
        if dst.read_bytes() == src.read_bytes():
            return "unchanged"
        if not overwrite:
            return "kept"
        outcome = "updated"
    else:
        outcome = "copied"
    if dry_run:
        return {"copied": "would copy", "updated": "would update"}[outcome]
    # Write beside the target and rename, so a daemon starting meanwhile never
    # reads half a file. Group-writable so the rest of hispec-ops can edit it;
    # the directory is setgid hispec-ops, which takes care of the group.
    tmp = dst.with_name(f".{dst.name}.{os.getpid()}.tmp")
    try:
        shutil.copyfile(src, tmp)
        os.chmod(tmp, 0o664)
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink()
    return outcome


class _Deployment(NamedTuple):
    name: str
    env_src: Path
    env_dst: Path
    config_src: Path
    config_dst: Path


def _deploy_plan(paths: Paths, names: List[str]) -> Optional[List[_Deployment]]:
    """Work out every copy up front, so a bad name copies nothing at all."""
    plan = []
    problems = 0
    for name in names:
        env_src = paths.repo_instances / f"{name}.env"
        if not inst.NAME_RE.match(name) or not env_src.is_file():
            _err(f"no {env_src}; is '{name}' a hispec instance? (see: hispec status --all)")
            problems += 1
            continue
        config = inst.read_env(env_src).get("HISPEC_CONFIG", "")
        if not config:
            _err(f"{env_src} sets no HISPEC_CONFIG")
            problems += 1
            continue
        found = inst.repo_configs(paths, name)
        if len(found) != 1:
            where = ", ".join(str(p) for p in found) or "none"
            _err(f"{name}: expected one {paths.repo}/config/*/{name}.yaml, found {where}")
            problems += 1
            continue
        plan.append(_Deployment(name, env_src, paths.instances / f"{name}.env",
                                found[0], Path(config)))
    return None if problems else plan


def _copy(paths: Paths, plan: List[_Deployment], force: bool, dry_run: bool) -> Optional[List[str]]:
    """Copy every file in the plan. Returns the instances whose files changed.

    The instance file only points at things, so it always follows the repo.
    The config is another matter: once deployed it holds this host's real
    ports and addresses, and a silent overwrite would lose them.
    """
    updated = []
    for item in plan:
        print(item.name)
        for src, dst, overwrite in ((item.env_src, item.env_dst, True),
                                    (item.config_src, item.config_dst, force)):
            try:
                outcome = _install_file(src, dst, overwrite, dry_run)
            except OSError as exc:
                print()
                _err(f"cannot write {dst}: {exc.strerror}")
                if isinstance(exc, PermissionError):
                    _err("deploying needs hispec-ops membership; run: hispec doctor")
                return None
            note = ""
            if outcome == "kept":
                where = src.relative_to(paths.repo)
                note = paint(f" (differs from {where}; --force replaces it)", "33")
            elif outcome == "updated" and item.name not in updated:
                updated.append(item.name)
            print(f"  {outcome:<12} {dst}{note}")
    return updated


def deploy(paths: Paths, args: argparse.Namespace) -> int:
    """Copy instance files and configs from the repo, then enable and start."""
    if args.new:
        have = set(inst.deployed(paths))
        names = [n for n in inst.in_repo(paths) if n not in have] + list(args.names)
        if not names:
            print(f"Nothing to deploy: every instance in {paths.repo_instances} "
                  "is already deployed.")
            return 0
    elif args.names:
        names = list(args.names)
    else:
        _err("name the instances to deploy, or pass --new")
        return 2

    plan = _deploy_plan(paths, list(dict.fromkeys(names)))
    if plan is None:
        return 1
    updated = _copy(paths, plan, args.force, args.dry_run)
    if updated is None:
        return 1

    names = [item.name for item in plan]
    rc = 0
    if not args.no_enable:
        rc |= _enable(names, [], args.dry_run)
    if not args.no_start:
        print()
        rc |= _act(names, "start", args.dry_run)

    running = units.states(updated) if updated and not args.dry_run else {}
    restart = [n for n, s in running.items() if s.running]
    if restart:
        print()
        print("Already running with the old files; to pick up the new ones:")
        print(f"  hispec restart {' '.join(restart)}")
    return rc


def _enable(names: List[str], options: List[str], dry_run: bool) -> int:
    verb = "disable" if "--disable" in options else "enable"
    if dry_run:
        print(f"would {verb} at boot: {' '.join(names)}")
        return 0
    proc = units.enable_helper([*options, *names])
    if proc.returncode == 0:
        print(f"{verb}d at boot: {' '.join(names)}")
        return 0
    detail = (proc.stderr or proc.stdout).strip()
    if "password is required" in detail or proc.returncode == 127:
        _err(f"cannot run {units.ENABLE_HELPER} without a password: {detail}")
        _err("an admin needs to add you to hispec-ops, or re-run install.sh; "
             "run: hispec doctor")
    else:
        _err(detail or f"{units.ENABLE_HELPER} failed")
    return 1


def enable(paths: Paths, args: argparse.Namespace) -> int:
    """Add instances to (or remove them from) the set started at boot."""
    names = _resolve(paths, args.targets, inst.deployed(paths))
    if names is None:
        return 1
    options = (["--disable"] if args.verb == "disable" else []) + (["--now"] if args.now else [])
    return _enable(names, options, args.dry_run)


_DONE = {"start": "started", "stop": "stopped", "restart": "restarted"}


def _act(names: List[str], verb: str, dry_run: bool) -> int:
    """Apply a verb to every instance, carrying on past failures."""
    state = units.states(names)
    failed = []
    for name in names:
        if verb == "start" and state[name].active == "active":
            print(f"{name:<24} already running")
            continue
        if verb == "stop" and not state[name].running:
            print(f"{name:<24} not running")
            continue
        if dry_run:
            print(f"{name:<24} would {verb}")
            continue
        if units.systemctl(verb, name):
            print(f"{name:<24} {_DONE[verb]}")
        else:
            print(f"{name:<24} " + paint("FAILED", "31") + f" (hispec logs {name})")
            failed.append(name)
    if failed:
        print()
        _err(f"{len(failed)} of {len(names)} failed to {verb}: {' '.join(failed)}")
        return 1
    return 0


def act(paths: Paths, args: argparse.Namespace) -> int:
    """start/stop/restart instances or whole subsystems."""
    names = _resolve(paths, args.targets, inst.deployed(paths))
    if names is None:
        return 1
    if args.verb == "stop":
        # Undo a start in the opposite order: `hispec stop power fei` would
        # otherwise cut power before the mechanisms had parked.
        names.reverse()
    return _act(names, args.verb, args.dry_run)


_STATE_COLOR = {"active": "32", "failed": "31", "activating": "33", "deactivating": "33"}


def status(paths: Paths, args: argparse.Namespace) -> int:
    """One line per instance: running? enabled at boot? since when?"""
    here = inst.deployed(paths)
    repo = inst.in_repo(paths)
    universe = sorted(set(here) | set(repo)) if args.all else here
    if args.targets:
        names = _resolve(paths, args.targets, universe)
        if names is None:
            return 1
    else:
        names = universe
    if not names:
        print(f"No instances deployed in {paths.instances}.")
        print("See what the repo defines with: hispec status --all")
        return 0

    rows = _status_rows(paths, names, here)
    width = max(len("INSTANCE"), *(len(r[0]) for r in rows))
    print(f"{'INSTANCE':<{width}}  {'STATE':<12}  {'BOOT':<8}  {'SINCE':<19}  DAEMON")
    for name, active, enabled, since, daemon in rows:
        colored = paint(f"{active:<12}", _STATE_COLOR.get(active, ""))
        print(f"{name:<{width}}  {colored}  {enabled:<8}  {since:<19}  {daemon}")

    if not args.all and not args.targets:
        missing = [n for n in repo if n not in here]
        if missing:
            print()
            print(f"{len(missing)} more in the repo, not deployed here "
                  "(hispec status --all; hispec deploy --new)")
    return 0


def _status_rows(paths: Paths, names: List[str], here: List[str]) -> List[Tuple[str, ...]]:
    state = units.states([n for n in names if n in here])
    rows = []
    for name in names:
        if name not in here:
            daemon = _daemon(paths.repo_instances / f"{name}.env")
            rows.append((name, "not deployed", "", "", daemon))
            continue
        s = state[name]
        since = s.since if s.active != "inactive" else ""
        rows.append((name, s.active, s.enabled, since, _daemon(paths.instances / f"{name}.env")))
    return rows


def _daemon(env: Path) -> str:
    try:
        return inst.read_env(env).get("HISPEC_DAEMON", "?")
    except OSError:
        return "?"


def logs(paths: Paths, args: argparse.Namespace) -> int:
    """Hand over to journalctl for the selected instances."""
    known = sorted(set(inst.deployed(paths)) | set(inst.in_repo(paths)))
    names = _resolve(paths, args.targets, known)
    if names is None:
        return 1
    cmd = ["journalctl"]
    for name in names:
        cmd += ["-u", inst.unit(name)]
    if args.follow:
        cmd.append("-f")
    if args.lines is not None:
        cmd += ["-n", str(args.lines)]
    elif not args.since and not args.follow:
        cmd += ["-n", "100"]
    if args.since:
        cmd += ["--since", args.since]
    if args.priority:
        cmd += ["-p", args.priority]
    try:
        os.execvp(cmd[0], cmd)
    except FileNotFoundError:
        _err("journalctl not found; this host does not look like it runs systemd")
    return 1
