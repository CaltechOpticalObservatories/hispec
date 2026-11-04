"""Geometry of the light path diagram, transcribed from the HISPEC UI design.

Coordinates are scene units matching the design drawing, which is about
2000 x 840. A line runs from the centre of node `a`, through `points`, to the
centre of node `b`. Lines are drawn under the nodes, so the ends are hidden.

A node that is `part_of` another, like a spectrograph's IS and slit block, is
not selectable itself: clicking it selects the whole, and light reaching it
lights the whole.

Nodes of kind "join" are not drawn. They exist where two lines meet without a
switch, so that the diagram is a graph a lit path can be traced through.
"""
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

Point = Tuple[float, float]

# What travels along a line; the theme turns it into a colour
FEI = "fei"
RED = "red"
BLUE = "blue"
CAL = "cal"

# Fibre subsystem daemons, not written yet. TIB serves the injection ports,
# laser diodes and photodiodes of both arms.
TIB = "hsfibers.tib"
CS = {"red": "hsfibers.csred", "blue": "hsfibers.csblue"}     # CAL source switches
AS = {"red": "hsfibers.asred", "blue": "hsfibers.asblue"}     # achromatic splitters


@dataclass(frozen=True)
class Node:  # pylint: disable=too-many-instance-attributes
    """One box, circle or switch in the diagram."""
    id: str
    label: str
    kind: str                       # stage, port, box, panel, junction, join
    pos: Point                      # centre
    size: Point = (0.0, 0.0)
    branch: str = "fei"             # fei, red, blue or neutral
    daemon: Optional[str] = None    # <group>.<peer> of the daemon behind it
    rows: Tuple[str, ...] = ()      # labelled rows, for panels
    part_of: Optional[str] = None   # node this is drawn apart from but belongs to
    prefix: str = ""                # names the subsystem in titles, e.g. TIB

    @property
    def title(self) -> str:
        """Name for panels and windows, e.g. "TIB Red Science" or "FEI P.O"."""
        name = self.label.replace("\n", " ")
        if self.prefix:
            return f"{self.prefix} {self.branch.capitalize()} {name}"
        return name


@dataclass(frozen=True)
class Line:
    """A fibre or beam between two nodes."""
    a: str
    b: str
    beam: str                       # fei, red, blue or cal
    points: Tuple[Point, ...] = ()


def _stage(nid, label, x, y, branch="fei", daemon=None):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    return Node(nid, label, "stage", (x, y), (48, 48), branch, daemon)


def _port(nid, label, x, y, branch, w=88, h=28):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    return Node(nid, label, "port", (x, y), (w, h), branch)


def _tib(nid, label, x, y, branch):
    return Node(nid, label, "port", (x, y), (88, 28), branch, TIB, prefix="TIB")


def _cal_switch(nid, x, y, side):
    # Drawn without a label; "Switch" only names it in titles
    return Node(nid, "Switch", "junction", (x, y), (9, 14), side, CS[side], prefix="CS")


def _junction(nid, x, y):
    return Node(nid, "", "junction", (x, y), (9, 14), "neutral")


def _join(nid, x, y):
    return Node(nid, "", "join", (x, y))


