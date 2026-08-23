==============================================================
HISPEC RTC Build: Headless Real-time Ubuntu 24.04 FEI Server
==============================================================

:Authors: Elijah A-B, Dan Ech
:Date: 2026-08-22
:Hostname: ``hispecfei``
:Primary User: ``hsfei``
:Engineering User: ``hsdev``
:OS: Real-time Ubuntu 24.04 LTS (PREEMPT_RT via Ubuntu Pro)
:Supersedes: ``fei_server_build_notes.rst``, ``rtc_buildnote.rst``

.. contents:: Table of Contents
   :depth: 2
   :local:

----

0. Scope & Design Principles
============================

This document merges the FEI server build notes and the TCC / real-time kernel
build notes into a single **headless RTC** recipe.

The OS is **Real-time Ubuntu 24.04 LTS** — Ubuntu with Canonical's
``PREEMPT_RT`` kernel, deployed through an **Ubuntu Pro** subscription
(§5). This is a genuine real-time operating system, not a tuned generic
kernel: ``PREEMPT_RT`` replaces the default scheduler with a fully preemptible
priority-based one, converts spinlocks to sleeping rt-mutexes with priority
inheritance, and forces IRQ handlers into schedulable kernel threads. It
provides a bounded upper limit on execution time.

What "RTC" scopes here: a COTS ``x86_64`` server running that RT kernel with
hard CPU shielding, Intel TCC enabled in firmware, and background services
stripped — dedicated to the camera/controller loop.

.. note::
   Real-time Ubuntu 24.04 is based on upstream kernel v6.8 with the
   ``PREEMPT_RT`` patchset applied, on ``amd64`` and ``arm64``. Ubuntu Pro is
   free for personal and small-scale commercial use on up to 5 machines;
   Caltech/COO deployments should use the institutional subscription.

Design rules applied throughout:

#. **The RT kernel is the foundation, not an optimization.** Every tuning step
   in §6, §7 and §12 assumes ``PREEMPT_RT`` is already running. Do not treat
   §5 as optional.
#. **No desktop environment.** Ubuntu **Server** 24.04.1 LTS, no GNOME, no
   display manager, no snaps beyond the base set.
#. **Install only what the instrument needs.** Every package group below is
   justified; anything GUI-only that the instrument does not require was cut.
#. **GUIs still work — remotely.** X11 is *not* run locally. Instead the box
   exports GUIs over SSH X11 forwarding and a pinned TigerVNC session
   (:ref:`section-remote-gui`). Plots and images are produced headlessly and
   pulled off the machine as files.
#. **Nothing runs on shielded cores except instrument code.** Shell sessions,
   VNC, and services are confined to housekeeping cores.

.. note::
   ``$`` prompts are omitted. Unless a block says otherwise, run as ``hsfei``
   with ``sudo``. Steps marked **[reboot]** require a restart before continuing.

----

1. Prerequisites & Media Preparation
====================================

All drives are erased before starting — this is a **0% → 100%** build.

USB Drive A: Ubuntu Installer
-----------------------------

* **OS:** Ubuntu **Server** 24.04.1 LTS (``.iso``, not Desktop)
* **Source:** official Ubuntu download
* **Format:** bootable ISO (``dd`` / Rufus / balenaEtcher)

USB Drive B: Cloud-Init (CIDATA)
--------------------------------

* **Format:** FAT32
* **Volume label:** ``CIDATA`` (exact, uppercase — the installer matches on it)
* **Required files, in the root directory:**

  * ``user-data`` — YAML autoinstall configuration
  * ``meta-data`` — empty file, but it *must* exist or the boot check fails

.. warning::
   On the previous build the automated cloud-init install failed and the
   **manual installer path was used instead**. Prepare Drive B, but expect to
   fall back to the manual walkthrough in :ref:`section-os-install`. Do not
   burn schedule time debugging autoinstall on a one-off machine.

Target Hardware Inventory
-------------------------

Record these before install; several later steps depend on them.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Item
     - Value / How to obtain
   * - CPU physical core count
     - ``lscpu | grep -E '^Core|^Socket'`` — needed for core shielding
   * - Boot / OS drive
     - Samsung 990 Pro 1 TB (NVMe)
   * - Data drive(s)
     - 2 TB — RAID 1 pending (:ref:`section-pending`)
   * - Management NIC
     - ``ip -br link`` — the interface carrying ``192.168.29.0/24``
   * - Archon fiber NIC
     - e.g. ``enp202s0f0np0`` — the port physically labelled **archon**
   * - FT4222 SPI board
     - ``lsusb`` → ``0403:601c``

----

.. _section-os-install:

2. OS Installation (Ubuntu Server 24.04.1)
==========================================

Installation Parameters
-----------------------

* **Language / Keyboard:** English
* **Networking:** Ethernet connected, **no proxy**. Leave DHCP for now; the
  static addresses are applied in :ref:`section-network`.
* **Mirror:** ``http://us.archive.ubuntu.com/ubuntu/`` (default)
* **Server profile:** minimized install — **decline** the "Featured Server
  Snaps" list entirely.
* **OpenSSH:** **Install it.** This is a headless machine; without ``sshd`` the
  build stops here.

.. important::
   The old FEI note selected the default "Popular Snaps". For the pseudo-RTC,
   select **none**. ``snapd`` timers are a jitter source and are disabled in
   :ref:`section-services`.

Storage Configuration
---------------------

* **Primary drive:** Samsung 990 Pro (1 TB) — root filesystem
* **Secondary 2 TB drive:** formatted ``ext4``, mounted at ``/usr``
  *(carried over from the previous build)*
* **Software RAID 1:** bypassed at install time — see :ref:`section-pending`

.. warning::
   Mounting a separate device at ``/usr`` requires the initramfs to mount it
   before ``switch_root``. It works on 24.04, but it is a non-standard layout.
   If the RAID rebuild in :ref:`section-pending` gives you an excuse to
   re-partition, prefer keeping ``/usr`` on root and mounting the 2 TB drive at
   ``/data`` or ``/srv``.

Credentials
-----------

* **Server name:** ``hispecfei``
* **Primary user created at install:** ``hsfei`` (gets ``sudo``)
* **Password:** set during installation — **not documented here**

First Boot
----------

