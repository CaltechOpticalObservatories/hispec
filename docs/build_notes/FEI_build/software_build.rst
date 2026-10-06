=======================================================
Software Build: Packages, Python, Drivers and Utilities
=======================================================

:Prerequisite: :doc:`rt_build` complete and verified
:Next: run :ref:`section-sw-verify`, then the instrument is ready

.. contents::
   :depth: 1
   :local:

Install only what the instrument needs. GUIs are not run locally; they are
exported over SSH or VNC and plots are written to disk.

----

.. _section-packages:

1. System Packages
==================

Core Build and Runtime
----------------------

.. code-block:: bash

   sudo apt update
   sudo apt install -y \
       build-essential \
       cmake \
       git \
       pkg-config \
       software-properties-common \
       wget curl \
       net-tools iproute2 \
       htop \
       tmux \
       rsync \
       libffi-dev libssl-dev zlib1g-dev libbz2-dev liblzma-dev \
       libreadline-dev libsqlite3-dev libncursesw5-dev \
       libxml2-dev libxmlsec1-dev xz-utils llvm \
       python3-pip python3-dev python3-venv \
       libboost-all-dev \
       libcfitsio-dev libccfits-dev \
       libopencv-dev \
       libzmq3-dev

Headless GUI Export
-------------------

Minimal X client libraries and a lightweight window manager. **No display
manager, no desktop environment.**

.. code-block:: bash

   sudo apt install -y \
       xauth x11-apps x11-utils \
       tigervnc-standalone-server tigervnc-common \
       openbox \
       xterm \
       fonts-dejavu-core

.. note::
   Without ``xauth``, ``ssh -X`` silently fails to set ``$DISPLAY`` and every
   remote GUI dies with ``cannot open display``.

Qt Runtime (only if Qt GUIs run here)
-------------------------------------

Prefer running Qt GUIs on an operator workstation.

.. code-block:: bash

   sudo apt install -y \
       python3-pyqt5 \
       qtbase5-dev qtbase5-dev-tools \
       libxcb-xinerama0 libxkbcommon-x11-0

.. warning::
   ``qt5-default`` does not exist on Ubuntu 26.04. Use ``qtbase5-dev`` and set
   ``QT_SELECT=5`` if a legacy build script demands it.

----

.. _section-python:

2. Python Environment
=====================

Shared Virtual Environment
--------------------------

A deployment environment at ``/opt/hispecfei/env``, owned by ``hsfei``.
Python **3.14** ships with 26.04 and is the required version.

.. code-block:: bash

   sudo mkdir -p /opt/hispecfei
   sudo python3 -m venv /opt/hispecfei/env
   sudo chown -R hsfei:hsfei /opt/hispecfei
   sudo chmod -R 775 /opt/hispecfei
   sudo chmod g+s /opt/hispecfei

   /opt/hispecfei/env/bin/python -m pip install --upgrade pip setuptools wheel
   /opt/hispecfei/env/bin/python -m pip install \
       numpy \
       scipy \
       matplotlib \
       astropy \
       pandas \
       pyserial \
       pipython \
       pyzmq

   echo 'source /opt/hispecfei/env/bin/activate' >> /home/hsfei/.bashrc

.. warning::
   * Install ``pyserial`` (imported as ``serial``). The PyPI package ``serial``
     is an unrelated project.
   * Do not ``pip install cmake``; it shadows the ``apt`` version on ``PATH``.
   * ``PyQt5`` comes from ``apt``, not the venv.

Headless Matplotlib
-------------------

Force the non-interactive backend so scripts never block on ``$DISPLAY``:

.. code-block:: bash

   sudo tee /etc/profile.d/mpl-headless.sh > /dev/null <<'EOF'
   export MPLBACKEND=Agg
   EOF

Override when tunnelling a GUI: ``MPLBACKEND=Qt5Agg python plot.py``.

----

.. _section-remote-gui:

3. Remote GUI and Plot Access
=============================

