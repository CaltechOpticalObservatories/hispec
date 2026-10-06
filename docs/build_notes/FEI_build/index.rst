===========================================
HISPEC FEI Server: Headless Real-time Build
===========================================

:Authors: Elijah A-B, Dan Ech
:Date: 2026-10-07
:Hostname: ``hispecfei``
:User: ``hsfei``
:OS: Real-time Ubuntu 26.04 LTS (PREEMPT_RT via Ubuntu Pro)
:Supersedes: ``fei_server_build_notes.rst``, ``rtc_buildnote.rst``

A COTS ``x86_64`` server running a ``PREEMPT_RT`` kernel with Intel TCC, hard
CPU shielding and stripped services, dedicated to the camera/controller loop.
Follow the three parts in order:

#. **Physical build:** hardware assembly and modifications.
#. **RT build:** BIOS, TCC and hardware RAID, OS install, network, RT kernel and
   CPU shielding.
#. **Software build:** system packages, Python environment, drivers and
   instrument utilities.

.. toctree::
   :maxdepth: 1

   physical_build
   rt_build
   software_build
