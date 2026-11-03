"""Where the light path window gets node states from.

The window only talks to a StateSource, so swapping MockSource for one backed
by libby.Client changes nothing in the UI.
"""
import random
from enum import Enum
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from .layout import NODES


class Status(Enum):
    """What a node's status light shows."""
    UNKNOWN = "unknown"
    OK = "ok"
    MOVING = "moving"
    FAULT = "fault"


class StateSource(QObject):
    """Base for state sources: caches the latest state and announces changes."""

    status_changed = Signal(str, object)    # node id, Status
    values_changed = Signal(str, dict)      # node id, keyword -> value
    path_changed = Signal(list)             # node ids along the lit path, in order

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.statuses: Dict[str, Status] = {}
        self.values: Dict[str, dict] = {}
        self.path: List[str] = []

    def start(self) -> None:
        """Begin delivering state."""

    def stop(self) -> None:
        """Stop delivering state."""

    def status(self, node_id: str) -> Status:
        """Return the last known status of a node."""
        return self.statuses.get(node_id, Status.UNKNOWN)

    def _set_status(self, node_id: str, status: Status) -> None:
        if self.statuses.get(node_id) != status:
            self.statuses[node_id] = status
            self.status_changed.emit(node_id, status)

    def _set_values(self, node_id: str, values: dict) -> None:
        self.values[node_id] = values
        self.values_changed.emit(node_id, values)

    def _set_path(self, path: List[str]) -> None:
        self.path = list(path)
        self.path_changed.emit(self.path)


_SCIENCE = ["aobench", "ofm", "feipo", "lsm", "ms", "adc", "fsm", "atcpo", "k_piaa"]

# Paths to light up for checking the look of the diagram
MOCK_PATHS: Dict[str, List[str]] = {
    "None": [],
    "Science → Red": _SCIENCE + ["rpiaa", "k_fam_red", "sci_red", "switch_red", "slit_red"],
    "Science → Blue": _SCIENCE + ["bpiaa", "k_fam_blue", "sci_blue", "switch_blue",
                                  "slit_blue"],
    "Blackbody → IS Red": ["bb_red", "j_bb_red", "j_dark_red_top", "is_red"],
    "Etalon → SPEC Red": ["etalon_red", "j_et_red", "j_red_merge", "j_red_dark",
                          "j_red_out", "as_red", "switch_red", "slit_red"],
    "LFC yJ → FEI → Blue": ["lfc_yj", "j_et_blue", "j_blue_merge", "j_blue_dark",
                            "j_blue_out", "j_cal_blue", "cal_blue", "j_bot_lsm", "lsm",
                            "ms", "adc", "fsm", "atcpo", "k_piaa", "bpiaa", "k_fam_blue",
                            "sci_blue", "switch_blue", "slit_blue"],
}


class MockSource(StateSource):
    """Made-up states, so the UI can be built and checked without daemons."""

    def __init__(self, parent: Optional[QObject] = None, interval_ms: int = 1500):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._tick)
        self._served = [node.id for node in NODES if node.daemon]

    def start(self) -> None:
        for node_id in self._served:
            self._set_status(node_id, Status.OK)
            self._set_values(node_id, self._mock_values(moving=False))
        self.set_path("None")
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def set_path(self, name: str) -> None:
        """Light one of MOCK_PATHS."""
        self._set_path(MOCK_PATHS[name])

    def _tick(self) -> None:
        # Keep one mechanism moving at a time, so the status lights visibly change
        for node_id in self._served:
            if self.status(node_id) is Status.MOVING:
                self._set_status(node_id, Status.OK)
                self._set_values(node_id, self._mock_values(moving=False))
        node_id = random.choice(self._served)
        self._set_status(node_id, Status.MOVING)
        self._set_values(node_id, self._mock_values(moving=True))

    @staticmethod
    def _mock_values(moving: bool) -> dict:
        return {
            "isconnected": True,
            "ismoving": moving,
            "positionnamed": "" if moving else "through",
            "positionvalue": round(random.uniform(0.0, 25.0), 3),
        }
