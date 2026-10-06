====================================
RT Build: Firmware, OS and RT Kernel
====================================

:Prerequisite: :doc:`physical_build` complete
:Next: :doc:`software_build`

.. contents::
   :depth: 1
   :local:

----

1. Scope
========

The OS is **Real-time Ubuntu 26.04 LTS**: Ubuntu with Canonical's
``PREEMPT_RT`` kernel, deployed through an **Ubuntu Pro** subscription
(:ref:`section-rt-kernel`). ``PREEMPT_RT`` makes the kernel fully preemptible,
converts spinlocks to sleeping rt-mutexes with priority inheritance, and runs
IRQ handlers as schedulable threads. The result is a bounded worst-case latency.

This page takes the machine from bare hardware to a tuned RT platform: TCC
enabled in firmware, hard CPU shielding, and background services stripped.

Design rules:

#. **The RT kernel is the foundation, not an optimization.** Every tuning step
   below assumes ``PREEMPT_RT`` is running.
#. **No desktop environment.** Ubuntu **Server**, no GNOME, no display manager,
   no snaps beyond the base set.
#. **Nothing runs on shielded cores except instrument code.** Shells, VNC and
   services are confined to housekeeping cores.

.. note::
   Ubuntu Pro is free for up to 5 machines for personal and small-scale use;
   Caltech/COO deployments should use the institutional subscription.

.. note::
   ``$`` prompts are omitted. Unless a block says otherwise, run as ``hsfei``
   with ``sudo``. Steps marked **[reboot]** require a restart before continuing.

----

2. Installation Media
=====================

All drives are erased before starting; this is a full rebuild.

* **OS:** Ubuntu **Server** 26.04 LTS (``.iso``, not Desktop)
* **Source:** official Ubuntu download
* **Format:** bootable USB (``dd`` / Rufus / balenaEtcher)

----

.. _section-bios:

3. Firmware: BIOS, TCC and Hardware RAID
========================================

Do this before installing the OS. The RAID volume must exist for the installer
to see it, and disabling SMT changes the core count used for shielding.

BIOS Settings
-------------

#. Reboot and enter BIOS (``F2``, ``Del``, or ``Esc``).
#. **Hyper-Threading / SMT / Logical Processors: Disabled.**
   Deterministic execution requires one thread per physical core.
#. **TCC Mode: Enabled.** On Intel reference BIOS this is under
   *Intel® Advanced Menu ‣ Time Coordinated Computing*. If the option is
   hidden, consult the board vendor or set the underlying options manually per
   Intel's TCC User Guide.
#. **Double reboot.** TCC settings are not fully applied until the second POST.

.. note::
   **TCC Mode subsumes the manual C-state work.** It disables C-states and
   optimizes power-state and frequency transitions. Canonical measured average
   scheduling jitter dropping from ~100 µs to under 10 µs on an isolated core
   from this setting alone.

   An isolated core whose periodic task finishes early idles for the rest of
   the cycle, and the idle subsystem drops it into a deep C-state with a long
   exit latency. That exit latency is the jitter. If TCC Mode is unavailable,
   disable C-states below C1 manually and set the power profile to
   *Maximum Performance*.

.. _section-raid:

Hardware RAID 1 (Boot Volume)
-----------------------------

The two Samsung 990 Pro 1 TB NVMe drives form a RAID 1 array on the Broadcom
MegaRAID 9520-2M2 controller.

#. During POST, enter the MegaRAID configuration utility.
#. Create a **RAID 1** virtual drive from the two 990 Pro NVMe drives.
#. Confirm the array reports **Optimal**.
#. The installer should then show a **single ~1 TB device** for the OS.

----

.. _section-os-install:

4. OS Installation (Ubuntu Server 26.04)
========================================

Installation Parameters
-----------------------

* **Language / Keyboard:** English
* **Networking:** Ethernet connected, **no proxy**. Leave DHCP for now; static
  addresses are applied in :ref:`section-network`.
* **Mirror:** ``http://us.archive.ubuntu.com/ubuntu/`` (default)
* **Server profile:** minimized install.
* **OpenSSH:** **install it.** Without ``sshd`` a headless build stops here.
* **Featured / Popular Snaps:** select **none**. ``snapd`` timers are a jitter
  source.

Storage
-------

* **Root filesystem:** the MegaRAID RAID 1 volume (:ref:`section-raid`)
* **Data:** 2 TB SSD, ``ext4``, mounted at ``/data``

Credentials
-----------

* **Server name:** ``hispecfei``
* **Primary user:** ``hsfei`` (gets ``sudo``)
* **Password:** set during installation, **not documented here**

First Boot
----------

.. code-block:: bash

   sudo apt update && sudo apt upgrade -y

----

.. _section-identity:

5. Identity: Hostname, Users, Groups
====================================

