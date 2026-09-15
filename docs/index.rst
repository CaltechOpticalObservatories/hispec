HISPEC Documentation
====================

HISPEC is a high-resolution near-infrared spectrograph for Keck Observatory.
This documentation site collects the instrument-control software notes, build
procedures, deployment references, and operational information needed by the
engineering team.

Getting Started
---------------

If you are new to the software, start with the :doc:`architecture overview
<architecture/overview>` to understand how the system fits together, then use
the :doc:`daemon inventory <architecture/daemons>` to find the piece you care
about.

If you are setting up a machine, start with the host-machine build page. Use
the FEI/RTC build page for subsystem-specific installation and configuration
details.

.. toctree::
   :caption: Architecture
   :maxdepth: 2

   architecture/index

.. toctree::
   :caption: Build Notes
   :maxdepth: 1
   :titlesonly:

   Host Machine Build Setup <build_notes/host_machine_build_notes>
   FEI Server and RTC Build <build_notes/fei_buildnote>

Planned Documentation Areas
---------------------------

These sections are placeholders for the next round of documentation pages:

* operations and troubleshooting procedures
* developer setup and contribution workflow
* hardware interface notes per subsystem
