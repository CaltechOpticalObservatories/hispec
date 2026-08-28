# HISPEC hsdev Build-Setup Playbook

Ansible playbook that automates
[`docs/build_notes/host_machine_build_notes.rst`](../docs/build_notes/host_machine_build_notes.rst):
provisioning a fresh **Ubuntu 24.04 LTS** host for HISPEC development under the
`hsdev` user.

## Layout

```
ansible/
├── ansible.cfg
├── inventory/hosts.ini          # add your target host(s) here
├── site.yml                     # entry-point playbook
└── roles/hsdev_build_setup/
    ├── defaults/main.yml        # every tunable (users, packages, hosts entries, ...)
    └── tasks/
        ├── main.yml             # imports the files below, in doc order
        ├── preflight.yml        # warn if OS != Ubuntu 24.04
        ├── users.yml            # hsdev user, hispec/instr groups, service accounts
        ├── packages.yml         # apt update + build tools + KROOT + instrument libs
        ├── python.yml           # pip packages, optional venv, version verification
        ├── directories.yml      # /home/hsdev/{external,svn}
        ├── external_libraries.yml  # optional 3rd-party build-from-source loop
        ├── hosts.yml            # /etc/hosts entries for 192.168.29.0/24
        └── services.yml         # disable cups/ModemManager/avahi/apt-daily
```

## Usage

1. Add your target host(s) to `inventory/hosts.ini`:

   ```ini
   [hsdev_hosts]
   hispec-devbox ansible_host=192.168.29.50 ansible_user=ubuntu
   ```

2. Run it:

   ```bash
   cd ansible
   ansible-playbook site.yml -K   # -K prompts for the sudo/become password
   ```

3. Everything is tagged, so you can run a subset, e.g.:

   ```bash
   ansible-playbook site.yml --tags packages,python -K
   ansible-playbook site.yml --tags hosts -K
   ```

   Available tags: `preflight`, `users`, `groups`, `packages`, `kroot`,
   `instrument`, `python`, `venv`, `directories`, `external`, `hosts`,
   `services`, `verify`.

## Variables worth knowing about

All defaults live in `roles/hsdev_build_setup/defaults/main.yml` and can be
overridden with `-e`, `group_vars/`, or `host_vars/`.

- `hispec_install_kroot_packages` / `hispec_install_instrument_packages`
  (default `true`) — the source doc marks these two package sets as separate,
  situational subsections; set to `false` to skip either.
- `hispec_create_venv` (default `false`) — the doc's "Optional: Virtual
  Environment" section. When enabled, creates `hispec_venv_path`
  (`/home/hsdev/env` by default) for the `hsdev` user instead of/in addition
  to the system-wide install.
- `hispec_external_libraries` (default `[]`) — the doc's "External Development
  Libraries" section is a generic `wget http://example.com/3rdparty.tar.gz`
  example, not a real package, so nothing is hardcoded here. Populate it to
  fetch/build/install real third-party sources under `/home/hsdev/external`:

  ```yaml
  hispec_external_libraries:
    - name: 3rdparty
      url: https://example.org/3rdparty-1.2.3.tar.gz
      configure_opts: ""
  ```

- `hispec_hosts_entries` — the `192.168.29.x` private-network host list,
  applied to `/etc/hosts` inside a marked, idempotent block.
- `hispec_services_to_disable` — units disabled for headless/dev hosts.

## Notes / caveats

- **PEP 668 (externally-managed environment):** Ubuntu 24.04's system Python
  refuses plain `pip install` by default. The doc's system-wide
  `python3 -m pip install ...` step is reproduced with
  `--break-system-packages` (controlled by `hispec_pip_break_system_packages`,
  default `true`) so the playbook actually succeeds out of the box. If you'd
  rather keep the system interpreter untouched, set that to `false` and turn
  on `hispec_create_venv: true` instead.
- **User creation sets no passwords.** Accounts (`hsdev`, `hispec`,
  `hispecbld`, `hispeceng`, `hispecrun`, `hispec1`-`hispec9`) are created
  locked, matching `adduser`'s "no password yet" state before you interactively
  set one. Provision SSH keys or vault-managed password hashes separately.
- **The `hispec` group/user name collision is intentional and handled.** The
  doc creates a `hispec` *group* first, then later a `hispec` *user*. The
  `hispec` user task explicitly reuses the pre-existing `hispec` group as its
  primary group — without that, `useradd` would fail trying to create a
  second, conflicting group of the same name.
- **Service-disable tasks check the unit exists first**, so the playbook
  doesn't fail on minimal server images that never installed `cups` or
  `ModemManager` in the first place.
- Package name spelling (e.g. `lib32c-dev`) is copied verbatim from the build
  notes and hasn't been independently re-verified against Ubuntu 24.04's
  repos — if `apt` rejects a name, fix it in the source `.rst` and here.