Hostname
--------

.. code-block:: bash

   sudo hostnamectl set-hostname hispecfei

Map the loopback alias in ``/etc/hosts``:

.. code-block:: text

   127.0.1.1   hispecfei

Groups and Users
----------------

``hsfei`` is the primary account created at install. ``hsdev`` is the
engineering account for day-to-day work and owns the hardware device nodes.

.. code-block:: bash

   sudo groupadd -f hispecfei     # instrument / deployment group
   sudo groupadd -f eng           # engineering read+write on /opt

   sudo adduser hsdev
   sudo usermod -aG sudo,dialout,hispecfei,eng hsdev
   sudo usermod -aG dialout,hispecfei,eng hsfei

.. note::
   Group changes require a logout/login (or ``newgrp dialout`` for the current
   shell). Confirm with ``id hsdev``.

SSH Keys and Hardening
----------------------

Install your public key for both accounts *before* relying on remote-only
access:

.. code-block:: bash

   ssh-copy-id hsfei@hispecfei
   ssh-copy-id hsdev@hispecfei

Then set in ``/etc/ssh/sshd_config``:

.. code-block:: text

   PasswordAuthentication no
   PermitRootLogin no
   X11Forwarding yes
   X11UseLocalhost yes

.. code-block:: bash

   sudo systemctl restart ssh

``X11Forwarding yes`` is required for :ref:`section-remote-gui`.

----

.. _section-network:

6. Network Configuration (netplan)
==================================

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
   Always use ``netplan try`` first. A bad netplan file on a headless box means
   a physical trip to the machine.

Archon Host Entry
-----------------

Add ``10.0.0.2    archon`` to ``/etc/hosts``, connect the Archon to the fiber
port labelled **archon**, and verify:

.. code-block:: bash

   ping -c 3 archon
   ip -br addr show enp202s0f0np0

The ``10.0.0.0/24`` link has no default route on purpose: instrument traffic
stays off the management network. See ``archongui.rst`` for Archon-side
configuration.

----

.. _section-rt-kernel:

7. Real-time Kernel (Ubuntu Pro)
================================

Attach Ubuntu Pro
-----------------

The RT kernel is delivered only through Ubuntu Pro (``elijahab`` account).

.. code-block:: bash

   sudo pro attach          # prompts for the token
   pro status

.. warning::
   Never paste the Pro token into this document, a script, or shell history.
   If a token has been echoed into a shared file, rotate it.

Install **[reboot]**
--------------------

.. code-block:: bash

   sudo apt update
   sudo apt install ubuntu-realtime
   sudo reboot

Accept the prompt to switch the default boot kernel.

Verify
------

.. code-block:: bash

   uname -a                              # contains PREEMPT_RT
   pro status | grep realtime            # realtime-kernel   enabled
   cat /sys/kernel/realtime              # 1
   chrt -m                               # SCHED_FIFO / SCHED_RR 1-99
   grep -c . /proc/pressure/cpu          # PSI available

As-built Result
---------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Component
     - Value
   * - CPU
     - Intel Core i5-13500E (13th Gen), 14 cores, 1 socket
   * - Firmware
     - TCC-capable BIOS, TCC Mode enabled
   * - OS
     - Ubuntu 26.04 LTS
   * - Kernel
     - ``7.0.0-38-realtime``
   * - Kernel config
     - ``PREEMPT_RT=y``, ``INTEL_TCC=y``, ``INTEL_TCC_COOLING=m``, ``TSNEP=m``
   * - Scheduler
     - ``SCHED_FIFO`` 1-99, ``SCHED_RR`` 1-99
   * - PSI
     - CPU pressure available

----

.. _section-grub:

8. CPU Shielding
================

GRUB Kernel Parameters **[reboot]**
-----------------------------------

Cores **0-5** are shielded from the scheduler, RCU callbacks and the timer
tick. Edit ``/etc/default/grub``:

.. code-block:: text

   GRUB_CMDLINE_LINUX_DEFAULT="quiet clocksource=tsc tsc=reliable nmi_watchdog=0 nosoftlockup isolcpus=domain,0-5 rcu_nocbs=0-5 nohz_full=0-5 irqaffinity=6-15 kthread_cpus=6-15"

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Parameter
     - Purpose
   * - ``clocksource=tsc tsc=reliable``
     - Use the TSC; avoids HPET/ACPI read latency spikes
   * - ``nmi_watchdog=0``
     - Remove periodic NMI perf interrupts
   * - ``nosoftlockup``
     - Suppress soft-lockup warnings from long RT bursts
   * - ``isolcpus=domain,0-5``
     - Remove cores 0-5 from all scheduling domains
   * - ``rcu_nocbs=0-5``
     - Offload RCU callbacks from the isolated cores
   * - ``nohz_full=0-5``
     - Stop the tick when one task is runnable
   * - ``irqaffinity=6-15``
     - Direct hardware IRQs to housekeeping cores
   * - ``kthread_cpus=6-15``
     - Restrict kernel threads to housekeeping cores