.. code-block:: bash

   sudo apt update && sudo apt upgrade -y

----

3. Identity: Hostname, Users, Groups
====================================

Hostname
--------

.. code-block:: bash

   sudo hostnamectl set-hostname hispecfei

Map the loopback alias in ``/etc/hosts``:

.. code-block:: text

   127.0.1.1   hispecfei

Verify:

.. code-block:: bash

   hostnamectl

Groups
------

.. code-block:: bash

   sudo groupadd -f hispecfei     # instrument / deployment group
   sudo groupadd -f eng           # engineering read+write on /opt

Engineering User
----------------

``hsfei`` is the primary account created at install. ``hsdev`` is the
engineering/development account used for day-to-day work and owns the hardware
device nodes.

.. code-block:: bash

   sudo adduser hsdev
   sudo usermod -aG sudo,dialout,hispecfei,eng hsdev
   sudo usermod -aG dialout,hispecfei,eng hsfei

Idempotent re-run (safe on an already-provisioned box — skips existing accounts):

.. code-block:: bash

   for u in hsfei hsdev; do
       sudo useradd -m -s /bin/bash "$u" 2>/dev/null || true
   done

.. note::
   * The new hostname takes full effect on reboot.
   * ``usermod`` group changes require a logout/login. To pick up ``dialout``
     in the current shell only: ``newgrp dialout``.
   * Confirm with ``id hsdev`` before troubleshooting any permission error.

SSH Keys (headless requirement)
-------------------------------

Install your public key for both accounts *before* you rely on the machine
being remote-only:

.. code-block:: bash

   ssh-copy-id hsfei@hispecfei
   ssh-copy-id hsdev@hispecfei

Then harden ``/etc/ssh/sshd_config``:

.. code-block:: text

   PasswordAuthentication no
   PermitRootLogin no
   X11Forwarding yes
   X11UseLocalhost yes

.. code-block:: bash

   sudo systemctl restart ssh

``X11Forwarding yes`` is what makes :ref:`section-remote-gui` work — do not
omit it while stripping the desktop.

----

.. _section-network:

4. Network Configuration (Headless / netplan)
=============================================

There is no GUI network panel on a server install. Both interfaces are
configured declaratively in netplan.

Create ``/etc/netplan/01-hispecfei.yaml``:

.. code-block:: yaml

   network:
     version: 2
     renderer: networkd
     ethernets:
       # --- Management / site network ---
       MGMT_IFACE:
         dhcp4: no
         addresses: [192.168.29.107/24]
         routes:
           - to: default
             via: 192.168.29.1
         nameservers:
           addresses: [8.8.8.8, 1.1.1.1]

       # --- Archon fiber link (isolated, no gateway) ---
       enp202s0f0np0:
         dhcp4: no
         addresses: [10.0.0.10/24]
         mtu: 9000

Replace ``MGMT_IFACE`` with the real name from ``ip -br link``. Apply:

.. code-block:: bash

   sudo chmod 600 /etc/netplan/01-hispecfei.yaml
   sudo netplan try            # auto-reverts in 120 s if you lose the link
   sudo netplan apply

.. warning::
   Use ``netplan try`` first. On a headless box a bad netplan file with no
   console access means a physical trip to the machine.

Archon Host Entry
-----------------

Add to ``/etc/hosts``:

.. code-block:: text

   10.0.0.2    archon

Connect the Archon to the fiber port labelled **archon** and verify:

.. code-block:: bash

   ping -c 3 archon
   ip -br addr show enp202s0f0np0

Refer to ``archongui.rst`` for Archon-side configuration.

.. note::
   The ``10.0.0.0/24`` Archon link carries no default route on purpose. Keep
   instrument traffic off the management network.

----

5. Deploy the Real-Time OS (Real-time Ubuntu)
=============================================

This is the step that makes the machine an RTC. Everything after it is tuning.

5.1 What You Get
----------------

Canonical's ``realtime-kernel`` is Ubuntu 24.04 with the upstream
``PREEMPT_RT`` patchset on kernel v6.8:

* **Fully preemptible kernel** — priority-based scheduling replaces the default
  CFS behaviour for RT tasks; kernel code itself becomes preemptible.
* **Threaded IRQ handlers** — hardware interrupts run as schedulable kernel
  threads that an RT task can preempt, rather than blocking arbitrarily.
* **Priority inheritance rt-mutexes** — spinlocks become sleeping locks with PI,
  bounding priority inversion.
* **High-resolution timers** — precise wakeups instead of tick-granular ones.

The practical result is a *bounded worst-case* latency, which is the property
the camera loop needs. Throughput is slightly lower than the generic kernel —
that trade is intentional.

5.2 Attach Ubuntu Pro
---------------------

The RT kernel is delivered only through Ubuntu Pro (``elijahab`` account).

.. code-block:: bash

   sudo pro attach          # interactive - prompts for the token
   pro status

.. warning::
   Do **not** paste the Pro token into this document, a script, or shell
   history. Run ``sudo pro attach`` with no argument so it prompts, or use
   ``HISTCONTROL=ignorespace`` with a leading space. If a token has ever been
   echoed into a shared file, rotate it.

5.3 Choose the Kernel Variant
-----------------------------

Two variants matter here. **Pick before enabling** — switching later means
another kernel install and reboot.

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Variant
     - Use when
   * - *(default)*
     - Generic ``PREEMPT_RT`` for ``amd64``/``arm64``. Vendor-neutral.
   * - ``intel-iotg``
     - Intel platform, and you want Intel **TCC** and **TSN** support built in.
       Validated on Intel Atom® X6000E and 11th/12th/13th Gen Intel® Core™.

.. important::
   **This build enables TCC Mode in BIOS (§6), so ``intel-iotg`` is very likely
   the correct variant.** The Intel-optimized kernel is what carries the TCC and
   TSN enablement; on the generic RT kernel you get the firmware-level TCC
   benefits but not the kernel-side feature support.

   Confirm the CPU generation against the supported list before committing::

      lscpu | grep -i 'model name'

List what your Pro subscription actually offers, then enable:

.. code-block:: bash

   # Generic real-time kernel
   sudo pro enable realtime-kernel

   # -- OR -- Intel IOTG optimized (TCC / TSN enabled)
   sudo pro enable realtime-kernel --variant=intel-iotg

