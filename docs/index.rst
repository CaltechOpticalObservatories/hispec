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

If you are running the instrument, :doc:`running the daemons with systemd
<operations/systemd>` covers starting, stopping, watching and debugging them.

If you are setting up a machine, :doc:`install` is the one way to put the
software on it. The build notes cover the OS, packages and hardware for each
host.

.. toctree::
   :caption: Architecture
   :maxdepth: 2

   architecture/index

.. toctree::
   :caption: Operations
   :maxdepth: 2

   install
   operations/systemd

.. toctree::
   :caption: Build Notes
   :maxdepth: 1
   :titlesonly:

   Host Machine Build Setup <build_notes/host_machine_build_notes>
   FEI Server and RTC Build <build_notes/FEI_build/index>

Planned Documentation Areas
---------------------------

These sections are placeholders for the next round of documentation pages:

* developer setup and contribution workflow
* hardware interface notes per subsystem
