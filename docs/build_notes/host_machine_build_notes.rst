===========================================
Build Setup for HISPEC and HSDEV User
===========================================

System Requirements
-------------------

- OS: Ubuntu 24.04 LTS (Noble Numbat)
- Python: 3.12 (Default system version)

Users
-----

Create ``hsdev`` as the administrative user during the OS installation, then
give it serial access:

.. code-block:: bash

   sudo usermod -aG dialout hsdev

Do not create a ``hispec`` login. The installer in
:ref:`section-host-hispec-software` creates ``hispec`` as the system account the
daemons run as, with no login shell, along with the ``hispec-ops`` group, and
enrols ``hsdev`` into that group.

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

.. _section-host-hispec-software:

HISPEC Software
---------------

Install the HISPEC software as described in :doc:`../install`, passing
``hsdev`` and every other operator to ``install.sh``. That page is also where
updating the host and enrolling operators are covered.

Update Hosts File
-----------------

Edit ``/etc/hosts`` to include the private network entries for HISPEC, ordered numerically by IP address:

.. code-block:: text

   192.168.29.2    hispecserver
   192.168.29.3    hispecserverlom
   192.168.29.4    specswitchspare
   192.168.29.100  feilantronix
   192.168.29.101  feiswitch
   192.168.29.102  feidcpdu2
   192.168.29.104  feilakeshore
   192.168.29.105  feieaton1
   192.168.29.106  feieaton2
   192.168.29.107  feifsm
   192.168.29.109  feitrackcomp
   192.168.29.110  feidcpdu1
   192.168.29.120  feiinficon
   192.168.29.122  tmpstanda
   192.168.29.123  redatten rediriscontroller
   192.168.29.125  blueinficon
   192.168.29.129  redswitch
   192.168.29.130  redlantronix
   192.168.29.131  specblueinficon
   192.168.29.132  specredinficon
   192.168.29.135  redinficon
   192.168.29.136  specredlakeshore
   192.168.29.140  hs1wirered
   192.168.29.145  host
   192.168.29.150  blueettemp
   192.168.29.151  blueeaton1
   192.168.29.152  blueeaton2
   192.168.29.153  bluelantronix
   192.168.29.154  hs1wireblue
   192.168.29.161  redlakeshore1
   192.168.29.162  redlakeshore2
   192.168.29.163  redeaton1
   192.168.29.164  redeaton2
   192.168.29.165  redettemp
   192.168.29.166  redeaton3
   192.168.29.171  specblueeaton
   192.168.29.177  specbluelakeshore
   192.168.29.181  specredeaton
   192.168.29.185  specredlakeshore

MQTT Broker Setup
-----------------

Install the Mosquitto broker and command-line clients, and enable the broker to start on boot:

.. code-block:: bash

   sudo apt install -y mosquitto mosquitto-clients
   sudo systemctl enable mosquitto

Configure the Listener
~~~~~~~~~~~~~~~~~~~~~~

Create ``/etc/mosquitto/conf.d/hispec.conf`` with the listener for the host the broker is served from:

.. code-block:: text

   listener 1883 hispec.caltech.edu
   allow_anonymous true

.. note::
   The listener address depends on where HISPEC is hosted. ``hispec.caltech.edu`` is the current host;
   replace it with the address of the machine running the broker.

Restart the broker to apply the configuration and confirm it is running:

.. code-block:: bash

   sudo systemctl restart mosquitto
   sudo systemctl status mosquitto

Test the Broker
~~~~~~~~~~~~~~~

In one terminal, subscribe to a test topic:

.. code-block:: bash

   mosquitto_sub -h hispec.caltech.edu -p 1883 -t "test/topic" -v

In a second terminal, publish a message to the same topic:

.. code-block:: bash

   mosquitto_pub -h hispec.caltech.edu -p 1883 -t "test/topic" -m "Hello"

The subscriber terminal should print:

.. code-block:: text

   test/topic Hello

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