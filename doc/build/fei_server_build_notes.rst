Build Setup for hsdev FEI
==========================

System Requirements
-------------------

- OS: Ubuntu 24.04 LTS
- Linux: Current Kernel version Linux 6.8.0 (-59 Ubuntu)
- Python: 3.12 (required)

User Setup
----------

Create a development user ``hsdev``:

.. code-block:: bash

    sudo adduser hsdev
    sudo usermod -aG sudo hsdev
    sudo usermod -aG dialout hsdev  # Add serial access group

System Package Installation
---------------------------

Update package list and install the essential build tools:

.. code-block:: bash

    sudo apt update
    sudo apt install -y \
        software-properties-common \
        build-essential \
        libffi-dev \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        wget \
        curl \
        llvm \
        libncursesw5-dev \
        xz-utils \
        tk-dev \
        libxml2-dev \
        libxmlsec1-dev \
        liblzma-dev \
        git \
        python3-pip \
        libboost-all-dev \
        libopencv-dev \
        libccfits-dev \
        libcfitsio-dev

Disable unnecessary services

.. code-block:: bash

    sudo systemctl disable cups.service # printing
    sudo systemctl disable cups-browsed.service # printing
    sudo systemctl disable ModemManager.service
    sudo systemctl disable apt-daily.timer # automatic updates
    sudo systemctl disable apt-daily-upgrade.timer #automatic updates
    sudo systemctl disable avahi-daemon.service # zeroconf mDNS

KROOT Specific Packages
~~~~~~~~~~~~~~~~~~~~~~~

These packages are needed for KROOT environments:

.. code-block:: bash

    sudo apt install -y \
        openconnect \
        subversion cvs at \
        python-dev-is-python3 \
        libxt-dev libxml2-dev libncurses-dev \
        tcl tcl-dev tcl-thread tcllib tk tk-dev expect \
        tclx tcl-fitstcl libpq-dev \
        g++ gfortran \
        libboost-dev libboost-system-dev libboost-filesystem-dev \
        python3-tk python3-pil.imagetk \
        libpam-dev \
        pandoc groff rst2pdf \
        python3-dev python3-docutils \
        python3-ephem \
        pyqt5-dev-tools \
        make m4 autoconf \
        xorg-dev xaw3dg-dev \
        libmotif-dev \
        lib32c-dev \
        libcfitsio-dev \
        snmp \
        flex flex-doc bison bison-doc

Python 3.12 Installation
------------------------

Ubuntu 24.04 ships with Python 3.12.3. Double check version is at least 3.12.3 and not newer than 3.13.

Check Version:

.. code-block:: bash

    python3 --version
    # Expected: Python 3.12.3 => must be < Python 3.13

If you need to install Python:

Build from Source:

.. code-block:: bash

    cd /usr/src
    sudo wget https://www.python.org/ftp/python/3.12.3/Python-3.12.3.tgz
    sudo tar xzf Python-3.12.3.tgz
    cd Python-3.12.3
    sudo ./configure --enable-optimizations
    sudo make -j $(nproc)
    sudo make altinstall  # Installs as python3.12

Python Package Installation
---------------------------

Install required Python packages using pip:

.. code-block:: bash

    python3.12 -m pip install --upgrade pip
    python3.12 -m pip install numpy matplotlib pipython serial panda QT5.2 cmake

Verify installation:

.. code-block:: bash

    python3.12 --version
    pip3.12 list

Optional: Virtual Environment
-----------------------------

Create and activate a virtual environment:

.. code-block:: bash

    python3.12 -m venv ~/env
    source ~/env/bin/activate
    pip install numpy matplotlib pipython

Download Needed Drivers (and software if needed)
------------------------------------------------

**Physik Instrumente**

**SPI Driver lib4222**
- [Dan install note]
- Permanent dialout access for user across machine (requires logout/login):

  .. code-block:: bash

      sudo usermod -a -G dialout hsdev

- Instant change in group for current terminal session:

  .. code-block:: bash

      newgrp dialout

OS Optimization Notes (07/09/2025)
----------------------------------

**Real-Time Scheduling and Process Prioritization**
- Use `chrt` to assign real-time priorities to time-critical processes.
- Allow `chrt` to be run without sudo for selected processes by modifying security policies (e.g., with setcap or via sudoers).
- Commonly used priority: FIFO scheduling with priority 60.

.. code-block:: bash

    sudo setcap 'cap_sys_nice=eip' <path/to/chrt>
    chrt -f 60 ./<executable file>

**CPU Isolation**
- Install and use cset (CPUSET) for isolating CPU cores

.. code-block:: bash

    sudo apt install cset

- Dedicated physical CPU cores (no SMT/hyperthreading):
  - Total cores: 16
  - Isolated cores for CameraD: 11–15
  - Remaining cores (0–10): Available for other system tasks
  - Disable hyperthreading/SMT in BIOS for deterministic performance.

**GRUB Boot Optimization**
- Edit `/etc/default/grub` to add kernel boot parameters
- You can edit using `vim`, or use this command:

.. code-block:: bash

    GRUB_CMDLINE_LINUX_DEFAULT="quiet splash isolcpus=11-15 nohz_full=11-15 rcu_nocbs=11-15 rcu_nocb_poll"
    sudo update-grub

**BIOS Changes**
- Save any work and restart the machine
- Press BIOS key during initial logo screen (typically Esc, F2, or Del)
- Navigate to BIOS menu (use Enter to select, Esc to go back)

  **CHANGES:**
  - Look for: Intel Hyper-Threading, SMT, or Logical Processor
  - Set to Disabled

.. note::

    For CameraD, change to FIFO process scheduling for those threads.

Final Step
==========

**RESTART/REBOOT** the server to complete driver installation and apply CPU/OS optimization changes.

Done!
=====
