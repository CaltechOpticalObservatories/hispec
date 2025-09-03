Build Setup for hsdev FEI
=========================

System Requirements
-------------------

- OS: Ubuntu 24.04 LTS
- Linux: Current Kernel version Linux 6.8.0 (-59 Ubuntu)
- Python: 3.12 (required)


User Setup
==========

Create a development user ``hsdev`` and facility user ``hispecfei``:

.. code-block:: bash

   sudo adduser hsdev
   sudo adduser hispecfei
   sudo usermod -aG sudo hsdev
   sudo usermod -aG sudo hispecfei
   sudo usermod -aG dialout hsdev  # Add serial access group
   sudo usermod -aG dialout hispecfei
   # requires logout/login to apply changes using usermod


Group and Account Setup
=======================

Create required groups for HISPEC development:

.. code-block:: bash

   sudo groupadd hispec
   sudo groupadd instr

Add development user ``hsdev`` to these groups:

.. code-block:: bash

   sudo usermod -aG hispec hsdev
   sudo usermod -aG instr hsdev

Create standard HISPEC accounts (if not already provisioned):

.. code-block:: bash

   sudo adduser hispec
   sudo adduser hispecbld
   sudo adduser hispeceng
   sudo adduser hispecrun

   # Batch create numbered accounts hispec1 through hispec9
   for i in $(seq 1 9); do
       sudo adduser hispec$i
   done

- Instant change in group for current terminal session:

  .. code-block:: bash

     newgrp dialout


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
       libcfitsio-dev \
       cmake \
       libzmq3-dev \
       net-tools \
       htop

Disable unnecessary services:

.. code-block:: bash

   sudo systemctl disable cups.service                # printing
   sudo systemctl disable cups-browsed.service        # printing
   sudo systemctl disable ModemManager.service
   sudo systemctl disable apt-daily.timer             # automatic updates
   sudo systemctl disable apt-daily-upgrade.timer     # automatic updates
   sudo systemctl disable avahi-daemon.service        # zeroconf mDNS


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
       python3.12-venv \
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

Check version:

.. code-block:: bash

   python3 --version
   # Expected: Python 3.12.3 => must be < Python 3.13

If you need to install Python, build from source:

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

   # Inside /home/hsdev
   python3.12 -m venv fei-venv
   source ~/fei-venv/bin/activate
   pip install numpy matplotlib pipython


Download Needed Drivers (and Software)
--------------------------------------

**Physik Instrumente**

Go to the PI website, fill out the form, and download the latest driver package for your OS.  
For Linux, you can find it here: https://www.physikinstrumente.com/en/products/software-suite

   i. Unpack the downloaded archive  
   ii. In a terminal window, navigate to the unpacked directory  
   iii. Run the installation script:

   .. code-block:: bash

      cd <path_to_unpacked_PI_driver>
      sudo ./INSTALL

   iv. Follow the on-screen instructions to complete the installation.  
   v. Specific answers to questions during installation:
      - **Do you agree to the General Software License Agreement? [yn]:** y
      - **{shows full License Agreement}** q
      - **Install the PI ${PI_PRODUCT_NAME} high level GCS library? [ynq]:** y
      - **To enable the access rights to a user group now press 'y'** y
      - **Enable the access rights to a user group now? [ynq]:** y
      - **{shows full License Agreement}** n
      - **Install ${PIPython} now? [ynq]:** n
      - **Install ${PI Terminal} now? [ynq]:** y
      - **Please enter the name of the user group ...:** dialout


**SPI Driver lib4222**

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

