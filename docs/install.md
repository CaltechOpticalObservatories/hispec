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

It moves the checkout to the newest release, bootstraps a pinned `uv`, runs
`uv sync --locked --all-packages` into `/opt/hispec/venv`, then hands over to
`hispec install`. That command comes from
[instrumentctl](https://github.com/CaltechOpticalObservatories/instrumentctl#host-setup),
whose README describes every step. It is shared with other instruments, so
HISPEC only supplies `src/hispec/cli/instrument.toml`.

## Releases

Hosts run a release, never whatever `main` holds. A release is an annotated
`hispec-X.Y` tag on `main`, and its message is the release notes. The tag
pins everything: hispec's own code, its submodules, and through the committed
`uv.lock` the exact commit of libby, instrumentctl and every other git
dependency. A change merged into libby therefore reaches a host only when a
hispec release locks it in.

To cut one:

1. If dependencies should move, open a PR that runs `uv lock --upgrade` and
   commits `uv.lock`, so the new commits are reviewed like any change.
2. Once it is on `main`, tag and push:

   ```bash
   git tag -a hispec-0.2 -m "What changed, for the release notes"
   git push origin hispec-0.2
   ```

`install.sh` picks the newest `hispec-*` tag. `--ref` installs something else
on purpose, a branch or an older tag, e.g. to try `main` on one host:

```bash
sudo /opt/hispec/app/systemd/install.sh --ref main
```

It refuses to move a checkout that has uncommitted edits; save them with
`hispec hotfix` first.

## Re-running it

`install.sh` is idempotent and reports only what it changes. Re-run it:

- to move the host to a new release;
- to enrol another operator: `sudo /opt/hispec/app/systemd/install.sh carol`;
- to repair anything `hispec doctor` flags.

Adding a daemon that the running release already contains does not need it:
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
