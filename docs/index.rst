HISPEC Documentation
====================

HISPEC is a high-resolution near-infrared spectrograph for Keck Observatory.
This documentation site collects the instrument-control software notes, build
procedures, deployment references, and operational information needed by the
engineering team.

The current documentation is focused on host and subsystem build setup. Each
build note is maintained as its own page so the sidebar can link directly to
the relevant setup procedure.

Getting Started
---------------

Start with the host-machine build page when setting up a development or
deployment machine. Use the FEI server and RTC pages for subsystem-specific
installation and configuration details.

.. toctree::
   :caption: Build Notes
   :maxdepth: 1
   :titlesonly:

   Host Machine Build Setup <build_notes/host_machine_build_notes>
   FEI Server Build Setup <build_notes/fei_server_build_notes>
   TCC and Real-Time Kernel Build <build_notes/rtc_buildnote>

Planned Documentation Areas
---------------------------

These sections are placeholders for the next round of documentation pages:

* software architecture and daemon responsibilities
* configuration and deployment workflow
* hardware interface notes
* operations and troubleshooting procedures
* developer setup and contribution workflow