Accept the prompt to install and switch the default boot kernel.

.. note::
   The variant flag is only accepted at *enable* time. To change variants
   afterwards, ``sudo pro disable realtime-kernel`` first.

5.4 Verify **[reboot]**
-----------------------

.. code-block:: bash

   sudo reboot

   # After boot:
   uname -a                     # expect PREEMPT_RT (and -realtime flavour)
   uname -r
   pro status | grep realtime   # expect: realtime-kernel   enabled
   cat /sys/kernel/realtime 2>/dev/null   # expect: 1

Confirm the RT scheduling classes are live:

.. code-block:: bash

   chrt -m                      # SCHED_FIFO / SCHED_RR priority ranges
   grep -c . /proc/pressure/cpu # PSI available

.. warning::
   **Record ``uname -r`` in the as-built log now.** Out-of-tree drivers
   (FT4222 helpers, any DKMS module) are built against a specific kernel. When
   Pro ships an RT kernel update, those modules must be rebuilt and the
   ``cyclictest`` baseline (§13) re-measured before the machine goes back on
   sky.

.. tip::
   To roll back to the generic kernel for debugging, see Canonical's
   `switch from real-time to generic kernel
   <https://documentation.ubuntu.com/real-time/latest/how-to/switch-from-realtime-to-generic-kernel/>`_.
   Keep a generic kernel entry in the GRUB menu as an escape hatch.

----

6. CPU Shielding, GRUB & TCC
============================

.. _section-grub:

GRUB Kernel Parameters
----------------------

Six cores (**0–5**) are shielded from the OS scheduler, RCU callbacks and the
timer tick. Edit ``/etc/default/grub``:

.. code-block:: text

   GRUB_CMDLINE_LINUX_DEFAULT="quiet clocksource=tsc tsc=reliable nmi_watchdog=0 nosoftlockup isolcpus=domain,0-5 rcu_nocbs=0-5 nohz_full=0-5 irqaffinity=6-15 kthread_cpus=6-15"

Adjust ``6-15`` to your actual housekeeping range —
``cat /sys/devices/system/cpu/present`` gives the total.

Parameter rationale:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Parameter
     - Purpose
   * - ``clocksource=tsc tsc=reliable``
     - Pin to the TSC; avoids HPET/ACPI read latency spikes
   * - ``nmi_watchdog=0``
     - Removes periodic NMI perf interrupts
   * - ``nosoftlockup``
     - Suppresses soft-lockup warnings from long RT bursts
   * - ``isolcpus=domain,0-5``
     - Removes cores 0–5 from all scheduling domains
   * - ``rcu_nocbs=0-5``
     - Offloads RCU callbacks off the isolated cores
   * - ``nohz_full=0-5``
     - Stops the 1 kHz tick when one task is runnable
   * - ``irqaffinity=6-15``
     - Directs all hardware IRQs to housekeeping cores — **corrected, see below**
   * - ``kthread_cpus=6-15``
     - Restricts kernel threads to housekeeping cores

.. warning::
   **``irqaffinity=0`` in the original RTC note is a copy-paste bug — corrected
   above.**

   Canonical's Intel TCC tutorial uses ``isolcpus=3 … irqaffinity=0``: core 3 is
   isolated and IRQs are sent to core **0**, which is a *housekeeping* core.
   The original note copied that line but widened the isolated set to ``0-5``
   while leaving ``irqaffinity=0`` unchanged — which now points every hardware
   interrupt **into** the shielded set, at the one core the RT threads most
   depend on.

   The rule is simply that the ``irqaffinity`` range and the ``isolcpus`` range
   must not overlap. Canonical states this directly: *"isolate one or more CPUs
   to run the real-time application and the others to handle the IRQs and
   kthreads."*

.. note::
   ``splash`` was also dropped from the original line — it is meaningless on a
   headless server.

Apply and reboot:

.. code-block:: bash

   sudo update-grub
   sudo reboot    # [reboot]

Verify after boot:

.. code-block:: bash

   cat /proc/cmdline
   cat /sys/devices/system/cpu/isolated       # expect 0-5
   cat /sys/devices/system/cpu/nohz_full      # expect 0-5
   cat /sys/devices/system/cpu/present        # total core count

Confirm no IRQ is still bound to a shielded core:

.. code-block:: bash

   # Any line showing only cores 0-5 in the affinity list is a problem
   for i in /proc/irq/[0-9]*; do
       printf '%-8s %s\n' "$(basename "$i")" "$(cat "$i"/smp_affinity_list 2>/dev/null)"
   done | sort -k2

Stray IRQs can be re-pointed at runtime (not persistent across reboot):

.. code-block:: bash

   echo 6-15 | sudo tee /proc/irq/<IRQ-NUMBER>/smp_affinity_list

.. warning::
   Never set an IRQ's affinity mask to zero — every IRQ must be handled by at
   least one CPU.

Disable irqbalance
------------------

``irqbalance`` actively redistributes interrupts across all cores at runtime,
which silently undoes the ``irqaffinity`` boot parameter. It must be off.

.. code-block:: bash

   sudo systemctl disable --now irqbalance
   systemctl status irqbalance

Confine systemd Services to Housekeeping Cores
----------------------------------------------

Set a global default affinity so every systemd-managed service — present and
future — stays off the shielded cores. Edit ``/etc/systemd/system.conf``:

.. code-block:: ini

   [Manager]
   CPUAffinity=6-15

.. code-block:: bash

   sudo systemctl daemon-reexec     # or reboot

This is broader and more reliable than per-unit ``CPUAffinity=``, and it covers
the VNC unit in §10.3 automatically. Keep the per-unit setting anyway as
defence in depth.

BIOS Configuration Checklist
----------------------------

#. Reboot and enter BIOS (``F2``, ``Del``, or ``Esc``).
#. **Hyper-Threading / SMT / Logical Processors → Disabled.**
   Deterministic execution requires one thread per physical core.
#. **TCC Mode → Enabled.** On Intel reference BIOS this lives under
   *Intel® Advanced Menu ‣ Time Coordinated Computing*. If the option is not
   present, the board vendor may have hidden it — consult the vendor or set the
   underlying options manually per Intel's TCC User Guide.
#. **Perform a double reboot** — TCC settings are not fully applied until the
   second POST.

