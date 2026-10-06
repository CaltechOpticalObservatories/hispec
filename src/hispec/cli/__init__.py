"""``hispec``: deploy, run and inspect the HISPEC daemons on this host.

One command for operators and developers, replacing the separate
hispec-fei-start / hispec-fei-stop / hispec-doctor scripts. Host setup
(users, groups, unit file, polkit, venv) is still systemd/install.sh, run by
an admin; nothing here needs root.
"""
from __future__ import annotations

import argparse
from typing import List, Optional

from . import commands
from .doctor import doctor
from .instances import Paths

TARGETS_HELP = ("instance names (hsfei_adc), subsystems (hsfei, or just fei), "
                "or 'all'")

EPILOG = """\
examples:
  hispec status                     what is deployed here, and is it running?
  hispec deploy hsfei_newthing      copy its files from the repo, enable, start
  hispec deploy --new               the same for every instance not deployed yet
  hispec start fei                  start every deployed hsfei_* daemon
  hispec stop fei                   stop them, in reverse order
  hispec restart hsfei_adc          e.g. after editing /etc/hispec/hsfei_adc.yaml
  hispec logs hsfei_adc -f          follow its log
  hispec doctor                     why isn't it working?

Every subcommand takes --help. Full guide:
  https://caltechopticalobservatories.github.io/hispec/operations/systemd.html
"""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hispec",
        description="Deploy, run and inspect the HISPEC daemons on this host.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    def add(name, func, help_text, description=None):
        p = sub.add_parser(name, help=help_text, description=description or help_text,
                           formatter_class=argparse.RawDescriptionHelpFormatter)
        p.set_defaults(func=func)
        return p

    p = add("deploy", commands.deploy,
            "copy instances from the repo to this host, enable and start them",
            "Copy each instance's .env and config from the repo into /etc/hispec, add\n"
            "it to the boot set, and start it. No daemon-reload or install.sh needed.\n\n"
            "The instance file always follows the repo. A deployed config that differs\n"
            "from the repo is kept, since it holds this host's real hardware values;\n"
            "pass --force to replace it.")
    p.add_argument("names", nargs="*", metavar="name", help="instances to deploy")
    p.add_argument("--new", action="store_true",
                   help="deploy every repo instance not yet deployed here")
    p.add_argument("--force", action="store_true",
                   help="replace deployed configs that differ from the repo")
    p.add_argument("--any-host", action="store_true",
                   help="deploy even if the instance names a different host")
    p.add_argument("--no-start", action="store_true", help="do not start them now")
    p.add_argument("--no-enable", action="store_true", help="do not start them at boot")
    p.add_argument("-n", "--dry-run", action="store_true", help="print what would happen")

    for verb, text in (("start", "start daemons (already-running ones are left alone)"),
                       ("stop", "stop daemons, in reverse order (they still start at boot)"),
                       ("restart", "restart daemons, e.g. after a config edit or git pull")):
        p = add(verb, commands.act, text)
        p.set_defaults(verb=verb)
        p.add_argument("targets", nargs="+", metavar="target", help=TARGETS_HELP)
        p.add_argument("-n", "--dry-run", action="store_true", help="print what would happen")

    for verb, text in (("enable", "start daemons at every boot (--now: and start now)"),
                       ("disable", "stop starting daemons at boot (--now: and stop now)")):
        p = add(verb, commands.enable, text)
        p.set_defaults(verb=verb)
        p.add_argument("targets", nargs="+", metavar="target", help=TARGETS_HELP)
        now = "start" if verb == "enable" else "stop"
        p.add_argument("--now", action="store_true", help=f"also {now} them now")
        p.add_argument("-n", "--dry-run", action="store_true", help="print what would happen")

    p = add("status", commands.status, "show each daemon: running? enabled at boot? since when?")
    p.add_argument("targets", nargs="*", metavar="target", help=TARGETS_HELP)
    p.add_argument("-a", "--all", action="store_true",
                   help="include instances defined in the repo but not deployed here")

    p = add("logs", commands.logs, "show daemon logs (journalctl)")
    p.add_argument("targets", nargs="+", metavar="target", help=TARGETS_HELP)
    p.add_argument("-f", "--follow", action="store_true", help="keep printing new lines")
    p.add_argument("-n", "--lines", type=int, help="how many lines (default 100)")
    p.add_argument("--since", help='e.g. "1 hour ago", today, "2026-09-21 09:00"')
    p.add_argument("-p", "--priority", help="e.g. err, warning")

    add("doctor", doctor, "check this host and your account, and say what to fix")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the ``hispec`` console script."""
    parser = _parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    try:
        return args.func(Paths.from_env(), args)
    except KeyboardInterrupt:
        return 130
