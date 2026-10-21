"""FEI motion stages, as their daemons name their keywords.

Each :class:`~hispec.scripting.Stage` mirrors one axis of a daemon configured
under ``config/hsfei/``: multi-stage daemons suffix their keywords with the
stage name from that config (``positionvalueh``), single-stage daemons use the
bare names. Update this file when those configs rename a stage.
"""
from hispec.scripting import Stage

#: Mask selector, horizontal and vertical (hsfei_ms.yaml), in mm
MS_H = Stage("hsfei.ms", "h")
MS_V = Stage("hsfei.ms", "v")

#: Lens selector mechanism, horizontal and vertical (hsfei_lsm.yaml), in mm
LSM_H = Stage("hsfei.lsm", "h")
LSM_V = Stage("hsfei.lsm", "v")

#: ATC pickoff dichroic selector (hsfei_atcp.yaml), in mm
ATCP = Stage("hsfei.atcp")

#: ATC lens stage (hsfei_atcl.yaml), in mm
ATCL = Stage("hsfei.atcl")

#: ATC filter wheel (hsfei_atcfw.yaml), in slots. Its position write blocks
#: until the wheel stops, and it has no ismoving or isreferenced keyword.
ATCFW = Stage("hsfei.atcfw", tolerance=0, has_ismoving=False, has_isreferenced=False)