.. warning::
   The ``irqaffinity`` and ``isolcpus`` ranges **must not overlap**.

.. code-block:: bash

   sudo update-grub
   sudo reboot

   # After boot
   cat /proc/cmdline
   cat /sys/devices/system/cpu/isolated       # 0-5
   cat /sys/devices/system/cpu/nohz_full      # 0-5

IRQs still bound to a shielded core after reboot are typically PCIe devices.
Rebinding them is not trivial or safe; they are left as-is and jitter has been
confirmed within spec.

Disable irqbalance
------------------

``irqbalance`` redistributes interrupts at runtime and silently undoes
``irqaffinity``:

.. code-block:: bash

   sudo systemctl disable --now irqbalance

Confine systemd Services
------------------------

Keep every systemd service, present and future, off the shielded cores. Edit
``/etc/systemd/system.conf``:

.. code-block:: ini

   [Manager]
   CPUAffinity=6-13

.. code-block:: bash

   sudo systemctl daemon-reexec

Check C-states
--------------

Confirm TCC (:ref:`section-bios`) disabled the deep C-states:

.. code-block:: bash

   for cpu in /sys/devices/system/cpu/cpu*/cpuidle/state*; do
       echo -n "$cpu: "; cat "$cpu"/name
       echo -n "  Exit latency: ";     cat "$cpu"/latency
       echo -n "  Disabled [1=yes]: "; cat "$cpu"/disable
   done

Further Intel Optimizations (optional)
--------------------------------------

If the latency baseline (:ref:`section-verify`) is not tight enough, evaluate:

* **Cache Allocation Technology (CAT):** partitions last-level cache so
  housekeeping workloads cannot evict the RT task's working set.
* **Speed Shift / HWP:** tunes frequency transitions on the isolated cores.

See Canonical's `Optimizing real-time performance on Intel CPUs
<https://documentation.ubuntu.com/real-time/latest/tutorial/intel-tcc/>`_.

----

.. _section-services:

9. Service Stripping
====================

Disable unneeded daemons, timers and update machinery. ``|| true`` keeps the
block safe when a unit is absent.

.. code-block:: bash

   for svc in \
       irqbalance.service \
       cups.service cups-browsed.service \
       ModemManager.service \
       avahi-daemon.service avahi-daemon.socket \
       bluetooth.service \
       apt-daily.timer apt-daily-upgrade.timer \
       unattended-upgrades.service \
       fwupd-refresh.timer \
       man-db.timer \
       motd-news.timer \
       update-notifier-download.timer \
       update-notifier-motd.timer \
       sysstat-collect.timer \
       sysstat-summary.timer \
       sysstat-rotate.timer \
       multipathd.service \
       udisks2.service \
       plocate-updatedb.timer
   do
       sudo systemctl disable --now "$svc" 2>/dev/null || true
   done

   # Audit what is left
   systemctl list-units --type=service --state=running
   systemctl list-timers --all

Keep enabled: ``ssh``, ``systemd-networkd``, ``systemd-resolved``, ``chrony``,
``ubuntu-advantage`` and ``ua-timer.timer``. ``thermald`` and
``networkd-dispatcher`` are retained pending further RT/thermal testing.

.. warning::
   With ``unattended-upgrades`` disabled, **security patching is manual**.
   Schedule a maintenance window.

----

.. _section-rt-privileges:

10. RT Tooling and Scheduling Privileges
========================================

.. code-block:: bash

   sudo apt install -y util-linux rt-tests linuxptp stress-ng

``rt-tests`` provides ``cyclictest`` for :ref:`section-verify`.

Allow the ``eng`` group to request real-time priority. Create
``/etc/security/limits.d/99-rt.conf``:

.. code-block:: text

   @eng    -    rtprio    95
   @eng    -    memlock   unlimited
   @eng    -    nice      -20

Log out and back in to apply. Alternatively grant the capability on ``chrt``:

.. code-block:: bash

   sudo setcap 'cap_sys_nice=eip' "$(command -v chrt)"

----

.. _section-verify:

11. Verification
================

Reboot, then record the results as the as-built baseline.

