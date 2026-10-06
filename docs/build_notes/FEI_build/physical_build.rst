==============================
Physical Build: Hardware Setup
==============================

:Next: :doc:`rt_build`

.. contents::
   :depth: 1
   :local:

----

1. Hardware Inventory
=====================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Item
     - Value
   * - CPU
     - Intel Core i5-13500E, 14 cores, 1 socket (``lscpu | grep -E '^Core|^Socket'``)
   * - RAID controller
     - Broadcom MegaRAID 9520-2M2
   * - Boot / OS drives
     - 2 x Samsung 990 Pro 1 TB NVMe (RAID 1, see :ref:`section-raid`)
   * - Data drive
     - 2 TB SSD, mounted at ``/data``
   * - Management NIC
     - Interface carrying ``192.168.29.0/24``
   * - Archon fiber NIC
     - ``enp202s0f0np0``, port physically labelled **archon**
   * - FT4222 SPI board
     - USB ``0403:601c``

----

2. Hardware Modifications
=========================

*To be provided.*