NODES: Tuple[Node, ...] = (
    Node("aobench", "AO Bench", "panel", (74, 400), (148, 126), "neutral",
         rows=("SFP:", "P.O:", "DM:", "")),

    # FEI, along the yellow beam
    _stage("ofm", "OFM", 184, 397),
    _stage("feipo", "FEI\nP.O", 250, 397, daemon="hsfei.feipo"),
    _stage("lsm", "LSM", 316, 397, daemon="hsfei.lsm"),
    _stage("ms", "MS", 382, 397, daemon="hsfei.ms"),
    _stage("adc", "ADC", 449, 397, daemon="hsfei.adc"),
    _stage("fsm", "FSM", 515, 397),
    _stage("atcpo", "ATC\nP.O", 582, 397, daemon="hsfei.atcp"),
    _stage("fw", "FW", 583, 317, daemon="hsfei.atcfw"),
    _stage("pf", "P/F", 582, 264, daemon="hsfei.atcl"),
    Node("atc", "ATC", "box", (582, 207), (70, 28), "fei", "hsfei.atcam"),
    _stage("rpiaa", "RPIAA", 779, 299, daemon="hsfei.piaagimr"),
    _stage("bpiaa", "BPIAA", 780, 494, daemon="hsfei.piaagimb"),
    _join("k_piaa", 779, 397),
    # Where the beam from each PIAA meets its port stack
    _join("k_fam_red", 902, 294),
    _join("k_fam_blue", 902, 493),

    # RED fibres
    _port("cal_red", "CAL", 785, 15, "red"),
    _tib("ld1_red", "LD1", 785, 49, "red"),
    _tib("ld2_red", "LD2", 785, 79, "red"),
    _tib("ld3_red", "LD3", 785, 109, "red"),
    _tib("rpd", "RPD", 785, 142, "red"),
    _tib("mmpd_red", "MMPD", 954, 285, "red"),
    _tib("smpd_red", "SMPD", 954, 320, "red"),
    _tib("retro_red", "Retro", 954, 350, "red"),
    _tib("sci_red", "Science", 954, 380, "red"),
    _join("k_ld1_red", 1115, 49),
    _join("k_ld2_red", 1115, 79),
    _junction("j_ld_red", 1115, 110),
    _join("k_retro_red", 1115, 350),
    _join("k_rpd", 985, 142),

    # BLUE fibres
    _tib("lantern", "Lantern", 952, 465, "blue"),
    _tib("sci_blue", "Science", 952, 501, "blue"),
    _tib("retro_blue", "Retro", 952, 531, "blue"),
    _tib("smpd_blue", "SMPD", 952, 560, "blue"),
    _tib("mmpd_blue", "MMPD", 952, 595, "blue"),
    _tib("bpd", "BPD", 788, 696, "blue"),
    _tib("ld3_blue", "LD3", 788, 730, "blue"),
    _tib("ld2_blue", "LD2", 788, 760, "blue"),
    _tib("ld1_blue", "LD1", 788, 790, "blue"),
    _port("cal_blue", "CAL", 788, 826, "blue"),
    _join("k_bpd", 970, 697),
    _junction("j_ld_blue", 1115, 734),
    _join("k_ld2_blue", 1115, 760),
    _join("k_ld1_blue", 1115, 790),
    _join("k_retro_blue", 1115, 533),

    # CAL sources, RED side. The lamps themselves have no daemons
    _port("bb_red", "Blackbody", 1242, 141, "red", h=30),
    _port("gascell", "Gas Cell", 1242, 193, "red", h=30),
    _port("etalon_red", "Etalon", 1242, 244, "red", h=30),
    _port("lfc_hk", "LFC HK", 1242, 295, "red", h=30),
    _port("dark_red_top", "Dark", 1506, 74, "red", h=30),
    _port("dark_red_mid", "Dark", 1448, 260, "red", h=30),
    _stage("as_red", "AS\nRed", 1596, 261, branch="red", daemon=AS["red"]),

    # CAL sources, BLUE side. The lamps themselves have no daemons
    _port("lfc_yj", "LFC yJ", 1241, 580, "blue", h=30),
    _port("etalon_blue", "Etalon", 1241, 629, "blue", h=30),
    _port("cathode", "Cathode", 1241, 681, "blue", h=30),
    _port("bb_blue", "Blackbody", 1239, 734, "blue", h=30),
    _port("dark_blue_mid", "Dark", 1447, 601, "blue", h=30),
    _port("dark_blue_bot", "Dark", 1505, 799, "blue", h=30),
    _stage("as_blue", "AS\nBlue", 1597, 606, branch="blue", daemon=AS["blue"]),

    # Switches on the CAL lines
    _junction("j_top_lsm", 316, 15),
    _junction("j_bot_lsm", 316, 826),
    _junction("j_cal_red", 988, 13),
    _junction("j_cal_blue", 1015, 826),

    # CAL source switches
    _cal_switch("j_bb_red", 1293, 141, "red"),
    _cal_switch("j_dark_red_top", 1507, 139, "red"),
    _cal_switch("j_gc", 1375, 191, "red"),
    _cal_switch("j_et_red", 1375, 243, "red"),
    _cal_switch("j_red_merge", 1462, 195, "red"),
    _cal_switch("j_red_dark", 1527, 196, "red"),
    _cal_switch("j_red_out", 1555, 196, "red"),
    _cal_switch("j_bb_blue", 1293, 733, "blue"),
    _cal_switch("j_dark_blue_bot", 1506, 735, "blue"),
    _cal_switch("j_et_blue", 1375, 628, "blue"),
    _cal_switch("j_cath", 1375, 681, "blue"),
    _cal_switch("j_blue_merge", 1462, 676, "blue"),
    _cal_switch("j_blue_dark", 1527, 676, "blue"),
    _cal_switch("j_blue_out", 1550, 676, "blue"),

    # Spectrograph side
    Node("socal", "SoCal", "box", (1274, 425), (72, 30), "neutral"),
    Node("switch_red", "Main Switch Red", "box", (1700, 377), (150, 85), "red"),
    Node("switch_blue", "Main Switch Blue", "box", (1701, 480), (150, 85), "blue"),
    Node("is_red", "IS", "port", (1856, 151), (34, 44), "red", part_of="spec_red"),
    Node("spec_red", "SPEC Red", "box", (1938, 151), (120, 48), "red"),
    Node("slit_red", "Slit Block", "port", (1938, 199), (120, 32), "red", part_of="spec_red"),
    Node("slit_blue", "Slit Block", "port", (1938, 677), (120, 32), "blue",
         part_of="spec_blue"),
    Node("is_blue", "IS", "port", (1856, 730), (34, 44), "blue", part_of="spec_blue"),
    Node("spec_blue", "SPEC Blue", "box", (1940, 729), (120, 48), "blue"),
)

