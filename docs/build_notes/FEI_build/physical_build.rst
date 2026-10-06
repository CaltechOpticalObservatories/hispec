==============================
Physical Build: Hardware Setup
==============================

:Next: :doc:`rt_build`

.. contents::
   :depth: 1
   :local:

----

1. Overview
===========

The FEI server is an **Advantech MIC-770 V3** with an Intel Core i5-13500E
(TCC-capable CPU and BIOS). Advantech offers this system pre-built to the full
spec below. We bought the base unit and installed the rest ourselves because of
the price and lead time of the pre-built option.

None of the hardware is modified. "Build" here means installing standard
components into the base unit. A pre-built unit to the same spec can skip this
page and start at :doc:`rt_build`.

Photos of the initial build: ``20260303_InitialComputerBuild``.

----

2. Bill of Materials
====================

See the Purchase Order for what came pre-installed with the base system.

.. list-table::
   :header-rows: 1
   :widths: 22 43 35

   * - Component
     - Part
     - Purpose
   * - Base system
     - Advantech MIC-770 V3
     - Chassis, motherboard, CPU, PSU
   * - CPU
     - Intel Core i5-13500E (13th Gen), 14 cores
     - Pre-installed. TCC support for real-time work
   * - Memory
     - 2 x 32 GB Crucial DDR5-4800 SODIMM (``CT2K32G48C50S5``), 64 GB total
     - System memory
   * - PCIe expansion
     - Advantech i-Module, 2-slot PCIe
     - Holds the RAID controller and fiber network card
   * - RAID controller
     - Broadcom MegaRAID 9520-2M2
     - Hardware RAID 1 for the boot volume
   * - Boot drives
     - 2 x Samsung 990 PRO 1 TB NVMe (``MZ-V9P1T0B/AM``)
     - Mounted on the RAID controller as a RAID 1 pair
   * - Data drive
     - Samsung 870 EVO 2 TB 2.5" SSD (``MZ-77E2T0B/AM``)
     - ``/data`` for frames and plots
   * - Fiber network card
     - NVIDIA Mellanox ConnectX-6 Lx (``MCX631102AN-ADAT``)
     - Dedicated fiber link to the Archon controller
   * - SPI interface
     - FTDI FT4222 board (USB ``0403:601c``)
     - SPI link to instrument hardware

Consumables: DDR thermal pads (one "Bottom", one thicker "Top"), CPU thermal
paste, and a spare pink thermal pad for the heat-fin block if needed.

.. note::
   **Reused NVMe drives:** the 990 PROs in the initial build came from the old
   FEI computer and still carried RAID metadata, so they showed up as an
   existing array. Wipe reused drives (for example from a live USB) before
   building the new array. New drives do not need this.

----

3. Assembly
===========

Work on an ESD-safe bench with the unit unplugged.

Open the Unit
-------------

#. Remove the bottom panel.
#. Remove the i-Module PCIe expansion module.
#. Remove the 2.5" drive holder.
#. Disconnect the short M.2 adapter for the TSN-enabled LAN (it is wired to the
   computer cover).

Data Drive
----------

#. Mount the 2 TB SSD in the 2.5" drive holder with the long pre-provided
   screws. Leave the holder out for now.

Memory (Bottom Slot)
--------------------

#. Remove the RAM/SSD thermal cover.
#. Install the first SODIMM with a **"Bottom"** DDR thermal pad.
#. Refit the RAM/SSD thermal cover.

Memory (Top Slot) and CPU Thermal Paste
---------------------------------------

The second SODIMM sits under the large outer heat-fin cover.

#. Loosen the 4 captive screws along the outer edges of the motherboard.
#. Remove the 4 spring-loaded (non-captive) screws around the RAM/SSD thermal
   cover.
#. Flip the unit over and lift off the heat-fin cover.
#. Install the second SODIMM with a **"Top"** DDR thermal pad (thicker than the
   bottom one).
#. If you have a spare, replace the pink thermal pad on the small metal block
   on the heat fin.
#. Clean the old thermal paste off the CPU and apply new paste (we used an X
   plus a small pea-sized dot).
#. Refit the heat-fin cover, flip the unit back, and reinstall all 8 screws.

Reassemble the Base Unit
------------------------

#. Reinstall the TSN LAN M.2 adapter with its original two small screws.
#. Connect the data and power cables between the motherboard and the 2 TB SSD,
   then reinstall the 2.5" drive holder.

PCIe Cards
----------

#. Mount both 990 PRO NVMe drives on the MegaRAID card's M.2 slots. The array
   itself is created in firmware later (:ref:`section-raid`).
#. Install the cards in the i-Module:

   * **RAID controller:** the slot closest to the motherboard, which leaves room
     for a cable later.
   * **ConnectX-6:** the other slot. Label the fiber port **archon**; the
     network config depends on it (:ref:`section-network`).

#. Refit the i-Module carefully and screw it down. It takes some force to seat;
   that is fine as long as the PCIe connector is well aligned.
#. Refit the outer cover.

Cabling
-------

#. Connect the FT4222 board over USB. In SPI master mode, its Slave Select (SS)
   pin must be tied high.
#. Connect power, the onboard management Ethernet and the Archon fiber.

----

4. First Power-On
=================

Before moving on to :doc:`rt_build`, confirm in BIOS / POST:

* 64 GB of memory is detected.
* The MegaRAID controller shows its configuration utility and lists both NVMe
  drives.
* The 2 TB SSD is detected.

.. note::
   During the initial build the OS installer chose the 2 TB SSD over the NVMe
   drives. If the installer offers the wrong disk, disconnect the 2.5" SSD's
   cables for the install and reconnect them afterwards.

After the OS is installed (:doc:`rt_build`), confirm from Linux:

.. code-block:: bash

   free -h                          # ~64 GB total
   lscpu | grep -E '^Core|^Socket'  # 14 cores, 1 socket
   lspci | grep -i -E 'raid|mellanox'
   lsblk                            # one ~1 TB RAID volume + 2 TB SSD
   lsusb | grep 0403:601c           # FT4222

----

5. Hardware Inventory
=====================

Values later steps depend on:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Item
     - Value
   * - Base system
     - Advantech MIC-770 V3
   * - CPU
     - Intel Core i5-13500E, 14 cores, 1 socket
   * - Memory
     - 64 GB (2 x 32 GB DDR5-4800 SODIMM)
   * - Boot volume
     - 2 x Samsung 990 PRO 1 TB, RAID 1 on Broadcom MegaRAID 9520-2M2
   * - Data drive
     - Samsung 870 EVO 2 TB, mounted at ``/data``
   * - Management NIC
     - Onboard Ethernet carrying ``192.168.29.0/24``
   * - Archon fiber NIC
     - ConnectX-6 Lx in the i-Module, ``enp202s0f0np0``, port labelled
       **archon**
   * - FT4222 SPI board
     - USB ``0403:601c``
