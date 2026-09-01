===========================================
Build Setup for hsdev FEI
===========================================

System Requirements
-------------------

- **OS:** Ubuntu 24.04 LTS
- **Linux Kernel:** 6.8.0 (-59 Ubuntu)
- **Python:** 3.12 (required)

Initial OS User & Hostname Setup
--------------------------------

The target machine is initially provisioned during OS installation with the primary administrative user:

- **Primary User:** ``hispecfei`` (with sudo privileges)

Configure hostname and network loopback resolution:

.. code-block:: bash

   # Set static hostname
   sudo hostnamectl set-hostname hispecfei

Edit ``/etc/hosts`` to map the local loopback entry to the new hostname:

.. code-block:: text

   127.0.1.1   hispecfei

Verify the active hostname:

.. code-block:: bash

   hostnamectl

Development User & Group Setup
------------------------------

Create required groups for HISPEC FEI engineering and development:

.. code-block:: bash

   sudo groupadd -f hispecfei
   sudo groupadd -f eng

Set up the secondary development user ``hsdev`` and assign appropriate group memberships:

.. code-block:: bash

   sudo adduser hsdev
   sudo usermod -aG sudo,dialout,hispecfei,eng hsdev

.. note::
   The following block provisions service accounts non-interactively. Since ``hispecfei`` is created during initial OS installation and ``hsdev`` is created above, the script gracefully skips pre-existing accounts while ensuring required target accounts exist.

.. code-block:: bash

   for u in hispecfei hsdev; do
       sudo useradd -m -s /bin/bash "$u" 2>/dev/null || true
   done

.. note::
   - On reboot, the new hostname takes effect system-wide.
   - User group modifications (via ``usermod``) require logging out and back in to take effect.
   - To force an immediate group update for the current session, run ``newgrp dialout``.

System Package Installation
---------------------------

Update package list and install core build tools, development libraries, and utilities:

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
       libcfitsio-dev \
       cmake \
       libzmq3-dev \
       net-tools \
       htop

KROOT Specific Packages (Optional / Machine Dependent)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install packages required for KROOT environment build dependencies:

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
       python3-venv \
       python3-ephem \
       pyqt5-dev-tools \
       make m4 autoconf \
       xorg-dev xaw3dg-dev \
       libmotif-dev \
       libc6-dev-i386 \
       libcfitsio-dev \
       snmp \
       flex flex-doc bison bison-doc

Python Environment Setup
------------------------

Global Shared Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a centralized, read-only-for-engineers virtual environment under ``/opt/hispecfei/env``. 
This environment houses the official deployed packages used across the instrument framework.

Execute as the primary ``hispecfei`` user:

.. code-block:: bash

   # Create global directory and virtual environment
   sudo mkdir -p /opt/hispecfei
   sudo python3 -m venv /opt/hispecfei/env

   # Set ownership: owned by 'hispecfei', group-accessible by 'eng'
   sudo chown -R hispecfei:eng /opt/hispecfei
   sudo chmod -R 775 /opt/hispecfei

   # Install canonical deployed packages into global environment
   /opt/hispecfei/env/bin/pip install --upgrade pip
   /opt/hispecfei/env/bin/pip install numpy matplotlib pipython serial pandas PyQt5 cmake

To make the global environment active by default for all session shells, add the activation hook to system or user bash profiles:

.. code-block:: bash

   echo 'source /opt/hispecfei/env/bin/activate' >> /home/hsdev/.bashrc

Local Engineer Virtual Environments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Engineers working under ``hsdev`` (or individual local accounts) can spin up isolated, lightweight local virtual environments for feature development.

Option A: Inherit Deployed Global Packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To inherit all pre-installed packages from the global environment while allowing local testing:

.. code-block:: bash

   python3 -m venv --system-site-packages ~/fei-venv
   source ~/fei-venv/bin/activate

Option B: Isolated Sandbox
^^^^^^^^^^^^^^^^^^^^^^^^^^

To build an isolated sandbox independent of the deployed environment:

