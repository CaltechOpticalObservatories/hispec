===============================================
Tracking Camera: Install, Run and Change on fei
===============================================

:Prerequisite: :doc:`software_build` complete
:Host role: ``feiserver``

.. contents::
   :depth: 1
   :local:

----

1. What Runs
============

``hsfei_atcam`` (``daemons/generic/camera``) drives the H2RG on the Archon
through ``camera_interface_tracking``, a compiled module built from the private
`hispec-tracking-camera-instrument
<https://github.com/CaltechOpticalObservatories/hispec-tracking-camera-instrument>`_
against `camera-interface
<https://github.com/CaltechOpticalObservatories/camera-interface>`_. Each frame
goes to the ImageStreamIO stream ``hispec_tracking_camera`` in ``/dev/shm`` and,
with FITS on, to ``/opt/hispec/data``. `atlas
<https://github.com/CaltechOpticalObservatories/atlas>`_ views either.

A running ``hsfei_atcam`` holds the Archon, so nothing else can drive the
camera beside it, ``run_camerad_script.py`` included. Stop it first with
``hispec stop hsfei_atcam``.

----

2. Install
==========

.. code-block:: bash

   sudo /opt/hispec/app/systemd/install.sh hsfei --host-role feiserver

On the first run without ``--host-role``, ``install.sh`` asks for the role and
records it in ``/etc/hispec/host``; later runs read it from there. The
``feiserver`` role brings:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - What
     - Where
   * - ImageStreamIO, built when missing
     - ``/usr/local``
   * - The camera module (``atcam`` extra), built from the clone
     - ``/opt/hispec/extra/hispec-tracking-camera-instrument``
   * - atlas (``atlas`` extra), installed editable from the clone
     - ``/opt/hispec/extra/atlas``
   * - Plotting for the analysis scripts (``scripts`` extra)
     - ``/opt/hispec/venv``

``install.sh`` clones the two repos only when they are missing; an existing
clone is never pulled or reset, so edits in it survive every run.

Then create the image directory and deploy the daemon:

.. code-block:: bash

   sudo install -d -o hispec -g hispec-ops -m 2775 /opt/hispec/data
   hispec deploy hsfei_atcam

Check it:

.. code-block:: bash

   hispec status hsfei_atcam
   libby show hsfei.atcam.state       # idle
   atlas --profile hispec_fei         # needs ssh -Y

----

3. Changing the Camera Config
=============================

The daemon reads ``/opt/hispec/app/config/hsfei/hispecatc.cfg`` in place.
Edit it there, then ``hispec restart hsfei_atcam``. The keys usually changed:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Key
     - Effect
   * - ``FITS_ENABLED``
     - write FITS files, ``yes`` or ``no``
   * - ``FITS_OUTPUT_DIR``, ``FITS_AUTODIR``, ``FITS_BASENAME``
     - where FITS files go, in a ``YYYYMMDD`` subdirectory when ``FITS_AUTODIR=yes``
   * - ``SHM_ENABLED``, ``SHM_SEGMENT_NAME``, ``SHM_DIR``
     - the shared-memory stream readers attach to
   * - ``IMDIR``, ``BASENAME``
     - where camerad itself writes images
   * - ``LOGPATH``
     - camerad's log directory

Paths must stay outside ``/home`` and ``/tmp``, which the ``hispec@`` unit
hides. To keep an edit, save it with ``hispec hotfix "what you changed"``,
which commits it to a hotfix branch and opens a pull request.

----

4. Changing the Camera Software
===============================

Each clone in ``/opt/hispec/extra/`` replaces the GitHub build of its package:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Clone
     - After an edit
   * - ``hispec-tracking-camera-instrument``
     - ``sudo /opt/hispec/app/systemd/install.sh``, then ``hispec restart hsfei_atcam``
   * - ``camera-interface`` (opt in, below)
     - the same
   * - ``atlas``
     - restart ``atlas``

To change camera-interface too, clone it and re-run ``install.sh``, which then
builds the camera module against it:

.. code-block:: bash

   sudo git clone https://github.com/CaltechOpticalObservatories/camera-interface.git \
       /opt/hispec/extra/camera-interface
   sudo /opt/hispec/app/systemd/install.sh

Keep a change with a commit, push and pull request from inside the clone.
``hispec hotfix`` does not cover these repos, and the host's deploy key only
reads, so pushing needs your own GitHub account. ``hispec doctor`` lists each
clone with its branch and anything uncommitted or not on GitHub.

Edits to hispec or a driver under ``/opt/hispec/app`` follow
:doc:`../../install`: ``install.sh`` installs them as they are, and
``hispec hotfix`` sends a driver edit to the driver's own repository.

----

5. Troubleshooting
==================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Symptom
     - Resolution
   * - ``libby show`` fails with ``Connection refused``
     - The CLI defaults to a broker on ``localhost``. Point it at the shared one:
       ``mkdir -p ~/.libby && echo 'rabbitmq_url: amqp://hispec.caltech.edu' > ~/.libby/cli_config.yaml``
   * - ``run_camerad_script.py`` cannot reach the Archon
     - ``hsfei_atcam`` holds it: ``hispec stop hsfei_atcam`` first.
   * - The camera module fails to build: ImageStreamIO not found
     - Re-run ``install.sh``, which builds it when
       ``/usr/local/lib/cmake/ImageStreamIOConfig.cmake`` is missing.
