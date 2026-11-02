"""FIB trunk interface box (TIB)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from .board import FibBoard


@dataclass(frozen=True)
class LaserSummary:
    """Compact laser state from ``status``; times are None while inactive."""

    power_mw: float | None
    ready: bool
    tec_on_s: int | None
    off_in_s: int | None


class TrunkInterfaceBox(FibBoard):
    """The FIB trunk interface box: MEMS routing, laser bank and attenuators."""

    BOARD: ClassVar[str] = "tib"

    def lasers(self) -> dict[str, LaserSummary]:
        """Return each laser's compact state, keyed by laser name.

        Reads driver registers only while the bank is already powered.
        """
        lasers = self.query("status", {"lasers": True})["lasers"]
        return {name: LaserSummary(entry["power_mw"], entry["ready"],
                                   entry["tec_on_s"], entry["off_in_s"])
                for name, entry in lasers.items()}

    def attenuations_db(self) -> dict[str, float | None]:
        """Return each attenuator's applied attenuation, keyed by laser name."""
        attens = self.query("status", {"attens": True})["attens"]
        return {name: entry["value_db"] for name, entry in attens.items()}