.. note::
   **TCC Mode subsumes the manual C-state work.** Enabling it disables C-states
   and their sub-options, and optimizes power-state and frequency-transition
   handling. Canonical measured average scheduling jitter dropping from ~100 µs
   to sub-10 µs on an isolated core purely from this one firmware knob.

   The mechanism matters for this instrument: an isolated core running a
   periodic task that finishes early *idles* for the remainder of the cycle,
   and the Linux idle subsystem then drops it into a deep C-state with a long
   exit latency. That exit latency is the jitter. If TCC Mode is unavailable on
   this board, disable C-states below C1 manually and set the power profile to
   *Maximum Performance*.

Inspect C-state configuration from the OS:

.. code-block:: bash

   for cpu in /sys/devices/system/cpu/cpu*/cpuidle/state*; do
       echo -n "$cpu: "; cat "$cpu"/name
       echo -n "  Target residency: "; cat "$cpu"/residency
       echo -n "  Exit latency: ";     cat "$cpu"/latency
       echo -n "  Disabled [1=yes]: "; cat "$cpu"/disable
   done

Further Intel Optimizations (optional)
--------------------------------------

If the ``cyclictest`` baseline in §13 is not tight enough, two further Intel
features are worth evaluating:

* **Cache Allocation Technology (CAT)** — partitions last-level cache so
  best-effort workloads on housekeeping cores cannot evict the RT task's
  working set. Directly relevant when large frame buffers move through the
  machine.
* **Speed Shift / HWP** — tunes frequency-transition responsiveness on the
  isolated cores.

See Canonical's `Optimizing real-time performance on Intel CPUs
<https://documentation.ubuntu.com/real-time/latest/tutorial/intel-tcc/>`_
tutorial.

.. tip::
   With shielding active, pin instrument threads to cores 0–5 using ``taskset``,
   ``chrt``, ``cset``, or the codebase's own affinity settings. Nothing lands
   there automatically.

----

.. _section-services:

7. Service Stripping
====================

Disable background daemons, timers and update machinery. On a headless server
several of these may already be absent — ``|| true`` keeps the block
copy-pasteable.

.. code-block:: bash

   for svc in \
       irqbalance.service \
       cups.service cups-browsed.service \
       ModemManager.service \
       avahi-daemon.service avahi-daemon.socket \
       bluetooth.service \
       apt-daily.timer apt-daily-upgrade.timer \
       unattended-upgrades.service \
       motd-news.timer \
       snapd.service snapd.socket snapd.seeded.service \
       fwupd-refresh.timer \
       man-db.timer \
       systemd-oomd.service
   do
       sudo systemctl disable --now "$svc" 2>/dev/null || true
   done

Also disable the periodic locate/tracker indexers if present:

.. code-block:: bash

   sudo systemctl disable --now plocate-updatedb.timer 2>/dev/null || true

Audit what is left:

.. code-block:: bash

   systemctl list-units --type=service --state=running
   systemctl list-timers --all

.. warning::
   Disabling ``unattended-upgrades`` means **security patching is now manual**.
   Schedule a maintenance window; do not simply forget about it.

.. note::
   Keep ``ssh``, ``systemd-networkd``, ``systemd-timesyncd`` (or ``chrony``),
   and ``ubuntu-advantage`` enabled. Losing SSH on a headless RTC is the one
   unrecoverable mistake in this document.

----

8. System Packages
==================

8.1 Core Build & Runtime (required)
-----------------------------------

.. code-block:: bash

   sudo apt update
   sudo apt install -y \
       build-essential \
       cmake \
       git \
       pkg-config \
       software-properties-common \
       wget curl \
       net-tools iproute2 \
       htop \
       tmux \
       rsync \
       libffi-dev libssl-dev zlib1g-dev libbz2-dev liblzma-dev \
       libreadline-dev libsqlite3-dev libncursesw5-dev \
       libxml2-dev libxmlsec1-dev xz-utils llvm \
       python3-pip python3-dev python3-venv \
       libboost-all-dev \
       libcfitsio-dev libccfits-dev \
       libopencv-dev \
       libzmq3-dev

8.2 Real-Time Tooling (required)
--------------------------------

.. code-block:: bash

   sudo apt install -y \
       cset \
       util-linux \
       rt-tests \
       linuxptp \
       stress-ng

``rt-tests`` provides ``cyclictest``, used in :ref:`section-verify`.

8.3 Headless GUI Export (required — see :ref:`section-remote-gui`)
------------------------------------------------------------------

Minimal X client libraries and a lightweight window manager. **No display
manager, no desktop environment.**

.. code-block:: bash

   sudo apt install -y \
       xauth x11-apps x11-utils \
       tigervnc-standalone-server tigervnc-common \
       openbox \
       xterm \
       fonts-dejavu-core

.. note::
   ``xauth`` is the package people forget. Without it ``ssh -X`` silently fails
   to set ``$DISPLAY`` and every remote GUI attempt dies with
   ``cannot open display``.

8.4 Qt Runtime (only if instrument GUIs are Qt-based)
-----------------------------------------------------

Install **only** if a tool you actually run on this machine needs Qt. Prefer
running Qt GUIs on an operator workstation.

.. code-block:: bash

   sudo apt install -y \
       python3-pyqt5 \
       qtbase5-dev qtbase5-dev-tools \
       libxcb-xinerama0 libxkbcommon-x11-0

.. warning::
   ``qt5-default`` **does not exist** on Ubuntu 24.04 (removed after 20.04).
   The old FEI troubleshooting note recommending it is obsolete — use
   ``qtbase5-dev`` and set ``QT_SELECT=5`` if a legacy build script demands it.

8.5 KROOT / Keck Environment (optional, machine-dependent)
----------------------------------------------------------

Skip this on a pure pseudo-RTC. Install only if this box must build KROOT.
This pulls in a large Tcl/Tk/Motif/X toolchain that is otherwise dead weight.