Preferred: write plots, FITS previews and diagnostics to disk and pull them:

.. code-block:: bash

   rsync -avz hsfei@hispecfei:/data/plots/ ./plots/
   scp hsfei@hispecfei:/data/frames/latest.fits .

Occasional GUI applications:

.. code-block:: bash

   ssh -X hsfei@hispecfei

For persistent graphical sessions, use TigerVNC over an SSH tunnel.

.. warning::
   Never expose VNC ports to the network. Use ``-localhost yes`` and SSH port
   forwarding only, and keep the VNC server off cores 0-5
   (:ref:`section-rt-placement`).

----

.. _section-drivers:

4. Hardware Drivers and Libraries
=================================

Physik Instrumente (PI) Driver
------------------------------

#. Download the Linux driver package from the `PI Software Suite
   <https://www.physikinstrumente.com/en/products/software-suite>`_ on a
   workstation and ``scp`` it over.
#. Extract and run the installer:

   .. code-block:: bash

      cd <path_to_unpacked_PI_driver>
      sudo ./INSTALL

#. Installer prompts:

   .. list-table::
      :header-rows: 1
      :widths: 65 15

      * - Prompt
        - Answer
      * - Do you agree to the General Software License Agreement? [yn]
        - ``y``
      * - *(license text shown in pager)*
        - ``q``
      * - Install the PI ``${PI_PRODUCT_NAME}`` high level GCS library? [ynq]
        - ``y``
      * - To enable the access rights to a user group now press 'y'
        - ``y``
      * - Enable the access rights to a user group now? [ynq]
        - ``y``
      * - *(license text shown again)*
        - ``n``
      * - Install ``${PIPython}`` now? [ynq]
        - ``n``
      * - Install ``${PI Terminal}`` now? [ynq]
        - ``y``
      * - Please enter the name of the user group ...
        - ``dialout``

``PIPython`` is declined here because it is installed into the venv
(:ref:`section-python`).

SPI Driver (libft4222)
----------------------

#. Extract and install:

   .. code-block:: bash

      tar xfvz libft4222-1.4.4.232.tgz
      sudo ./install4222.sh
      sudo ldconfig
      ldconfig -p | grep ft4222

   This installs ``libft4222.so`` to ``/usr/local/lib`` and headers to
   ``/usr/local/include``.

#. Build and run the test binary (no ``sudo`` needed):

   .. code-block:: bash

      cd examples
      cc get-version.c -lft4222 -Wl,-rpath,/usr/local/lib -o ft4222-version
      ./ft4222-version

   Expected: ``Chip version: 42220400, LibFT4222 version: 010404E8``

.. note::
   Link dynamically. If a static build is needed:
   ``cc -static get-version.c -lft4222 -ldl -lpthread -lrt -lstdc++ -o ft4222-version-static``.
   Ignore old advice to install ``binutils-2.26``; it does not exist on 26.04.

.. _section-ft4222-udev:

FT4222 udev Rules
-----------------

#. Create ``/etc/udev/rules.d/99_HISPEC_spi_ftdi_4222.rules``:

   .. code-block:: text

      SUBSYSTEM=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="601c", OWNER="hsdev", MODE="0660", GROUP="dialout"

