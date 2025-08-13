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
        libcfitsio-dev \
        net-tools \
        htop

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

    # Inside /home/hsdev
    python3.12 -m venv fei-venv
    source ~/fei-venv/bin/activate
    pip install numpy matplotlib pipython

Download Needed Drivers (and Software)
------------------------------------------------

**Physik Instrumente**
Go to the PI website, fill out the form and download the latest driver package for your OS. For Linux, you can find it here: https://www.physikinstrumente.com/en/products/software-suite
    i. Unpack the downloaded archive
    ii. In a terminal window, navigate to the unpacked directory
    iii. Run the installation script:

    .. code-block:: bash

        cd <path_to_unpacked_PI_driver> #hsdev@hsdev:~/Downloads/PI-Software-Suite-C-990.CD1/Linux/PI_Application_Software-1.22.0.2-INSTALL/PI_Application_Software
        sudo ./INSTALL

    iv. Follow the on-screen instructions to complete the installation. 
    v. Specific answers to questions during installation:
       - **Do you agree to the General Software License Agreement? [yn]:**: y
       - **{shows full License Agreement}**: q
       - **Install the PI ${PI_PRODUCT_NAME} high level GCS library? [ynq]:**: y
       - **To enable the access rights to a user group now press 'y'**: y
       - **Enable the access rights to a user group now? [ynq]::**: y
       - **{shows full License Agreement}**: n
       - **Install ${PIPython} now? [ynq]:**: n
       - **Install ${PI Terminal} now? [ynq]:**: y
       - **Please enter the name of the user group for which you would like to enable the access rights to the ${PI_PRODUCT_NAME}. Enter empty string to abort:**: dialout

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

   This installs the dynamic library. It copies `libft4222.so.1.4.4.232` and headers to
   `/usr/local/lib` and `/usr/local/include` respectively. It also creates a 
   version-independent symbolic link, `libft4222.so`.

3. Detailed Build Instructions:

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

   If your `ld` version is too old, static build may fail. To resolve:

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
     
     - There may be no FT4222H connected. Run `lsusb` and check for something like:

       .. code-block:: text

          Bus 001 Device 005: ID 0403:601c Future Technology Devices International, Ltd

     - Or your program lacks USB access. Use `sudo`, `su`, or run as root.

   - **ABI mismatch error (libft4222.so):** Try upgrading `glibc` to version 2.10 or newer.

   - **SPI Mode Note:** If enabling SPI master mode, the SS pin **must be tied high**.


- Permanent dialout access for user across machine (requires logout/login):

  .. code-block:: bash

      sudo usermod -a -G dialout hsdev

- Instant change in group for current terminal session:

  .. code-block:: bash

      newgrp dialout

**CameraD Installation**
   .. code-block:: bash

    cd ~
    git clone https://github.com/CaltechOpticalObservatories/camera-interface.git
    cd camera-interface
    cd build
    rm -rf ./*  # Clean any previous contents
    cmake ..
    make

**Archon GUI Installation**
1. **Download** the Archon GUI source code from the STA website and extract the zip file:

   http://www.sta-inc.net/archon/

   Direct link for the source code (currently):

   http://www.sta-inc.net/archongui

2. **Install Qt5**:

   .. code-block:: bash

      sudo apt install qt5-qmake qtbase5-dev qtbase5-dev-tools qtchooser

3. **Install Qt5 SVG libraries**:

   .. code-block:: bash

      sudo apt install libqt5svg5*

4. **Navigate to the extracted Archon GUI source code**:

   .. code-block:: bash

      cd ~/<apps,downloads,documents,etc.>/archongui

5. **Prepare the Qt project for building**:

   .. code-block:: bash

      qmake archongui.pro

6. **Build the binary**:

   .. code-block:: bash

      make

7. **Run the GUI**:

   .. code-block:: bash
      # from inside the archongui directory
      ./release/archongui


**Troubleshooting**

- If Ubuntu doesn’t find Qt5 or if you previously had Qt4 installed, run:

  .. code-block:: bash

     sudo apt install qt5-default

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