3. Detailed build instructions:

   i. Change to the examples directory:

   .. code-block:: bash

      cd examples

   ii. Build an executable:

   For **dynamic library**:

   .. code-block:: bash

      sudo cc get-version.c -lft4222 -Wl,-rpath,/usr/local/lib

   For **static library**:

   .. code-block:: bash

      sudo cc -static get-version.c -lft4222 -Wl,-rpath,/usr/local/lib -ldl -lpthread -lrt -lstdc++

   If your ``ld`` version is too old, static build may fail. To resolve:

   .. code-block:: bash

      sudo apt-get update
      sudo apt-get install binutils-2.26
      export PATH="/usr/lib/binutils-2.26/bin:$PATH"

   iii. Run the executable:

   .. code-block:: bash

      sudo ./a.out

   You should see output similar to:

   .. code-block:: text

      Chip version: 42220400, LibFT4222 version: 010404E8

   If you see:

   - **"No devices connected"** or **"No FT4222H detected"**:
     
     - There may be no FT4222H connected. Run ``lsusb`` and check for something like:

       .. code-block:: text

          Bus 001 Device 005: ID 0403:601c Future Technology Devices International, Ltd

     - Or your program lacks USB access. Use ``sudo``, ``su``, or run as root.

   - **ABI mismatch error (libft4222.so):** Try upgrading ``glibc`` to version 2.10 or newer.
   - **SPI Mode Note:** If enabling SPI master mode, the SS pin **must be tied high**.


**CameraD Installation**

.. code-block:: bash

   cd ~
   git clone https://github.com/CaltechOpticalObservatories/camera-interface.git
   cd camera-interface
   cd build
   rm -rf ./*  # Clean any previous contents
   cmake ..
   make


**Archon + GUI Installation**

LINK to Archon GUI Installation instructions: `archongui.rst <archongui.rst>`_

- Configure Archon  
  1. Open Ubuntu settings  
  2. Click "Network"  
  3. Look for “Ethernet enp202s0f0np0” and click the gear icon  
  4. Go to the IPV4 tab  
  5. Change the IPV4 Method to "Manual"  
  6. Set the address to ``10.0.0.10``, netmask to ``255.255.255.0`` and the gateway to ``10.0.0.1``  
  7. Hit the "Apply" button  
  8. Add ``10.0.0.2 archon`` to ``/etc/hosts``

- NOTE: Archon must be plugged into the correct fiber port (labeled "archon").

- Test Archon connection:

  .. code-block:: bash

     ping archon

  You should see replies from the Archon.


Troubleshooting
---------------

- If Ubuntu doesn’t find Qt5 or if you previously had Qt4 installed, run:

  .. code-block:: bash

     sudo apt install qt5-default


OS Optimization Notes (07/09/2025)
----------------------------------

**Real-Time Scheduling and Process Prioritization**

- Use ``chrt`` to assign real-time priorities to time-critical processes.
- Allow ``chrt`` to be run without sudo for selected processes by modifying security policies (e.g., with setcap or via sudoers).
- Commonly used priority: FIFO scheduling with priority 60.

.. code-block:: bash

   sudo setcap 'cap_sys_nice=eip' <path/to/chrt>
   chrt -f 60 ./<executable file>

**CPU Isolation**

- Install and use cset (CPUSET) for isolating CPU cores:

  .. code-block:: bash

     sudo apt install cset

- Dedicated physical CPU cores (no SMT/hyperthreading):  
  - Total cores: 16  
  - Isolated cores for CameraD: 11–15  
  - Remaining cores (0–10): Available for other system tasks  
  - Disable hyperthreading/SMT in BIOS for deterministic performance.

**GRUB Boot Optimization**

- Edit ``/etc/default/grub`` to add kernel boot parameters:

  .. code-block:: bash

     GRUB_CMDLINE_LINUX_DEFAULT="quiet splash isolcpus=11-15 nohz_full=11-15 rcu_nocbs=11-15 rcu_nocb_poll"
     sudo update-grub

**BIOS Changes**

- Save any work and restart the machine  
- Press BIOS key during initial logo screen (typically Esc, F2, or Del)  
- Navigate to BIOS menu (use Enter to select, Esc to go back)

  **Changes:**
  - Look for Intel Hyper-Threading, SMT, or Logical Processor  
  - Set to Disabled

.. note::

   For CameraD, change to FIFO process scheduling for those threads.


Final Step
==========

**RESTART/REBOOT** the server to complete driver installation and apply CPU/OS optimization changes.


Done!
=====
