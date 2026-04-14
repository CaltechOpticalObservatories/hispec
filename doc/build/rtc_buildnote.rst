Certainly! Here is your updated documentation—now including the author names and the current date—formatted as a **reStructuredText (.rst)** file.

.. code-block:: rst

    ================================================
    System Build: TCC & Real-Time Kernel
    ================================================

    :Authors: Elijah A-B, Dan Ech
    :Date: 2026-04-13
    :System Name: hsfei

    1. Prerequisites & Media Preparation
    ====================================
    To ensure a clean environment, all drives were erased before starting the 
    **0% -> 100% build**.

    USB Drive A: Ubuntu Installer
    -----------------------------
    * **OS:** Ubuntu Server 24.04.1 LTS
    * **Source:** Official Ubuntu Download
    * **Format:** Bootable ISO

    USB Drive B: Cloud-Init (CIDATA)
    --------------------------------
    * **Format:** FAT32
    * **Volume Name:** ``CIDATA``
    * **Required Files (Root Directory):**
        * ``user-data``: YAML formatted configuration file.
        * ``meta-data``: Empty file (required for boot check).

    2. OS Installation (Ubuntu Server 24.04)
    ========================================
    *Note: Due to issues with the automated installation, the manual method was used.*

    Installation Parameters
    -----------------------
    * **Language/Keyboard:** English
    * **Networking:** Ethernet connected; No Proxy.
    * **Mirror:** ``[http://us.archive.ubuntu.com/ubuntu/](http://us.archive.ubuntu.com/ubuntu/)`` (Default)

    Storage Configuration
    ---------------------
    * **Primary Drive:** Samsung 990 Pro (1TB).
    * **Mount Points:** Temporary format of the 2TB drive as ``ext4``, mounted to ``/usr``.
    * **Note:** Software RAID 1 was bypassed; to be configured at a later stage.

    Credentials
    -----------
    * **Name/Server/User:** ``hsfei``
    * **Password:** ``fain'tdev``
    * **Software:** Default "Popular Snaps" selected.

    3. Post-Install System Hardening
    ================================
    Run the following commands immediately after the first boot:

    System Updates
    --------------
    .. code-block:: bash

        sudo apt update && sudo apt upgrade -y

    Enable Real-Time Kernel
    ----------------------
    The Real-Time (RT) kernel requires an Ubuntu Pro subscription (using ``elijahab`` account).

    .. code-block:: bash

        # Attach Ubuntu Pro
        sudo pro attach [USER_TOKEN]

        # Enable RT Kernel
        sudo pro enable realtime-kernel

    CPU Shielding & GRUB Optimization
    ---------------------------------
    To optimize performance, 6 cores were shielded to prevent background OS interference.

    1. Edit ``/etc/default/grub``:

    .. code-block:: text

        GRUB_CMDLINE_LINUX_DEFAULT="quiet splash clocksource=tsc tsc=reliable nmi_watchdog=0 nosoftlockup isolcpus=domain,0-5 rcu_nocbs=0-5 nohz_full=0-5 irqaffinity=0"

    2. Update GRUB and Reboot.

    .. tip::
       You can now assign threads to these shielded cores (0-5) using ``taskset`` 
       or via codebase affinity settings.

    4. TCC Mode (Time Coordinated Computing)
    ========================================

    Enable Sequence
    ---------------
    1. Enter BIOS -> **Enable TCC Mode**.
    2. Perform a **Double Reboot** to ensure all hardware settings are applied.

    5. Pending Tasks
    ================
    * [ ] **Static IP Assignment:** Change from DHCP to ``192.168.29.107``.
    * [ ] **Software Stack:** Follow GitHub build notes for Python libraries, C++ sources, and hardware drivers.
    * [ ] **RAID:** Finalize hardware or software RAID 1 configuration for data drives.