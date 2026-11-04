"""Light and dark colour themes for the light path GUI.

Everything off the lit path is grey, so only the path itself carries colour.
The path colours come from the Okabe-Ito palette, which stays distinguishable
with the common colour vision deficiencies. Lit lines are also wider than
grey ones and status lights differ in shape, so neither relies on colour alone.
"""
from dataclasses import dataclass
from typing import Mapping

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class Theme:  # pylint: disable=too-many-instance-attributes
    """Colours for one appearance. Branch keys are fei, red, blue and cal."""
    name: str
    background: str
    text: str               # labels on neutral boxes, selection outline
    off_line: str           # anything not on the lit path
    off_fill: str
    off_border: str
    off_text: str
    neutral_fill: str       # stage circles and neutral boxes
    lit: Mapping[str, str]  # lines, ports and lit stages
    on_lit: Mapping[str, str]   # text on a lit fill
    tint: Mapping[str, str]     # large boxes on the lit path
    casing: str             # outline under lit lines, empty for none
    status: Mapping[str, str]   # by Status value


LIGHT = Theme(
    name="light",
    background="#ffffff",
    text="#1a1a1a",
    off_line="#d4d4d4",
    off_fill="#dcdcdc",
    off_border="#b4b4b4",
    off_text="#6e6e6e",
    neutral_fill="#ffffff",
    lit={"fei": "#F0E442", "red": "#D55E00", "blue": "#0072B2", "cal": "#009E73",
         "neutral": "#ffffff"},
    on_lit={"fei": "#1a1a1a", "red": "#ffffff", "blue": "#ffffff", "cal": "#ffffff",
            "neutral": "#1a1a1a"},
    tint={"fei": "#F0E442", "red": "#F3C3A1", "blue": "#A9CFEA", "cal": "#A6DBC9",
          "neutral": "#ffffff"},
    casing="#3a3a3a",
    status={"unknown": "#9E9E9E", "ok": "#009E73", "moving": "#E69F00", "fault": "#D55E00"},
)

DARK = Theme(
    name="dark",
    background="#1e1f22",
    text="#ececec",
    off_line="#46484d",
    off_fill="#393b40",
    off_border="#56585e",
    off_text="#9c9ea3",
    neutral_fill="#2b2d31",
    lit={"fei": "#F0E442", "red": "#E66A1F", "blue": "#6E8CFF", "cal": "#22B573",
         "neutral": "#2b2d31"},
    on_lit={"fei": "#1a1a1a", "red": "#1a1a1a", "blue": "#1a1a1a", "cal": "#1a1a1a",
            "neutral": "#ececec"},
    tint={"fei": "#8a8326", "red": "#7a4122", "blue": "#3b4a8a", "cal": "#1f6b4f",
          "neutral": "#2b2d31"},
    casing="",
    status={"unknown": "#8a8a8a", "ok": "#22B573", "moving": "#E69F00", "fault": "#FF6E3A"},
)


def apply_to_app(theme: Theme) -> None:
    """Give the rest of the application's widgets the theme's appearance."""
    app = QApplication.instance()
    if theme is LIGHT:
        app.setPalette(app.style().standardPalette())
        return
    palette = QPalette()
    window, base, text = QColor("#2b2d31"), QColor(theme.background), QColor(theme.text)
    for role, color in ((QPalette.Window, window), (QPalette.WindowText, text),
                        (QPalette.Base, base), (QPalette.AlternateBase, window),
                        (QPalette.Text, text), (QPalette.Button, window),
                        (QPalette.ButtonText, text), (QPalette.ToolTipBase, window),
                        (QPalette.ToolTipText, text), (QPalette.Highlight, QColor("#4b6eaf")),
                        (QPalette.HighlightedText, QColor("#ffffff"))):
        palette.setColor(role, color)
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        palette.setColor(QPalette.Disabled, role, QColor(theme.off_text))
    app.setPalette(palette)
