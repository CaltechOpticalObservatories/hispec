===========================================
Build Setup for hsdev User
===========================================

System Requirements
-------------------

- OS: Ubuntu 24.04 LTS (Noble Numbat)
- Python: 3.12 (Default system version)

Initial OS User
---------------

The target machine is initially provisioned during the OS installation with the primary administrative user:

- **Primary User:** ``hispec`` (with sudo privileges)

Development User & Group Setup
------------------------------

Create required groups for HISPEC engineering and development:

.. code-block:: bash

   sudo groupadd -f hispec
   sudo groupadd -f eng

Set up the secondary development user ``hsdev`` and assign appropriate group memberships:

.. code-block:: bash

   sudo adduser hsdev
   sudo usermod -aG sudo,dialout,hispec,eng hsdev

.. note::
   The following block provisions secondary accounts non-interactively. Since ``hispec`` is created during initial OS installation and ``hsdev`` is created above, the script gracefully skips pre-existing accounts while ensuring any missing target accounts are safely created.

.. code-block:: bash

   for u in hispec hsdev; do
       sudo useradd -m -s /bin/bash "$u" 2>/dev/null || true
   done

System Package Installation
---------------------------

Update package list and install essential build tools and dependencies:

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
     libc6-dev-i386 \
     snmp \
     flex flex-doc bison bison-doc \
     pandoc groff rst2pdf

KROOT Specific Packages
~~~~~~~~~~~~~~~~~~~~~~~

Packages required for KROOT environments:

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   sudo apt install -y \
     libboost-all-dev \
     libopencv-dev \
     libccfits-dev \
     libcfitsio-dev

Python Environment Setup
------------------------

Global Shared Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a centralized, read-only-for-engineers virtual environment under ``/opt/hispec/env``. 
This environment houses the official deployed packages used across the instrument framework.

Execute as the primary ``hispec`` user:

.. code-block:: bash

   # Create global directory and virtual environment
   sudo mkdir -p /opt/hispec
   sudo python3 -m venv /opt/hispec/env

   # Set ownership: owned by 'hispec', group-accessible by 'eng'
   sudo chown -R hispec:eng /opt/hispec
   sudo chmod -R 775 /opt/hispec

   # Install canonical deployed packages into global environment
   /opt/hispec/env/bin/pip install --upgrade pip
   /opt/hispec/env/bin/pip install numpy matplotlib pipython

To make the global environment active by default for all session shells, add the activation hook to system or user bash profiles:

.. code-block:: bash

   echo 'source /opt/hispec/env/bin/activate' >> /home/hsdev/.bashrc

Local Engineer Virtual Environments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Engineers working under ``hsdev`` (or individual local accounts) can spin up isolated, lightweight local virtual environments for feature development.

Option A: Inherit Deployed Global Packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To inherit all pre-installed packages from the global environment while allowing local testing:

.. code-block:: bash

   python3 -m venv --system-site-packages ~/env
   source ~/env/bin/activate

Option B: Isolated Sandbox
^^^^^^^^^^^^^^^^^^^^^^^^^^

To build an isolated sandbox independent of the deployed environment:

.. code-block:: bash

   python3 -m venv ~/env_sandbox
   source ~/env_sandbox/bin/activate
   pip install --upgrade pip
Update Hosts File
-----------------

Edit ``/etc/hosts`` to include the private network entries for HISPEC, ordered numerically by IP address:

.. code-block:: text

   192.168.29.100 feilantronix
   192.168.29.101 switch
   192.168.29.102 feieaton1
   192.168.29.104 feilakeshore
   192.168.29.105 feieaton2
   192.168.29.106 feieaton3
   192.168.29.120 feiinficon
   192.168.29.125 blueinficon
   192.168.29.150 blueettemp
   192.168.29.151 blueeaton1
   192.168.29.152 blueeaton2
   192.168.29.153 bluelantronix
   192.168.29.154 hs1wireblue

Disable Unnecessary Services
----------------------------

Disable unused background services in headless/development setups:

.. code-block:: bash

   sudo systemctl disable cups.service              # Printing
   sudo systemctl disable cups-browsed.service      # Printing browsing
   sudo systemctl disable ModemManager.service      # Modem management
   sudo systemctl disable apt-daily.timer           # Automatic updates
   sudo systemctl disable apt-daily-upgrade.timer   # Background upgrades
   sudo systemctl disable avahi-daemon.service      # Zeroconf mDNS

Done!
-----

System setup prepared for ``Ubuntu 24.04 LTS`` under user ``hsdev``.