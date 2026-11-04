"""Tests for the hispec CLI against a fake repo and /etc, with systemd stubbed."""
import subprocess

import pytest

from hispec import cli
from hispec.cli import instances as inst
from hispec.cli import units


@pytest.fixture(name="host")
def fixture_host(tmp_path, monkeypatch):
    """A repo with three instances and an empty /etc/hispec."""
    repo = tmp_path / "repo"
    etc = tmp_path / "etc"
    (repo / "systemd" / "instances").mkdir(parents=True)
    (etc / "instances").mkdir(parents=True)
    for name, daemon in (("hsfei_adc", "hsfei/adc"), ("hsfei_ms", "hsfei/pi-daemon"),
                         ("hspower_fei1", "hspower/eaton_pdu")):
        subsystem = name.split("_", maxsplit=1)[0]
        (repo / "systemd" / "instances" / f"{name}.env").write_text(
            f"# {name}\nHISPEC_DAEMON={daemon}\nHISPEC_CONFIG={etc}/{name}.yaml\n")
        (repo / "config" / subsystem).mkdir(parents=True, exist_ok=True)
        (repo / "config" / subsystem / f"{name}.yaml").write_text(f"name: {name}\n")
    monkeypatch.setenv("HISPEC_REPO_DIR", str(repo))
    monkeypatch.setenv("HISPEC_ETC_DIR", str(etc))

    calls = []
    active = set()

    def fake_run(cmd, capture=False):  # pylint: disable=unused-argument
        calls.append(list(cmd))
        if cmd[:2] == ["systemctl", "show"]:
            blocks = []
            for unit in cmd[4:]:
                name = unit[len("hispec@"):-len(".service")]
                state = "active" if name in active else "inactive"
                blocks.append(f"Id={unit}\nActiveState={state}\nUnitFileState=disabled\n"
                              "StateChangeTimestamp=Mon 2026-09-21 09:14:02 HST")
            return subprocess.CompletedProcess(cmd, 0, "\n\n".join(blocks) + "\n", "")
        if cmd[0] == "systemctl" and cmd[1] in ("start", "restart"):
            active.add(cmd[2][len("hispec@"):-len(".service")])
        if cmd[0] == "systemctl" and cmd[1] == "stop":
            active.discard(cmd[2][len("hispec@"):-len(".service")])
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(units, "run", fake_run)
    return {"repo": repo, "etc": etc, "calls": calls, "active": active}


def _actions(calls):
    return [c for c in calls if c[:2] != ["systemctl", "show"]]


def test_resolve_names_subsystems_and_order():
    """Targets expand to names and prefixes, in command-line order."""
    names = ["hsfei_adc", "hsfei_ms", "hspower_fei1", "hispec_keygrabber"]
    assert inst.resolve(["hsfei_ms"], names) == ["hsfei_ms"]
    assert inst.resolve(["fei"], names) == ["hsfei_adc", "hsfei_ms"]
    assert inst.resolve(["hsfei_"], names) == ["hsfei_adc", "hsfei_ms"]
    assert inst.resolve(["power", "fei"], names) == ["hspower_fei1", "hsfei_adc", "hsfei_ms"]
    assert inst.resolve(["hsfei_ms", "fei"], names) == ["hsfei_ms", "hsfei_adc"]
    assert inst.resolve(["hispec"], names) == ["hispec_keygrabber"]
    assert inst.resolve(["all"], names) == names
    with pytest.raises(inst.TargetError):
        inst.resolve(["hsfei_nope"], names)
    # A subsystem prefix must end at an underscore, not mid-word.
    with pytest.raises(inst.TargetError):
        inst.resolve(["hsfe"], names)


def test_read_env_strips_comments_and_quotes(tmp_path):
    """EnvironmentFile parsing ignores comments and unquotes values."""
    env = tmp_path / "x.env"
    env.write_text('# c\n\nHISPEC_DAEMON="generic/inficon"\nHISPEC_CONFIG=/etc/hispec/x.yaml\n')
    assert inst.read_env(env) == {"HISPEC_DAEMON": "generic/inficon",
                                  "HISPEC_CONFIG": "/etc/hispec/x.yaml"}