LINES: Tuple[Line, ...] = (
    # FEI beam
    Line("aobench", "ofm", FEI, ((148, 397),)),
    Line("ofm", "feipo", FEI),
    Line("feipo", "lsm", FEI),
    Line("lsm", "ms", FEI),
    Line("ms", "adc", FEI),
    Line("adc", "fsm", FEI),
    Line("fsm", "atcpo", FEI),
    Line("atcpo", "fw", FEI),
    Line("fw", "pf", FEI),
    Line("pf", "atc", FEI),
    Line("atcpo", "k_piaa", FEI),
    Line("k_piaa", "rpiaa", FEI),
    Line("k_piaa", "bpiaa", FEI),
    Line("rpiaa", "k_fam_red", FEI, ((800, 294),)),
    Line("bpiaa", "k_fam_blue", FEI, ((800, 492),)),
    # The fibre alignment mechanisms pick which port the beam enters
    Line("k_fam_red", "mmpd_red", FEI),
    Line("k_fam_red", "smpd_red", FEI, ((902, 320),)),
    Line("k_fam_red", "retro_red", FEI, ((902, 350),)),
    Line("k_fam_red", "sci_red", FEI, ((902, 380),)),
    Line("k_fam_blue", "lantern", FEI, ((902, 465),)),
    Line("k_fam_blue", "sci_blue", FEI, ((902, 501),)),
    Line("k_fam_blue", "retro_blue", FEI, ((902, 531),)),
    Line("k_fam_blue", "smpd_blue", FEI, ((902, 560),)),
    Line("k_fam_blue", "mmpd_blue", FEI, ((902, 595),)),

    # CAL distribution round the outside, and the LSM feed
    Line("aobench", "j_top_lsm", CAL, ((70, 337), (70, 13))),
    Line("aobench", "j_bot_lsm", CAL, ((70, 463), (70, 828))),
    Line("j_top_lsm", "cal_red", CAL),
    Line("j_bot_lsm", "cal_blue", CAL),
    Line("j_top_lsm", "lsm", CAL),
    Line("lsm", "j_bot_lsm", CAL),
    Line("cal_red", "j_cal_red", CAL),
    Line("cal_blue", "j_cal_blue", CAL),
    Line("j_cal_red", "j_red_out", CAL, ((1562, 13), (1562, 196))),
    Line("j_cal_blue", "j_blue_out", CAL, ((1562, 828), (1562, 676))),

    # RED fibres
    Line("j_cal_red", "k_ld1_red", RED, ((988, 27), (1160, 27), (1170, 38), (1158, 49))),
    Line("ld1_red", "k_ld1_red", RED),
    Line("ld2_red", "k_ld2_red", RED),
    Line("ld3_red", "j_ld_red", RED),
    Line("k_ld1_red", "k_ld2_red", RED),
    Line("k_ld2_red", "j_ld_red", RED),
    Line("j_ld_red", "k_retro_red", RED),
    Line("k_retro_red", "retro_red", RED),
    Line("rpd", "k_rpd", RED),
    Line("k_rpd", "mmpd_red", RED, ((1028, 175), (1098, 175), (1098, 285))),
    Line("k_rpd", "smpd_red", RED, ((1106, 142), (1106, 320))),
    Line("sci_red", "switch_red", RED, ((990, 380), (1625, 380))),
    Line("socal", "switch_red", RED, ((1312, 420), (1578, 420), (1585, 390), (1625, 390))),
    Line("switch_red", "slit_red", RED, ((1776, 350), (1930, 350), (1930, 215))),
    Line("switch_red", "slit_red", RED, ((1776, 372), (1937, 372), (1937, 215))),
    Line("switch_red", "slit_red", RED, ((1776, 397), (1945, 397), (1945, 215))),

    # BLUE fibres
    Line("j_cal_blue", "k_ld1_blue", BLUE, ((1018, 812), (1155, 812), (1165, 803), (1155, 790))),
    Line("ld1_blue", "k_ld1_blue", BLUE),
    Line("ld2_blue", "k_ld2_blue", BLUE),
    Line("ld3_blue", "j_ld_blue", BLUE),
    Line("k_ld1_blue", "k_ld2_blue", BLUE),
    Line("k_ld2_blue", "j_ld_blue", BLUE),
    Line("j_ld_blue", "k_retro_blue", BLUE),
    Line("k_retro_blue", "retro_blue", BLUE),
    Line("bpd", "k_bpd", BLUE),
    Line("k_bpd", "mmpd_blue", BLUE, ((1032, 662), (1094, 662), (1094, 597))),
    Line("k_bpd", "smpd_blue", BLUE, ((1105, 697), (1105, 562))),
    Line("lantern", "switch_blue", BLUE, ((990, 463), (1625, 463))),
    Line("sci_blue", "switch_blue", BLUE, ((990, 501), (1150, 501), (1153, 472), (1625, 472))),
    Line("socal", "switch_blue", BLUE, ((1312, 430), (1575, 430), (1582, 452), (1625, 452))),
    Line("switch_blue", "slit_blue", BLUE, ((1776, 455), (1945, 455), (1945, 661))),
    Line("switch_blue", "slit_blue", BLUE, ((1776, 477), (1937, 477), (1937, 661))),
    Line("switch_blue", "slit_blue", BLUE, ((1776, 497), (1927, 497), (1927, 661))),

    # CAL sources, RED side
    Line("bb_red", "j_bb_red", CAL),
    Line("j_bb_red", "j_dark_red_top", CAL),
    Line("dark_red_top", "j_dark_red_top", CAL),
    Line("j_dark_red_top", "is_red", CAL, ((1838, 139),)),
    Line("j_bb_red", "j_gc", CAL, ((1330, 175),)),
    Line("gascell", "j_gc", CAL),
    Line("j_gc", "j_red_merge", CAL),
    Line("etalon_red", "j_et_red", CAL),
    Line("lfc_hk", "j_et_red", CAL, ((1345, 295),)),
    Line("j_et_red", "j_red_merge", CAL, ((1430, 200),)),
    Line("j_red_merge", "j_red_dark", CAL),
    Line("dark_red_mid", "j_red_dark", CAL, ((1497, 260), (1497, 215))),
    Line("j_red_dark", "j_red_out", CAL),
    Line("j_red_out", "as_red", CAL, ((1590, 196), (1590, 240))),
    Line("as_red", "switch_red", CAL, ((1590, 282), (1590, 370), (1625, 370))),
    Line("as_red", "switch_red", RED, ((1600, 282), (1600, 362), (1625, 362))),

    # CAL sources, BLUE side
    Line("lfc_yj", "j_et_blue", CAL, ((1330, 580),)),
    Line("etalon_blue", "j_et_blue", CAL),
    Line("j_et_blue", "j_blue_merge", CAL, ((1400, 672),)),
    Line("cathode", "j_cath", CAL),
    Line("j_cath", "j_blue_merge", CAL),
    Line("bb_blue", "j_bb_blue", CAL),
    Line("j_bb_blue", "j_cath", CAL, ((1330, 715),)),
    Line("j_bb_blue", "j_dark_blue_bot", CAL),
    Line("dark_blue_bot", "j_dark_blue_bot", CAL),
    Line("j_dark_blue_bot", "is_blue", CAL, ((1838, 734),)),
    Line("j_blue_merge", "j_blue_dark", CAL),
    Line("dark_blue_mid", "j_blue_dark", CAL, ((1497, 601), (1500, 655))),
    Line("j_blue_dark", "j_blue_out", CAL),
    Line("j_blue_out", "as_blue", CAL, ((1595, 676), (1595, 627))),
    Line("as_blue", "switch_blue", CAL, ((1595, 585), (1595, 497), (1625, 497))),
    Line("as_blue", "switch_blue", BLUE, ((1605, 585), (1605, 507), (1625, 507))),
)

NODES_BY_ID: Dict[str, Node] = {node.id: node for node in NODES}