.. code-block:: bash

   python3 -m venv ~/fei-venv_sandbox
   source ~/fei-venv_sandbox/bin/activate
   pip install --upgrade pip

Hardware Drivers & Specialized Subsystems
-----------------------------------------

Physik Instrumente (PI) Driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Download the latest Linux driver package from `Physik Instrumente Software Suite <https://www.physikinstrumente.com/en/products/software-suite>`_.
2. Extract the archive, open terminal in the target directory, and launch the installer:

   .. code-block:: bash

      cd <path_to_unpacked_PI_driver>
      sudo ./INSTALL

3. Installation Prompt Responses:
   - **Do you agree to the General Software License Agreement? [yn]:** ``y``
   - **{shows full License Agreement}** press ``q`` to exit pager
   - **Install the PI ${PI_PRODUCT_NAME} high level GCS library? [ynq]:** ``y``
   - **To enable the access rights to a user group now press 'y'** ``y``
   - **Enable the access rights to a user group now? [ynq]:** ``y``
   - **{shows full License Agreement}** ``n``
   - **Install ${PIPython} now? [ynq]:** ``n``
   - **Install ${PI Terminal} now? [ynq]:** ``y``
   - **Please enter the name of the user group ...:** ``dialout``

SPI Driver (libft4222)
~~~~~~~~~~~~~~~~~~~~~~

1. Extract the archive:

   .. code-block:: bash

      tar xfvz libft4222-1.4.4.232.tgz

   This unpacks the archive, creating the following directory structure:

   - build-x86_32
   - build-x86_64
   - build-arm-v6-hf
   - build-arm-v7-hf
   - build-arm-v7-sf
   - build-arm-v7-hf-uclibc
   - build-arm-v8
   - libft4222-linux-1.4.4.221 for mips (based on libftd2xx v1.4.27)
   - examples
   - libft4222.h
   - ftd2xx.h
   - WinTypes.h
   - install4222.sh

2. Install the library:

   .. code-block:: bash

      sudo ./install4222.sh

   This installs the dynamic library. It copies ``libft4222.so.1.4.4.232`` and headers to
   ``/usr/local/lib`` and ``/usr/local/include`` respectively. It also creates a 
   version-independent symbolic link, ``libft4222.so``.

3. Compile test executable from examples:

   .. code-block:: bash

      cd examples

   # Dynamic library build:
      sudo cc get-version.c -lft4222 -Wl,-rpath,/usr/local/lib

   # Static library build:
      sudo cc -static get-version.c -lft4222 -Wl,-rpath,/usr/local/lib -ldl -lpthread -lrt -lstdc++

.. note::
   If static compilation fails due to an outdated linker, update binutils:

   .. code-block:: bash

      sudo apt-get update
      sudo apt-get install binutils-2.26
      export PATH="/usr/lib/binutils-2.26/bin:$PATH"

4. Execute binary test:

   .. code-block:: bash

      sudo ./a.out

Expected output:

   .. code-block:: text

      Chip version: 42220400, LibFT4222 version: 010404E8

SPI FTDI 4222 udev Configuration (Non-Root USB Access)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
     
     - There may be no FT4222H connected. Run ``lsusb`` and check for something like:

       .. code-block:: text

          Bus 001 Device 005: ID 0403:601c Future Technology Devices International, Ltd

     - Or your program lacks USB access. Use ``sudo``, ``su``, or run as root.

   - **ABI mismatch error (libft4222.so):** Try upgrading ``glibc`` to version 2.10 or newer.
   - **SPI Mode Note:** If enabling SPI master mode, the SS pin **must be tied high**.

**SPI FTDI 4222 udev Configuration (Non-root Access)**

1. Create a udev rules file at ``/etc/udev/rules.d/99_HISPEC_spi_ftdi_4222.rules``:

.. code-block:: text

   SUBSYSTEM=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="601c", OWNER="hsdev", MODE="0660", GROUP="dialout"

2. Reload rules:

   .. code-block:: bash

      sudo udevadm control --reload-rules
      sudo udevadm trigger