def test_deploy_copies_enables_and_starts(host):
    """A plain deploy copies both files, enables, then starts."""
    assert cli.main(["deploy", "hsfei_adc"]) == 0
    assert (host["etc"] / "instances" / "hsfei_adc.env").is_file()
    assert (host["etc"] / "hsfei_adc.yaml").read_text() == "name: hsfei_adc\n"
    assert _actions(host["calls"]) == [
        ["sudo", "-n", units.ENABLE_HELPER, "hsfei_adc"],
        ["systemctl", "start", "hispec@hsfei_adc.service"],
    ]


def test_deploy_keeps_a_host_edited_config_unless_forced(host, capsys):
    """A host-edited config survives a deploy unless --force."""
    (host["etc"] / "hsfei_adc.yaml").write_text("name: hsfei_adc\nport: /dev/ttyUSB3\n")
    assert cli.main(["deploy", "--no-start", "--no-enable", "hsfei_adc"]) == 0
    assert "port: /dev/ttyUSB3" in (host["etc"] / "hsfei_adc.yaml").read_text()
    assert "kept" in capsys.readouterr().out

    assert cli.main(["deploy", "--no-start", "--no-enable", "--force", "hsfei_adc"]) == 0
    assert (host["etc"] / "hsfei_adc.yaml").read_text() == "name: hsfei_adc\n"


def test_deploy_always_updates_the_instance_file(host):
    """The .env follows the repo even when the deployed one differs."""
    deployed = host["etc"] / "instances" / "hsfei_adc.env"
    deployed.write_text("HISPEC_DAEMON=old/path\n")
    assert cli.main(["deploy", "--no-start", "--no-enable", "hsfei_adc"]) == 0
    assert "HISPEC_DAEMON=hsfei/adc" in deployed.read_text()


def test_deploy_suggests_restart_when_running_instance_changed(host, capsys):
    """Changing files under a running daemon prints the restart command."""
    cli.main(["deploy", "hsfei_adc"])
    (host["repo"] / "systemd" / "instances" / "hsfei_adc.env").write_text(
        f"HISPEC_DAEMON=hsfei/adc2\nHISPEC_CONFIG={host['etc']}/hsfei_adc.yaml\n")
    capsys.readouterr()
    cli.main(["deploy", "hsfei_adc"])
    out = capsys.readouterr().out
    assert "already running" in out
    assert "hispec restart hsfei_adc" in out


def test_deploy_new_picks_only_undeployed(host):
    """--new deploys exactly the instances missing from this host."""
    cli.main(["deploy", "--no-start", "--no-enable", "hsfei_adc"])
    host["calls"].clear()
    assert cli.main(["deploy", "--new"]) == 0
    assert ["sudo", "-n", units.ENABLE_HELPER, "hsfei_ms", "hspower_fei1"] in host["calls"]


def test_deploy_unknown_name_copies_nothing(host):
    """One bad name aborts the whole deploy before any copy."""
    assert cli.main(["deploy", "hsfei_adc", "hsfei_typo"]) == 1
    assert not (host["etc"] / "instances" / "hsfei_adc.env").exists()
    assert not _actions(host["calls"])


def test_deploy_dry_run_writes_nothing(host):
    """--dry-run touches neither files nor systemd."""
    assert cli.main(["deploy", "--dry-run", "--new"]) == 0
    assert not list((host["etc"] / "instances").iterdir())
    assert not _actions(host["calls"])


def test_start_skips_running_and_stop_reverses(host):
    """start leaves running daemons alone; stop runs in reverse order."""
    cli.main(["deploy", "--no-start", "--no-enable", "--new"])
    host["active"].add("hsfei_adc")
    host["calls"].clear()
    assert cli.main(["start", "fei"]) == 0
    assert _actions(host["calls"]) == [["systemctl", "start", "hispec@hsfei_ms.service"]]

    host["calls"].clear()
    assert cli.main(["stop", "power", "fei"]) == 0
    assert [c[2] for c in _actions(host["calls"])] == [
        "hispec@hsfei_ms.service", "hispec@hsfei_adc.service"]


