"""Launch the light path GUI: hispec-lightpath, or python -m hispec_gui.lightpath"""
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from .state import MockSource
from .theme import DARK, LIGHT
from .window import LightPathWindow


def main() -> int:
    """Open the window on mock data until it is closed."""
    app = QApplication.instance() or QApplication(sys.argv)
    # Fusion draws the same on every platform, and honours the dark palette
    app.setStyle("Fusion")
    dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    source = MockSource()
    window = LightPathWindow(source)
    window.set_theme(DARK if dark else LIGHT)
    window.show()
    source.start()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