.. code-block:: bash

   sudo apt install -y \
       openconnect \
       subversion cvs at \
       python-dev-is-python3 python3-docutils \
       libxt-dev libxml2-dev libncurses-dev \
       tcl tcl-dev tcl-thread tcllib tk tk-dev expect \
       tclx tcl-fitstcl libpq-dev \
       g++ gfortran \
       libboost-dev libboost-system-dev libboost-filesystem-dev \
       python3-tk python3-pil.imagetk \
       libpam-dev \
       pandoc groff rst2pdf \
       python3-ephem \
       pyqt5-dev-tools \
       make m4 autoconf \
       xorg-dev xaw3dg-dev \
       libmotif-dev \
       libc6-dev-i386 \
       snmp \
       flex flex-doc bison bison-doc

----

9. Python Environment
=====================

Global Shared Virtual Environment
---------------------------------

A centralized deployment environment at ``/opt/hispecfei/env`` — owned by
``hsfei``, group-writable by ``eng``. Python **3.12** ships with 24.04 and is
the required version.

Run as ``hsfei``:

.. code-block:: bash

   sudo mkdir -p /opt/hispecfei
   sudo python3 -m venv /opt/hispecfei/env

   # Ownership: primary user hsfei, engineering group eng
   sudo chown -R hsfei:eng /opt/hispecfei
   sudo chmod -R 775 /opt/hispecfei
   sudo chmod g+s /opt/hispecfei          # new files inherit the eng group

   /opt/hispecfei/env/bin/pip install --upgrade pip setuptools wheel
   /opt/hispecfei/env/bin/pip install \
       numpy \
       scipy \
       matplotlib \
       astropy \
       pandas \
       pyserial \
       pipython \
       pyzmq

.. warning::
   Two corrections against the original FEI package list:

   * ``serial`` is the **wrong** PyPI package — it is an unrelated project.
     The Physik Instrumente / device-comms package you want is ``pyserial``
     (imported as ``import serial``).
   * ``cmake`` was listed as a pip install. CMake is already installed via
     ``apt`` in §8.1; installing it again via pip creates two versions on
     ``PATH`` and shadows the system one. Dropped.

   ``PyQt5`` is also dropped from the global env — install it via ``apt``
   (§8.4) only if Qt GUIs actually run here.

Activate by default for engineering shells:

.. code-block:: bash

   echo 'source /opt/hispecfei/env/bin/activate' >> /home/hsdev/.bashrc
   echo 'source /opt/hispecfei/env/bin/activate' >> /home/hsfei/.bashrc

Headless Matplotlib
-------------------

There is no local display. Force the non-interactive backend system-wide so
plotting scripts never block or crash on ``$DISPLAY``:

.. code-block:: bash

   sudo tee /etc/profile.d/mpl-headless.sh > /dev/null <<'EOF'
   export MPLBACKEND=Agg
   EOF

Scripts then write figures to disk and you retrieve them per
:ref:`section-remote-gui`. Override interactively when tunnelling a GUI:
``MPLBACKEND=Qt5Agg python plot.py``.

Local Engineer Virtual Environments
-----------------------------------

**Option A — inherit the deployed global packages:**

.. code-block:: bash

   python3 -m venv --system-site-packages ~/fei-venv
   source ~/fei-venv/bin/activate

**Option B — fully isolated sandbox:**

.. code-block:: bash

   python3 -m venv ~/fei-venv_sandbox
   source ~/fei-venv_sandbox/bin/activate
   pip install --upgrade pip

.. note::
   Never ``pip install`` into ``/opt/hispecfei/env`` for experimental work.
   That environment is the deployed baseline — use Option A or B.

----

.. _section-remote-gui:

10. Remote GUI, Plots & Image Export
====================================

The machine is headless. Three complementary paths get pixels off it, in
increasing order of weight. **Prefer the lightest one that does the job.**

10.1 Files First (preferred)
----------------------------

For plots, FITS previews and diagnostics, write files and pull them down. No
X server, no VNC, zero jitter on the RT cores.

.. code-block:: bash

   # From your workstation
   rsync -avz hsdev@hispecfei:/data/plots/ ./plots/
   scp hsdev@hispecfei:/data/frames/latest.fits .

Or serve a directory read-only over an SSH tunnel:

.. code-block:: bash

   # On hispecfei (bind to loopback only)
   cd /data/plots && python3 -m http.server 8000 --bind 127.0.0.1

   # On your workstation
   ssh -L 8000:localhost:8000 hsdev@hispecfei
   # then browse http://localhost:8000

.. note::
   Binding to ``127.0.0.1`` and reaching it through the SSH tunnel keeps the
   server off the site network. Do not bind ``0.0.0.0``.

10.2 SSH X11 Forwarding (single applications)
---------------------------------------------

For one-off Qt/Tk tools, forward the individual window — no persistent desktop.

Requires ``X11Forwarding yes`` (§3) and ``xauth`` (§8.3) on the server, and an
X server on the client (native on Linux, XQuartz on macOS, VcXsrv/MobaXterm on
Windows).

.. code-block:: bash

   # From your workstation
   ssh -X hsdev@hispecfei
   xeyes                      # smoke test
   xdpyinfo | head            # confirms the forwarded display

   # -Y (trusted) only if -X trips an extension error, and only on a trusted LAN
   ssh -Y hsdev@hispecfei

.. tip::
   X11 forwarding is chatty over high-latency links. For anything that redraws
   continuously, use VNC (§10.3) instead — it compresses far better.

10.3 TigerVNC Session (persistent desktop)
------------------------------------------

For a session that survives disconnect — long-running Archon GUIs, alignment
tools, multi-window work.

**Set the VNC password** (as ``hsdev``):

.. code-block:: bash

   vncpasswd

**Configure a minimal Openbox session** in ``~/.vnc/xstartup``:

.. code-block:: bash

   mkdir -p ~/.vnc
   cat > ~/.vnc/xstartup <<'EOF'
   #!/bin/sh
   unset SESSION_MANAGER
   unset DBUS_SESSION_BUS_ADDRESS
   export MPLBACKEND=Qt5Agg
   exec openbox-session
   EOF
   chmod +x ~/.vnc/xstartup

**Start the server, pinned off the shielded cores.** This is the critical RTC
detail — VNC must never run on cores 0–5:

.. code-block:: bash

   # Adjust 6-15 to your housekeeping core range
   taskset -c 6-15 vncserver :1 \
       -localhost yes \
       -geometry 1920x1080 \
       -depth 24

``-localhost yes`` binds VNC to loopback only. Reach it through an SSH tunnel:

.. code-block:: bash

   # On your workstation
   ssh -L 5901:localhost:5901 hsdev@hispecfei
   # then point any VNC client at localhost:5901

Stop the session:

.. code-block:: bash

   vncserver -kill :1

**Optional — run it as a pinned systemd user service.** Create
``/etc/systemd/system/vncserver@.service``:

.. code-block:: ini

   [Unit]
   Description=TigerVNC server on display %i (housekeeping cores only)
   After=network-online.target

   [Service]
   Type=forking
   User=hsdev
   WorkingDirectory=/home/hsdev
   # Confine to housekeeping cores - keeps VNC off the shielded set
   CPUAffinity=6-15
   Nice=10
   ExecStartPre=-/usr/bin/vncserver -kill :%i
   ExecStart=/usr/bin/vncserver :%i -localhost yes -geometry 1920x1080 -depth 24
   ExecStop=/usr/bin/vncserver -kill :%i
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target

.. code-block:: bash

   sudo systemctl daemon-reload
   sudo systemctl enable --now vncserver@1.service

.. warning::
   ``CPUAffinity=`` in the unit file and ``taskset`` on the command line are
   both mandatory habits on this machine. An unpinned VNC session will migrate
   onto an isolated core and inject latency into the camera loop — the exact
   failure this whole build exists to prevent.

.. important::
   **Never expose VNC (5900–5910) directly to the network.** Always
   ``-localhost yes`` + SSH tunnel. TigerVNC's native auth is weak and the
   Archon network must stay clean.

----

11. Hardware Drivers & Subsystems
=================================

11.1 Physik Instrumente (PI) Driver
-----------------------------------

#. Download the Linux driver package from the `Physik Instrumente Software
   Suite <https://www.physikinstrumente.com/en/products/software-suite>`_ on a
   workstation and copy it over with ``scp`` (the RTC has no browser).
#. Extract, then run the installer:

   .. code-block:: bash

      cd <path_to_unpacked_PI_driver>
      sudo ./INSTALL

#. **Installer prompt responses:**

   .. list-table::
      :header-rows: 1
      :widths: 65 15

      * - Prompt
        - Answer
      * - Do you agree to the General Software License Agreement? [yn]
        - ``y``
      * - *(license text shown in pager)*
        - ``q``
      * - Install the PI ``${PI_PRODUCT_NAME}`` high level GCS library? [ynq]
        - ``y``
      * - To enable the access rights to a user group now press 'y'
        - ``y``
      * - Enable the access rights to a user group now? [ynq]
        - ``y``
      * - *(license text shown again)*
        - ``n``
      * - Install ``${PIPython}`` now? [ynq]
        - ``n``
      * - Install ``${PI Terminal}`` now? [ynq]
        - ``y``
      * - Please enter the name of the user group …
        - ``dialout``

.. note::
   ``PIPython`` is declined at the installer prompt on purpose — it is
   installed into the managed venv via ``pip install pipython`` (§9) so the
   deployed environment stays reproducible.

11.2 SPI Driver (libft4222)
---------------------------

#. Extract the archive:

   .. code-block:: bash

      tar xfvz libft4222-1.4.4.232.tgz

   Expected contents:

   * ``build-x86_32`` / ``build-x86_64``
   * ``build-arm-v6-hf`` / ``build-arm-v7-hf`` / ``build-arm-v7-sf`` /
     ``build-arm-v7-hf-uclibc`` / ``build-arm-v8``
   * ``libft4222-linux-1.4.4.221`` (mips, based on libftd2xx v1.4.27)
   * ``examples/``
   * ``libft4222.h``, ``ftd2xx.h``, ``WinTypes.h``
   * ``install4222.sh``

#. Install the library:

   .. code-block:: bash

      sudo ./install4222.sh

   This copies ``libft4222.so.1.4.4.232`` to ``/usr/local/lib`` and the headers
   to ``/usr/local/include``, and creates the version-independent symlink
   ``libft4222.so``.

   .. code-block:: bash

      sudo ldconfig
      ldconfig -p | grep ft4222

#. Build the example test binary:

   .. code-block:: bash

      cd examples

      # Dynamic link
      cc get-version.c -lft4222 -Wl,-rpath,/usr/local/lib -o ft4222-version

      # Static link
      cc -static get-version.c -lft4222 -Wl,-rpath,/usr/local/lib \
         -ldl -lpthread -lrt -lstdc++ -o ft4222-version-static

   .. note::
      The original notes ran ``cc`` under ``sudo``. That is unnecessary —
      compiling into your own directory needs no privileges, and root-owned
      build artifacts cause permission problems later. Dropped.

#. Run the test:

   .. code-block:: bash

      ./ft4222-version

   Expected output:

   .. code-block:: text

      Chip version: 42220400, LibFT4222 version: 010404E8

.. warning::
   The original note suggested ``sudo apt-get install binutils-2.26`` if static
   linking failed. **No such package exists on Ubuntu 24.04** — that advice is
   from a much older release. If static linking fails on 24.04, link
   dynamically (the supported path) or investigate the actual linker error;
   do not chase a versioned binutils package.

11.3 FT4222 udev Rules (non-root USB access)
--------------------------------------------

#. Create ``/etc/udev/rules.d/99_HISPEC_spi_ftdi_4222.rules``:

   .. code-block:: text

      SUBSYSTEM=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="601c", OWNER="hsdev", MODE="0660", GROUP="dialout"

#. Reload:

   .. code-block:: bash

      sudo udevadm control --reload-rules
      sudo udevadm trigger