3. Verify ownership on reconnected board:

.. code-block:: bash

      ls -l /dev/bus/usb/*/* | grep 0403

   The device node should be owned by ``hsdev``, belong to the ``dialout`` group, and
   have read/write permissions for the owner and group (``0660``).

Once verified, the SPI board should be accessible without requiring root privileges.

CameraD Installation
~~~~~~~~~~~~~~~~~~~~

Clone and build the camera interface repository with specific controller and instrument definitions:

.. code-block:: bash

   cd ~
   git clone https://github.com/CaltechOpticalObservatories/camera-interface.git
   cd camera-interface/build
   rm -rf ./*
   cmake .. -DCONTROLLER=archon -DINSTRUMENT=hispec_tracking_camera
   make

Archon & Network Setup
~~~~~~~~~~~~~~~~~~~~~~

Refer to the primary Archon GUI documentation: `archongui.rst <archongui.rst>`_

1. Open Ubuntu Network Settings.
2. Select Ethernet controller **enp202s0f0np0** gear icon $\rightarrow$ IPv4 tab.
3. Configure **Manual** IPv4 address:
   - **Address:** ``10.0.0.10``
   - **Netmask:** ``255.255.255.0``
   - **Gateway:** ``10.0.0.1``
4. Add host entry in ``/etc/hosts``:

.. code-block:: text

   10.0.0.2 archon

5. Connect Archon hardware to the fiber port labeled **archon** and verify link:

  .. code-block:: bash

     ping archon

System & Real-Time Optimizations
--------------------------------

Services Management
~~~~~~~~~~~~~~~~~~~

Disable unnecessary background daemons and automatic updates:

  .. code-block:: bash

   sudo systemctl disable cups.service
   sudo systemctl disable cups-browsed.service
   sudo systemctl disable ModemManager.service
   sudo systemctl disable apt-daily.timer
   sudo systemctl disable apt-daily-upgrade.timer
   sudo systemctl disable avahi-daemon.service

Real-Time Scheduling
~~~~~~~~~~~~~~~~~~~~

Allow non-root processes to use FIFO real-time priority scheduling:

.. code-block:: bash

   sudo setcap 'cap_sys_nice=eip' <path/to/chrt>
   chrt -f 60 ./<executable file>

CPU Core Isolation & Isolation Profile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reserve dedicated physical CPU cores for time-critical processing (e.g., CameraD):

1. Install cpuset management utility:

  .. code-block:: bash

     sudo apt install cset

2. Configure bootloader parameters in ``/etc/default/grub`` to isolate physical cores 11–15:

.. code-block:: text

   GRUB_CMDLINE_LINUX_DEFAULT="quiet splash isolcpus=11-15 nohz_full=11-15 rcu_nocbs=11-15 rcu_nocb_poll"

3. Apply GRUB configuration:

.. code-block:: bash

   sudo update-grub

BIOS Configuration Checklist
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Reboot system and enter BIOS utility (typically ``F2``, ``Del``, or ``Esc``).
2. Locate CPU settings (e.g., *Intel Hyper-Threading*, *SMT*, or *Logical Processors*).
3. Set option to **Disabled** to ensure deterministic execution per physical core.

Troubleshooting
---------------

- **Qt5 Discovery:** If Ubuntu fails to detect Qt5 or defaults to an older Qt4 installation, run:

  .. code-block:: bash

     sudo apt install qt5-default

- **FT4222 USB Access Failures:**
  - Verify USB connection via ``lsusb`` looking for Vendor ID ``0403:601c``.
  - Check program invocation privileges (must have udev rules configured or run with ``sudo``).
- **FT4222 ABI Mismatch:** Ensure system ``glibc`` version is $\ge 2.10$.
- **SPI Master Mode:** Verify the Slave Select (SS) line is pulled high.

Final Step
----------

Reboot the machine to apply kernel parameter changes, BIOS optimizations, service disablement, and udev rule updates:

.. code-block:: bash

   sudo reboot

Done!