.. list-table::
   :header-rows: 1
   :widths: 25 50 25

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
   * - Kernel cmdline
     - ``cat /proc/cmdline``
     - matches :ref:`section-grub`
   * - Isolated / tickless cores
     - ``cat /sys/devices/system/cpu/{isolated,nohz_full}``
     - ``0-5``
   * - IRQ affinity
     - ``cat /proc/irq/*/smp_affinity_list``
     - none confined to 0-5 (PCIe excepted)
   * - irqbalance off
     - ``systemctl is-enabled irqbalance``
     - ``disabled`` / not-found
   * - systemd affinity
     - ``grep CPUAffinity /etc/systemd/system.conf``
     - ``6-13``
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
   * - Management net
     - ``ip -br addr``
     - ``192.168.29.107/24``
   * - Archon link
     - ``ping -c 3 archon``
     - 0% loss

Latency Baseline
----------------

.. code-block:: bash

   # 30 min, RT prio 80, one thread per shielded core
   sudo cyclictest -m -S -p80 -i200 -h400 -D30m -a 0-5 > cyclictest_baseline.txt

   # Repeat while stressing the housekeeping cores
   stress-ng --cpu 8 --taskset 6-15 --timeout 30m &
   sudo cyclictest -m -S -p80 -i200 -h400 -D30m -a 0-5 > cyclictest_loaded.txt

A large gap between loaded and idle max latency means something is still
running on the isolated cores; recheck ``irqaffinity`` first.

----

12. Troubleshooting
===================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Symptom
     - Resolution
   * - Installer shows two 1 TB drives
     - RAID 1 volume not created; revisit :ref:`section-raid`.
   * - Latency spikes under load
     - Check in order: (1) ``irqaffinity`` overlapping the shielded set;
       (2) ``irqbalance`` still running; (3) TCC Mode off / C-states enabled
       (look for jitter on an *idle* isolated core); (4) SMT still on;
       (5) unpinned processes on 0-5 (:ref:`section-rt-placement`);
       (6) cache contention, evaluate Intel CAT.
   * - RT kernel not booting after a Pro update
     - Select the previous kernel in GRUB. Out-of-tree modules need rebuilding
       against the new ``uname -r``.
   * - ``chrt``: "Operation not permitted"
     - ``limits.d`` rtprio grant or ``cap_sys_nice`` missing
       (:ref:`section-rt-privileges`); re-login after editing limits.
   * - Locked out after ``netplan apply``
     - Physical console required. Always ``netplan try`` first.
   * - Group membership not taking effect
     - Re-login, or ``newgrp dialout`` for the current shell.

----

13. Pending Tasks
=================

* [ ] **RAID 1 on /data**: data drive is not yet mirrored.
* [ ] **Intel CAT / Speed Shift**: evaluate if the latency baseline is not tight
  enough.
* [ ] **Patching policy**: ``unattended-upgrades`` is disabled; define a manual
  maintenance window.

----

14. References
==============

Real-time Ubuntu
----------------

* `Real-time Ubuntu documentation <https://documentation.ubuntu.com/real-time/latest/>`_
* `How to enable Real-time Ubuntu <https://documentation.ubuntu.com/real-time/latest/how-to/enable-real-time-ubuntu/>`_
* `Ubuntu Pro Client: enable realtime-kernel <https://documentation.ubuntu.com/pro/pro-client/enable_realtime_kernel/>`_
* `Switch from real-time to generic kernel <https://documentation.ubuntu.com/real-time/latest/how-to/switch-from-realtime-to-generic-kernel/>`_
* `Real-time Ubuntu releases <https://documentation.ubuntu.com/real-time/latest/reference/releases/>`_

Tuning
------

* `Configure CPUs for real-time processing <https://documentation.ubuntu.com/real-time/latest/how-to/cpu-boot-configs/>`_
* `Tune IRQ affinity <https://documentation.ubuntu.com/real-time/latest/how-to/tune-irq-affinity/>`_
* `Isolate CPUs with cpusets <https://documentation.ubuntu.com/real-time/latest/how-to/isolate-workload-cpusets/>`_
* `Kernel boot parameters reference <https://documentation.ubuntu.com/real-time/latest/reference/kernel-boot-parameters/>`_
* `Modify kernel boot parameters <https://documentation.ubuntu.com/real-time/latest/how-to/modify-kernel-boot-parameters/>`_

Intel TCC
---------

* `Optimizing real-time performance on Intel CPUs <https://documentation.ubuntu.com/real-time/latest/tutorial/intel-tcc/>`_
* `TCC mode <https://documentation.ubuntu.com/real-time/latest/tutorial/intel-tcc/tcc-mode/>`_
* `Cache Allocation Technology <https://documentation.ubuntu.com/real-time/latest/tutorial/intel-tcc/intel-cat/>`_
* `Intel TCC User Guide <https://www.intel.com/content/www/us/en/content-details/851159/public-intel-time-coordinated-compute-tcc-user-guide.html>`_

Measurement
-----------

* `Measure maximum latency <https://documentation.ubuntu.com/real-time/latest/how-to/measure-maximum-latency/>`_
* `Tools for measuring real-time metrics <https://documentation.ubuntu.com/real-time/latest/reference/real-time-metrics-tools/>`_
