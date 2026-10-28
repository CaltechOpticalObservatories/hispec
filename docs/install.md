# Installing HISPEC on a host

This is the one way to put the HISPEC software on an instrument host. It is a
root job for whoever administers the machine; operators never need it to
deploy, start or debug daemons. The host-specific build notes
({doc}`build_notes/host_machine_build_notes`, {doc}`build_notes/FEI_build/index`)
cover the OS, packages and hardware, and link back here for the software.

## What you end up with

| Path | What it is |
| --- | --- |
| `/opt/hispec/app` | the hispec checkout the daemons run from |
| `/opt/hispec/venv` | the virtualenv, built by `uv` from that checkout |
| `/etc/hispec` | deployed configs and instance files, plus `secrets.env` and the host role |
| `/var/log/hispec` | the daemons' own log files |

The daemons run as the unprivileged `hispec` system account. People log in as
themselves (or the shared `hsdev`) and are members of `hispec-ops`, which owns
`/opt/hispec` and `/etc/hispec`. Members can pull, hotfix, sync the venv,
edit configs and start or stop daemons without `sudo`. A default ACL keeps
files added later group-writable, whatever the creator's umask.

`secrets.env` and the GitHub token stay root-owned, and `/var/log/hispec` is
written only by the daemons.

The venv's `bin` is on every login shell's `PATH`, set by
`/etc/profile.d/hispec.sh`, so `python`, `libby` and `hispec` work without
activating anything.

## Install

1. Prerequisites. The OS packages in the build notes, plus:

   ```bash
   sudo apt install -y acl git curl
   ```

2. Clone, with submodules:

   ```bash
   sudo git clone --recurse-submodules \
       https://github.com/CaltechOpticalObservatories/hispec.git /opt/hispec/app
   ```

3. Install the deploy key. `uv lock` reads every extra on every host, and the
   tracking camera repo is private, so each host needs its read-only key:

   ```bash
   sudo install -D -m 600 -o root -g root <deploy-key> /etc/hispec/deploy-key
   ```

   The key is generated once and registered as a read-only deploy key on
   `hispec-tracking-camera-instrument`; every host gets a copy of the same
   private half.

4. Run the installer, naming every account that operates this host:

   ```bash
   sudo /opt/hispec/app/systemd/install.sh hsdev alice bob --host-role <role>
   ```

   `--host-role` is the name instance files use in `HISPEC_HOST`
   (`hispecserver`, `feiserver`, ...). Leave it out to use the short hostname.
   It is written once, to `/etc/hispec/host`; edit that file to change it.

   On `feiserver` the installer also builds the tracking camera module into
   the venv (the `atcam` extra); any other role is refused it. Other extras
   are added with `--extra <name>` and recorded in `/etc/hispec/extras`, so
   later runs keep them; `hispec doctor` reports one that has gone missing.

   Before `hispec deploy hsfei_atcam` on `feiserver`, put the ACF at
   `/etc/hispec/hispecatc.acf` and create `/opt/hispec/data` writable by
   `hispec`. The daemon holds the Archon, so nothing else can drive the camera
   while it runs.

5. Log out and back in, so the new groups and `PATH` take effect.

6. Add the credentials this host's daemons need:

   ```bash
   $EDITOR /etc/hispec/secrets.env
   ```

   [Secrets](operations/systemd.md#secrets) lists the variables.
   `hispec doctor` says which are still missing.

7. Check the host:

   ```bash
   hispec doctor
   ```

8. Deploy and start daemons, as yourself:
   {doc}`operations/systemd` from here on.

## What install.sh does

It bootstraps a pinned `uv`, runs `uv lock --upgrade` and
`uv sync --all-packages` into `/opt/hispec/venv`, then hands over to
`hispec install`. That command comes from
[instrumentctl](https://github.com/CaltechOpticalObservatories/instrumentctl#host-setup),
whose README describes every step. It is shared with other instruments, so
HISPEC only supplies `src/hispec/cli/instrument.toml`.

## Re-running it

`install.sh` is idempotent and reports only what it changes. Re-run it:

- to enrol another operator: `sudo /opt/hispec/app/systemd/install.sh carol`;
- after a pull that changed dependencies, or to pick up merged libby fixes,
  since the lock is refreshed each run;
- to repair anything `hispec doctor` flags.

Neither adding a daemon nor picking up code changes needs it. A
`git -C /opt/hispec/app pull` followed by `hispec deploy` or `hispec restart`
covers both, with no `sudo`.

## Development checkouts

Your own clone for development is separate from all of this. Build it with
`uv sync --all-packages` as the README describes, then use `uv run`. The
`PATH` entry for `/opt/hispec/venv` does not get in the way, since `uv run`
uses the project's `.venv`.
