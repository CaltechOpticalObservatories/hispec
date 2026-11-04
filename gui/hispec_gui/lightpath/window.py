from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QComboBox, QDockWidget, QLabel, QMainWindow, QWidget

from .layout import NODES_BY_ID
from .panel import NodePanel
from .scene import LightPathScene, LightPathView
from .state import MOCK_PATHS, MockSource, StateSource
from .theme import DARK, LIGHT, Theme, apply_to_app


class LightPathWindow(QMainWindow):
    """The light path GUI, fed by a StateSource. The details panel starts hidden."""

    def __init__(self, source: StateSource, theme: Theme = LIGHT, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HISPEC Light Path")
        self.resize(1600, 800)
        self.source = source
        self.popups: Dict[str, QWidget] = {}

        self.scene = LightPathScene(theme=theme, parent=self)
        self.view = LightPathView(self.scene)
        self.setCentralWidget(self.view)

        self.panel = NodePanel(source)
        self.dock = QDockWidget("Details", self)
        self.dock.setObjectName("details")
        self.dock.setWidget(self.panel)
        self.dock.setMinimumWidth(280)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.hide()

        self.scene.node_selected.connect(self.panel.set_node)
        self.view.node_activated.connect(self.pop_out)
        self.panel.pop_out_requested.connect(self.pop_out)
        source.status_changed.connect(self.scene.set_status)
        source.path_changed.connect(self.scene.set_path)
        for node_id in self.scene.node_items:
            self.scene.set_status(node_id, source.status(node_id))
        self.scene.set_path(source.path)

        details = self.dock.toggleViewAction()
        details.setText("&Details")
        details.setShortcut("Ctrl+D")
        self.dark_mode = QAction("Dar&k mode", self, checkable=True)
        self.dark_mode.setShortcut("Ctrl+Shift+D")
        self.dark_mode.toggled.connect(lambda on: self.set_theme(DARK if on else LIGHT))
        fit = QAction("&Fit diagram", self)
        fit.setShortcut("Ctrl+0")
        fit.triggered.connect(self.view.fit)

        view_menu = self.menuBar().addMenu("&View")
        view_menu.addActions([details, self.dark_mode])
        view_menu.addSeparator()
        for text, shortcut, slot in (
                ("Zoom &in", QKeySequence.ZoomIn, lambda: self.view.zoom(1.25)),
                ("Zoom &out", QKeySequence.ZoomOut, lambda: self.view.zoom(0.8))):
            action = QAction(text, self)
            action.setShortcut(shortcut)
            action.triggered.connect(slot)
            view_menu.addAction(action)
        view_menu.addAction(fit)

        toolbar = self.addToolBar("View")
        toolbar.setObjectName("view")
        toolbar.addActions([details, self.dark_mode, fit])
        self.dark_mode.setChecked(theme is DARK)

        if isinstance(source, MockSource):
            self._add_mock_toolbar(source)
            self.statusBar().addWidget(QLabel("Mock data: not connected to daemons"))

    def set_theme(self, theme: Theme) -> None:
        """Switch the diagram and the rest of the window to `theme`."""
        apply_to_app(theme)
        self.scene.set_theme(theme)
        self.dark_mode.setChecked(theme is DARK)

    def pop_out(self, node_id: str) -> None:
        """Open a node in its own window, or raise the one already open."""
        popup = self.popups.get(node_id)
        if popup is None:
            popup = NodePanel(self.source, can_pop_out=False)
            popup.setWindowFlag(Qt.Window)
            popup.setAttribute(Qt.WA_DeleteOnClose)
            popup.setWindowTitle(f"HISPEC: {NODES_BY_ID[node_id].title}")
            popup.resize(360, 420)
            popup.set_node(node_id)
            popup.destroyed.connect(lambda *_: self.popups.pop(node_id, None))
            self.popups[node_id] = popup
        popup.show()
        popup.raise_()
        popup.activateWindow()

    def closeEvent(self, event) -> None:  # pylint: disable=invalid-name
        """Close the pop-outs with the main window, and stop the source."""
        for popup in list(self.popups.values()):
            popup.close()
        self.source.stop()
        super().closeEvent(event)

    def _add_mock_toolbar(self, source: MockSource) -> None:
        toolbar = self.addToolBar("Mock")
        toolbar.setObjectName("mock")
        toolbar.addWidget(QLabel(" Mock lit path: "))
        paths = QComboBox()
        paths.addItems(list(MOCK_PATHS))
        paths.setCurrentText("None")
        paths.currentTextChanged.connect(source.set_path)
        toolbar.addWidget(paths)
