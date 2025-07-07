===========================================
Build Setup for hsdev User
===========================================

System Requirements
====================

- OS: Ubuntu 24.04 LTS
- Python: 3.9 (required)

User Setup
==========

Create a development user ``hsdev``:

.. code-block:: bash

   sudo adduser hsdev
   sudo usermod -aG sudo hsdev
   sudo usermod -aG dialout hsdev  # Add serial access group

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
     python3-pip

KROOT Specific Packages
--------------------------

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

Python 3.9 Installation
=======================

Ubuntu 24.04 ships with Python 3.12. Install Python 3.9 using one of the methods below:

Option 1: Build from Source
---------------------------

.. code-block:: bash

   cd /usr/src
   sudo wget https://www.python.org/ftp/python/3.9.19/Python-3.9.19.tgz
   sudo tar xzf Python-3.9.19.tgz
   cd Python-3.9.19
   sudo ./configure --enable-optimizations
   sudo make -j $(nproc)
   sudo make altinstall  # Installs as python3.9

Option 2: Use Deadsnakes PPA (if available for 24.04)
-----------------------------------------------------

.. code-block:: bash

   sudo add-apt-repository ppa:deadsnakes/ppa
   sudo apt update
   sudo apt install -y python3.9 python3.9-venv python3.9-dev

Python Package Installation
===========================

Install required Python packages using ``pip``:

.. code-block:: bash

   python3.9 -m pip install --upgrade pip
   python3.9 -m pip install numpy matplotlib pipython

Verify installation:

.. code-block:: bash

   python3.9 --version
   pip3.9 list

Optional: Virtual Environment
=============================

Create and activate a virtual environment:

.. code-block:: bash

   python3.9 -m venv ~/env
   source ~/env/bin/activate
   pip install numpy matplotlib pipython

Done!
=====