#. Reload, replug the board, and verify:

   .. code-block:: bash

      sudo udevadm control --reload-rules
      sudo udevadm trigger
      ls -l /dev/bus/usb/*/* | grep -i 0403   # hsdev dialout 0660

.. note::
   **SPI master mode:** the Slave Select (SS) pin **must be tied high**.

CameraD (camera-interface)
--------------------------

.. code-block:: bash

   cd ~
   git clone https://github.com/CaltechOpticalObservatories/camera-interface.git
   cd camera-interface/build
   rm -rf ./*
   cmake .. -DCONTROLLER=archon -DINSTRUMENT=hispec_tracking_camera
   taskset -c 6-13 make -j8

   # Record in the as-built log
   git -C ~/camera-interface rev-parse --short HEAD

See ``archongui.rst`` for Archon-side configuration.

----

.. _section-rt-placement:

5. Real-Time Process Placement
==============================

Only instrument code runs on the shielded cores 0-5. RT privileges are set up
in :ref:`section-rt-privileges`.

.. code-block:: bash

   # Direct affinity
   taskset -c 0-5 chrt -f 80 ./camerad

   # Or via cpuset shielding
   sudo cset shield --cpu 0-5 --kthread=on
   sudo cset shield --exec -- chrt -f 80 ./camerad
   sudo cset shield --reset      # tear down

Must never run on cores 0-5: VNC / Xvnc / Openbox, SSH sessions and shells,
``rsync`` / ``scp``, monitoring tools, and compilation.

Keep login shells off the shielded cores by adding to ``~/.bashrc``:

.. code-block:: bash

   taskset -cp 6-13 $$ > /dev/null 2>&1

----

.. _section-sw-verify:

6. Final Reboot and Verification
================================

.. code-block:: bash

   sudo reboot

.. list-table::
   :header-rows: 1
   :widths: 25 50 25

   * - Check
     - Command
     - Expected
   * - Python
     - ``/opt/hispecfei/env/bin/python -V``
     - ``3.14.x``
   * - FT4222
     - ``./ft4222-version``
     - ``Chip version: 42220400``
   * - udev perms
     - ``ls -l /dev/bus/usb/*/* | grep 0403``
     - ``hsdev dialout 0660``
   * - X11 forward
     - ``ssh -X hsdev@hispecfei xeyes``
     - window appears
   * - VNC pinning
     - ``taskset -cp $(pgrep Xvnc)``
     - **not** 0-5

Re-run the latency baseline (:ref:`section-verify`) with the instrument
software running.

----

7. Troubleshooting
==================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Symptom
     - Resolution
   * - ``cannot open display`` over SSH
     - Install ``xauth``; confirm ``X11Forwarding yes`` in ``sshd_config``;
       connect with ``ssh -X``. Do not set ``$DISPLAY`` manually.
   * - ``ssh -X`` fails, ``-Y`` works
     - Untrusted-X restriction. Acceptable on a trusted LAN.
   * - VNC shows a grey screen
     - ``~/.vnc/xstartup`` not executable or ``openbox`` missing. Check
       ``~/.vnc/*.log``.
   * - VNC refuses remote connections
     - Expected with ``-localhost yes``. Use the SSH tunnel.
   * - Qt: ``could not load the Qt platform plugin "xcb"``
     - Install ``libxcb-xinerama0`` and ``libxkbcommon-x11-0``. Debug with
       ``QT_DEBUG_PLUGINS=1``.
   * - Matplotlib fails with no display
     - Check ``echo $MPLBACKEND`` is ``Agg`` (:ref:`section-python`).
   * - ``import serial`` fails
     - Install ``pyserial``, not ``serial``.
   * - FT4222 not found
     - ``lsusb`` for ``0403:601c``. Absent: cable/board problem. Present but
       inaccessible: reload udev rules and replug (:ref:`section-ft4222-udev`).
   * - FT4222 ABI mismatch on ``libft4222.so``
     - Usually a stale ``.so`` in ``/usr/local/lib``. Remove old copies and run
       ``sudo ldconfig``.
   * - SPI master mode misbehaves
     - Slave Select (SS) must be tied **high**.

----

8. Pending Tasks
================

* [ ] **VNC setup**: document the pinned TigerVNC unit and ``xstartup``.
* [ ] **Software stack**: track upstream GitHub build notes for Python
  libraries, C++ sources and hardware drivers.

----

9. References
=============

* ``archongui.rst``: Archon GUI and controller configuration
* `camera-interface <https://github.com/CaltechOpticalObservatories/camera-interface>`_
* `Physik Instrumente Software Suite <https://www.physikinstrumente.com/en/products/software-suite>`_
