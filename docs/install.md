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

3. Install the deploy key. The lock references every extra, and the tracking
   camera repo is private, so each host needs its read-only key:

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

   Some extras come with the role. On `feiserver` the installer builds the
   tracking camera module into the venv (the `atcam` extra), which any other
   role is refused. On `feiserver` and `hispecserver` it installs atlas, the
   shared-memory and FITS viewer (the `atlas` extra), which needs a graphical
   session such as `ssh -Y`. Other extras are added with `--extra <name>` and
   recorded in `/etc/hispec/extras`, so later runs keep them; `hispec doctor`
   reports one that has gone missing.

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

By default it installs `/opt/hispec/app` as it is, edits included, and runs no
git command that changes it. It bootstraps a pinned `uv`, runs
`uv sync --locked --all-packages` into `/opt/hispec/venv` from the checkout's
`uv.lock`, then hands over to `hispec install`. That command comes from
[instrumentctl](https://github.com/CaltechOpticalObservatories/instrumentctl#host-setup),
whose README describes every step. It is shared with other instruments, so
HISPEC only supplies `src/hispec/cli/instrument.toml`.

## Updating a host

Hosts run `main`. Pulling is a separate step from installing:

```bash
git -C /opt/hispec/app pull
git -C /opt/hispec/app submodule update --init --recursive
```

`hispec update` does the same, and keeps a driver that runs an unmerged hotfix
on its branch. hispec and every driver are installed editable, so the pulled
code takes effect at the next `hispec restart <instance>`. Re-run `install.sh`
only after `pyproject.toml` or `uv.lock` changes.

`install.sh --checkout <ref>` fetches and checks out a branch or tag, with its
submodules, before installing, and refuses a checkout with uncommitted edits:

```bash
sudo /opt/hispec/app/systemd/install.sh --checkout main
```

An edit made on the host, in hispec or in a driver, is installed as it is.
Keep it with `hispec hotfix "what you fixed"`, which sends a driver edit to
the driver's own repository; see
[instrumentctl](https://github.com/CaltechOpticalObservatories/instrumentctl#hotfixes).

Dependencies move only through a PR that updates `uv.lock`, so the new commits
are reviewed like any change. libby is pinned to a release tag in
`pyproject.toml`, so moving it means changing that tag; `uv lock --upgrade`
moves the others.

## Re-running it

`install.sh` is idempotent and reports only what it changes. Re-run it:

- after a pull that changed `pyproject.toml` or `uv.lock`;
- to enrol another operator: `sudo /opt/hispec/app/systemd/install.sh carol`;
- to repair anything `hispec doctor` flags.

Adding a daemon that the checkout already contains does not need it:
`hispec deploy` covers that, with no `sudo`.

## Changing an extra's code on a host

Extras install from GitHub, so a host has no source for them to edit. To change
one on the host that runs it, clone it into `/opt/hispec/extra/`; `install.sh`
then builds that extra from the clone instead:

| Clone | Replaces | After an edit |
|---|---|---|
| `hispec-tracking-camera-instrument` | the camera module (`atcam`) | `sudo /opt/hispec/app/systemd/install.sh`, then `hispec restart hsfei_atcam` |
| `camera-interface` | the core that module builds against; only with the clone above | the same |
| `atlas` | the viewer (`atlas`), installed editable | restart `atlas` |

```bash
sudo mkdir -p /opt/hispec/extra && cd /opt/hispec/extra
# private: cloned with the host's deploy key
sudo env GIT_SSH_COMMAND="ssh -i /etc/hispec/deploy-key -o IdentitiesOnly=yes" \
  git clone git@github.com:CaltechOpticalObservatories/hispec-tracking-camera-instrument.git
sudo git clone https://github.com/CaltechOpticalObservatories/camera-interface.git
sudo git clone https://github.com/CaltechOpticalObservatories/atlas.git
sudo /opt/hispec/app/systemd/install.sh
```

Clone only what you need. `install.sh` refuses a clone for an extra this host
does not install, hands the clones to `hispec-ops` and lets operators run git in
them, and prints which local sources it used. `hispec doctor` warns while any
clone is present, with its branch and anything uncommitted or not on GitHub.

`hotfix` does not cover these. Keep a change with a commit, push and pull
request from the clone; pushing needs a GitHub account with access, since the
deploy key only reads. To go back to the GitHub build, remove the clone and
re-run `install.sh`.

## Development checkouts

Your own clone for development is separate from all of this. Build it with
`uv sync --all-packages` as the README describes, then use `uv run`. The
`PATH` entry for `/opt/hispec/venv` does not get in the way, since `uv run`
uses the project's `.venv`.