def test_start_undeployed_points_at_deploy(host, capsys):  # pylint: disable=unused-argument
    """Starting an undeployed instance says how to deploy it."""
    assert cli.main(["start", "hsfei_adc"]) == 1
    assert "hispec deploy hsfei_adc" in capsys.readouterr().err


def test_enable_uses_the_root_helper(host):
    """enable/disable go through sudo -n and the root helper."""
    cli.main(["deploy", "--no-start", "--no-enable", "hsfei_adc"])
    host["calls"].clear()
    assert cli.main(["disable", "--now", "hsfei_adc"]) == 0
    assert _actions(host["calls"]) == [
        ["sudo", "-n", units.ENABLE_HELPER, "--disable", "--now", "hsfei_adc"]]


def test_status_lists_deployed_and_counts_the_rest(host, capsys):
    """status shows deployed instances and counts the undeployed."""
    cli.main(["deploy", "--no-start", "--no-enable", "hsfei_adc"])
    host["active"].add("hsfei_adc")
    capsys.readouterr()
    assert cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "hsfei_adc" in out and "active" in out and "hsfei/adc" in out
    assert "hsfei_ms" not in out
    assert "2 more in the repo" in out
    cli.main(["status", "--all"])
    assert "not deployed" in capsys.readouterr().out


def test_status_verbose_shows_files_then_systemctl_status(host, capsys):
    """status -v prints each instance's files, then hands over to systemctl status."""
    cli.main(["deploy", "--no-start", "--no-enable", "fei"])
    (host["etc"] / "hsfei_ms.yaml").write_text("name: hsfei_ms\nport: /dev/ttyUSB3\n")
    host["calls"].clear()
    capsys.readouterr()
    assert cli.main(["status", "-v", "-n", "25", "fei"]) == 0
    assert _actions(host["calls"]) == [
        ["systemctl", "status", "--no-pager", "--full", "--lines=25", f"hispec@{n}.service"]
        for n in ("hsfei_adc", "hsfei_ms")]
    out = capsys.readouterr().out
    assert "hsfei/adc" in out and f"{host['etc']}/hsfei_adc.yaml\n" in out
    assert "(differs from config/hsfei/hsfei_ms.yaml)" in out


def test_status_verbose_skips_undeployed_and_reports_no_systemctl(host, monkeypatch, capsys):
    """-v covers deployed instances only, and says when systemctl cannot answer."""
    cli.main(["deploy", "--no-start", "--no-enable", "hsfei_adc"])
    host["calls"].clear()
    assert cli.main(["status", "-v", "--all"]) == 0
    assert [c[-1] for c in _actions(host["calls"])] == ["hispec@hsfei_adc.service"]

    monkeypatch.setattr(units, "run", lambda cmd, capture=False:
                        subprocess.CompletedProcess(cmd, 127, "", ""))
    capsys.readouterr()
    assert cli.main(["status", "-v"]) == 1
    assert "could not report on: hsfei_adc" in capsys.readouterr().err


def test_states_parses_systemctl_show(monkeypatch):
    """systemctl show output maps to per-instance states."""
    output = ("Id=hispec@a.service\nActiveState=failed\nUnitFileState=enabled\n"
              "StateChangeTimestamp=Tue 2026-09-22 10:00:00 HST\n\n"
              "Id=hispec@b.service\nActiveState=active\nUnitFileState=disabled\n"
              "StateChangeTimestamp=\n")
    monkeypatch.setattr(units, "run", lambda cmd, capture=False:
                        subprocess.CompletedProcess(cmd, 0, output, ""))
    got = units.states(["a", "b", "c"])
    assert got["a"] == units.UnitState("failed", "enabled", "2026-09-22 10:00:00")
    assert got["b"].running
    assert got["c"] == units.UNKNOWN