#. Replug the board and verify ownership:

   .. code-block:: bash

      lsusb | grep 0403
      ls -l /dev/bus/usb/*/* | grep -i 0403

   The node should be owned by ``hsdev``, group ``dialout``, mode ``0660``.
   The SPI board is then usable without ``sudo``.

.. note::
   **SPI master mode:** the Slave Select (SS) pin **must be tied high**.

11.4 CameraD (camera-interface)
-------------------------------

.. code-block:: bash

   cd ~
   git clone https://github.com/CaltechOpticalObservatories/camera-interface.git
   cd camera-interface/build
   rm -rf ./*
   cmake .. -DCONTROLLER=archon -DINSTRUMENT=hispec_tracking_camera
   make -j"$(nproc)"

Record the commit hash in the as-built log:

.. code-block:: bash

   git -C ~/camera-interface rev-parse --short HEAD

See ``archongui.rst`` for Archon-side configuration and GUI usage.

----

12. Real-Time Process Placement
===============================

12.1 Real-Time Scheduling Privileges
------------------------------------

Allow non-root processes to request FIFO real-time priority:

.. code-block:: bash

   sudo setcap 'cap_sys_nice=eip' "$(command -v chrt)"
   chrt -f 60 ./<executable>

Alternatively grant it per-group in ``/etc/security/limits.d/99-rt.conf``:

.. code-block:: text

   @eng    -    rtprio    95
   @eng    -    memlock   unlimited
   @eng    -    nice      -20

Log out and back in to apply.

12.2 Pinning to Shielded Cores
------------------------------

.. code-block:: bash

   # Direct affinity
   taskset -c 0-5 chrt -f 80 ./camerad

   # Or via cpuset shielding (cores 0-5 shielded, rest for the system)
   sudo cset shield --cpu 0-5 --kthread=on
   sudo cset shield --exec -- chrt -f 80 ./camerad
   sudo cset shield --reset      # tear down

12.3 What Must Never Touch Cores 0–5
------------------------------------

* VNC / Xvnc / Openbox (§10.3 — pinned to housekeeping cores)
* SSH sessions and interactive shells
* ``rsync`` / ``scp`` transfers
* ``htop``, monitoring agents, log shippers
* Compilation (``make -j``) — build on housekeeping cores or another machine

.. tip::
   Add this to ``/home/hsdev/.bashrc`` so no login shell ever lands on a
   shielded core::

      taskset -cp 6-15 $$ > /dev/null 2>&1

----

.. _section-verify:

13. Verification & Acceptance
=============================

Run this after the final reboot. Record the results as the as-built baseline.

.. list-table::
   :header-rows: 1
   :widths: 32 48 20

   * - Check
     - Command
     - Expected
   * - Hostname
     - ``hostnamectl``
     - ``hispecfei``
   * - Users / groups
     - ``id hsfei; id hsdev``
     - ``dialout``, ``eng``, ``hispecfei``
   * - RT kernel
     - ``uname -a``
     - contains ``PREEMPT_RT``
   * - RT flag
     - ``cat /sys/kernel/realtime``
     - ``1``
   * - Ubuntu Pro
     - ``pro status``
     - ``realtime-kernel: enabled``
   * - Kernel variant
     - ``uname -r``
     - ``-realtime`` (or ``-intel-iotg``)
   * - Kernel cmdline
     - ``cat /proc/cmdline``
     - matches §6
   * - Isolated cores
     - ``cat /sys/devices/system/cpu/isolated``
     - ``0-5``
   * - Tickless cores
     - ``cat /sys/devices/system/cpu/nohz_full``
     - ``0-5``
   * - IRQ affinity
     - ``cat /proc/irq/*/smp_affinity_list``
     - no entry confined to 0–5
   * - irqbalance off
     - ``systemctl is-enabled irqbalance``
     - ``disabled`` / not-found
   * - systemd affinity
     - ``grep CPUAffinity /etc/systemd/system.conf``
     - ``6-15``
   * - SMT disabled
     - ``lscpu | grep 'Thread(s) per core'``
     - ``1``
   * - C-states (TCC)
     - ``cat /sys/devices/system/cpu/cpu0/cpuidle/state*/disable``
     - deep states ``1``
   * - Clocksource
     - ``cat /sys/devices/system/clocksource/clocksource0/current_clocksource``
     - ``tsc``
   * - No desktop
     - ``systemctl get-default``
     - ``multi-user.target``
   * - Services stripped
     - ``systemctl list-units --state=running``
     - short list only
   * - Management net
     - ``ip -br addr``
     - ``192.168.29.107/24``
   * - Archon link
     - ``ping -c 3 archon``
     - 0% loss
   * - Python
     - ``/opt/hispecfei/env/bin/python -V``
     - ``3.12.x``
   * - FT4222
     - ``./ft4222-version``
     - ``Chip version: 42220400``
   * - udev perms
     - ``ls -l /dev/bus/usb/*/* | grep 0403``
     - ``hsdev dialout 0660``
   * - X11 forward
     - ``ssh -X hsdev@hispecfei xeyes``
     - window appears
   * - VNC
     - tunnel ``5901`` → connect
     - Openbox session
   * - VNC pinning
     - ``taskset -cp $(pgrep Xvnc)``
     - **not** 0–5

Latency Baseline
----------------

Run under representative load and keep the numbers:

.. code-block:: bash

   # 30 minutes, RT prio 80, one thread per shielded core, hist output
   sudo cyclictest -m -S -p80 -i200 -h400 -D30m -a 0-5 > cyclictest_baseline.txt

   # Repeat while stressing the housekeeping cores
   stress-ng --cpu 8 --taskset 6-15 --timeout 30m &
   sudo cyclictest -m -S -p80 -i200 -h400 -D30m -a 0-5 > cyclictest_loaded.txt

Compare max latency loaded vs. idle. A large gap means something is still
scheduled on the isolated cores — recheck ``irqaffinity`` (§6) first.

----

14. Troubleshooting
===================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Symptom
     - Resolution
   * - ``cannot open display`` over SSH
     - Install ``xauth`` (§8.3); confirm ``X11Forwarding yes`` in
       ``sshd_config``; connect with ``ssh -X``; check ``echo $DISPLAY`` is
       non-empty. Do not set ``$DISPLAY`` manually.
   * - ``ssh -X`` fails, ``-Y`` works
     - Untrusted-X extension restriction. Acceptable on a trusted LAN; verify
       the client's ``ForwardX11Trusted`` setting.
   * - VNC connects to a grey screen
     - ``~/.vnc/xstartup`` is not executable or ``openbox`` is missing.
       ``chmod +x`` it and check ``~/.vnc/*.log``.
   * - VNC refuses remote connections
     - Expected — ``-localhost yes`` is deliberate. Use the SSH tunnel (§10.3).
   * - Qt app: ``could not load the Qt platform plugin "xcb"``
     - Install ``libxcb-xinerama0`` and ``libxkbcommon-x11-0`` (§8.4).
       Debug with ``QT_DEBUG_PLUGINS=1``.
   * - Advice to install ``qt5-default``
     - **Obsolete.** Package removed after Ubuntu 20.04. Use ``qtbase5-dev``.
   * - Matplotlib fails with no display
     - ``MPLBACKEND=Agg`` should be set by ``/etc/profile.d/mpl-headless.sh``
       (§9). Confirm with ``echo $MPLBACKEND``.
   * - FT4222 not found
     - ``lsusb`` for ``0403:601c``. If absent, it is a cable/board problem. If
       present but inaccessible, the udev rule (§11.3) did not apply — reload
       rules and replug.
   * - FT4222 ABI mismatch on ``libft4222.so``
     - Requires ``glibc`` ≥ 2.10. Ubuntu 24.04 ships 2.39, so a mismatch here
       almost always means a stale ``.so`` in ``/usr/local/lib`` — remove old
       copies and re-run ``sudo ldconfig``.
   * - SPI master mode misbehaves
     - Slave Select (SS) must be tied **high**.
   * - Static link fails, linker looks old
     - Link dynamically. Do **not** chase ``binutils-2.26`` — it does not exist
       on 24.04 (§11.2).
   * - ``import serial`` fails
     - Install ``pyserial``, not ``serial`` (§9).
   * - Latency spikes under load
     - Work the list in order: (1) ``irqaffinity`` overlapping the shielded set
       (§6) — the most common cause; (2) ``irqbalance`` still running and
       undoing it; (3) C-states not disabled / TCC Mode not enabled — look for
       jitter on an *idle* isolated core specifically; (4) SMT still on;
       (5) unpinned VNC or build jobs (§12.3); (6) cache contention → evaluate
       Intel CAT.
   * - RT kernel not booting after a Pro update
     - Select the previous kernel from the GRUB menu. Out-of-tree modules need
       rebuilding against the new ``uname -r`` (§5.4).
   * - ``chrt`` returns "Operation not permitted"
     - ``cap_sys_nice`` or the ``limits.d`` rtprio grant is missing (§12.1);
       re-login required after editing limits.
   * - Locked out after ``netplan apply``
     - Physical console required. Always use ``netplan try`` first (§4).
   * - Group membership not taking effect
     - ``usermod`` needs a re-login. ``newgrp dialout`` for the current shell.

----

.. _section-pending:

15. Pending Tasks
=================

* [ ] **RAID 1** — finalize hardware or software RAID 1 for the data drives.
  Revisit the ``/usr``-on-second-drive layout at the same time (§2).
* [ ] **Static IP** — confirm ``192.168.29.107`` is applied and reserved on the
  site network (§4); the previous build was still on DHCP.
* [ ] **Kernel variant** — confirm whether ``--variant=intel-iotg`` applies to
  this CPU and re-enable if the generic RT kernel was installed first (§5.3).
* [ ] **Intel CAT / Speed Shift** — evaluate if the §13 latency baseline is not
  tight enough (§6).
* [ ] **Patching policy** — ``unattended-upgrades`` is disabled (§7); define a
  manual maintenance window.
* [ ] **Backups** — no backup strategy defined for ``/opt/hispecfei`` or
  instrument configuration.
* [ ] **Software stack** — track upstream GitHub build notes for Python
  libraries, C++ sources and hardware drivers.
* [ ] **As-built log** — record kernel version, ``camera-interface`` commit,
  driver versions and ``cyclictest`` baselines.

----

16. Final Step
==============

Reboot to apply kernel parameters, BIOS settings, service changes and udev
rules, then work through §13.

.. code-block:: bash

   sudo reboot

Done.

----

17. References
==============

Real-time Ubuntu
----------------

* `Real-time Ubuntu documentation <https://documentation.ubuntu.com/real-time/latest/>`_ — top level
* `How to enable Real-time Ubuntu <https://documentation.ubuntu.com/real-time/latest/how-to/enable-real-time-ubuntu/>`_
* `Ubuntu Pro Client: enable realtime-kernel <https://documentation.ubuntu.com/pro/pro-client/enable_realtime_kernel/>`_
* `Switch from real-time to generic kernel <https://documentation.ubuntu.com/real-time/latest/how-to/switch-from-realtime-to-generic-kernel/>`_
* `Real-time Ubuntu releases <https://documentation.ubuntu.com/real-time/latest/reference/releases/>`_

Tuning
------

* `Configure CPUs for real-time processing <https://documentation.ubuntu.com/real-time/latest/how-to/cpu-boot-configs/>`_
* `Tune IRQ affinity <https://documentation.ubuntu.com/real-time/latest/how-to/tune-irq-affinity/>`_ — basis for the §6 correction
* `Isolate CPUs with cpusets <https://documentation.ubuntu.com/real-time/latest/how-to/isolate-workload-cpusets/>`_
* `Kernel boot parameters reference <https://documentation.ubuntu.com/real-time/latest/reference/kernel-boot-parameters/>`_
* `Modify kernel boot parameters <https://documentation.ubuntu.com/real-time/latest/how-to/modify-kernel-boot-parameters/>`_

Intel TCC
---------

* `Optimizing real-time performance on Intel CPUs <https://documentation.ubuntu.com/real-time/latest/tutorial/intel-tcc/>`_
* `TCC mode <https://documentation.ubuntu.com/real-time/latest/tutorial/intel-tcc/tcc-mode/>`_
* `Cache Allocation Technology <https://documentation.ubuntu.com/real-time/latest/tutorial/intel-tcc/intel-cat/>`_
* `Intel TCC User Guide <https://www.intel.com/content/www/us/en/content-details/851159/public-intel-time-coordinated-compute-tcc-user-guide.html>`_
* `Real-time Ubuntu on Intel SoCs <https://canonical.com/blog/real-time-industrial-systems>`_

Measurement
-----------

* `Measure maximum latency <https://documentation.ubuntu.com/real-time/latest/how-to/measure-maximum-latency/>`_
* `Tools for measuring real-time metrics <https://documentation.ubuntu.com/real-time/latest/reference/real-time-metrics-tools/>`_

Instrument
----------

* ``archongui.rst`` — Archon GUI and controller configuration
* `camera-interface <https://github.com/CaltechOpticalObservatories/camera-interface>`_
* `Physik Instrumente Software Suite <https://www.physikinstrumente.com/en/products/software-suite>`_