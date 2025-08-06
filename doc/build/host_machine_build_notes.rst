===========================================
Build Setup for hsdev User
===========================================

System Requirements
====================

- OS: Ubuntu 24.04 LTS
- Python: 3.12 (default system version)

User Setup
==========

Create a development user ``hsdev``:

.. code-block:: bash

   sudo adduser hsdev
   sudo usermod -aG sudo hsdev
   sudo usermod -aG dialout hsdev  # Add serial access group

Group and Account Setup
========================

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

System Package Installation
===========================

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
     python3-venv \
     python3-dev \
     python3-docutils \
     python3-tk \
     python3-pil.imagetk \
     pyqt5-dev-tools \
     make m4 autoconf \
     xorg-dev xaw3dg-dev \
     libmotif-dev \
     lib32c-dev \
     snmp \
     flex flex-doc bison bison-doc \
     pandoc groff rst2pdf

KROOT Specific Packages
--------------------------

These packages are needed for KROOT environments:

.. code-block:: bash

   sudo apt install -y \
     openconnect \
     subversion cvs at \
     libxt-dev libncurses-dev \
     tcl tcl-dev tcl-thread tcllib tk tk-dev expect \
     tclx tcl-fitstcl libpq-dev \
     g++ gfortran \
     libpam-dev \
     python3-ephem

Additional Instrument Development Packages
------------------------------------------

.. code-block:: bash

   sudo apt install -y \
     libboost-all-dev \
     libopencv-dev \
     libccfits-dev \
     libcfitsio-dev

Python Package Installation
===========================

Use Python 3.12 (default) and install required Python packages:

.. code-block:: bash

   python3 -m pip install --upgrade pip
   python3 -m pip install numpy matplotlib pipython

Verify installation:

.. code-block:: bash

   python3 --version
   pip3 list

Optional: Virtual Environment
=============================

Create and activate a virtual environment:

.. code-block:: bash

   python3 -m venv ~/env
   source ~/env/bin/activate
   pip install numpy matplotlib pipython

Directory Structure
===================

The following directory structure is recommended:

::

   /home/hsdev/
   ├── external/   # Third-party development-only software (not instrument delivery)
   └── svn/        # SVN working copy for KROOT

Create the directories:

.. code-block:: bash

   mkdir -p /home/hsdev/external
   mkdir -p /home/hsdev/svn
   chown -R hsdev:hsdev /home/hsdev/external /home/hsdev/svn

External Development Libraries
==============================

For third-party libraries, build and install them under ``/home/hsdev/external``:

.. code-block:: bash

   cd /home/hsdev/external
   wget http://example.com/3rdparty.tar.gz
   tar -xzvf 3rdparty.tar.gz
   cd 3rdparty
   ./configure --prefix=/home/hsdev/external/3rdparty
   make && make install

Disable Unnecessary Services
============================

To reduce background system noise or services not needed in headless/dev setups:

.. code-block:: bash

   sudo systemctl disable cups.service              # Printing
   sudo systemctl disable cups-browsed.service      # Printing browsing
   sudo systemctl disable ModemManager.service      # Modem management
   sudo systemctl disable apt-daily.timer           # Automatic updates
   sudo systemctl disable apt-daily-upgrade.timer   # Background upgrades
   sudo systemctl disable avahi-daemon.service      # Zeroconf mDNS

Done!
=====

System is now prepared for development under the ``hsdev`` user.
