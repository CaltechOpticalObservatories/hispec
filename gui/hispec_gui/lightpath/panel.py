"""Details of one node: its daemon, status, keyword values and (later) controls."""
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from .layout import NODES_BY_ID
from .state import StateSource, Status


class NodePanel(QWidget):  # pylint: disable=too-many-instance-attributes,too-few-public-methods
    """Shows whichever node it is given; follows that node's state from the source."""

    pop_out_requested = Signal(str)

    def __init__(self, source: StateSource, parent=None, can_pop_out: bool = True):
        super().__init__(parent)
        self.source = source
        self.node_id: Optional[str] = None

        self.title = QLabel()
        self.title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.pop_out = QPushButton("Pop out")
        self.pop_out.setToolTip("Open this component in its own window")
        self.pop_out.setVisible(can_pop_out)
        self.pop_out.clicked.connect(lambda: self.pop_out_requested.emit(self.node_id))
        header = QHBoxLayout()
        header.addWidget(self.title, 1)
        header.addWidget(self.pop_out)

        self.daemon = QLabel()
        self.daemon.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.branch = QLabel()
        self.status = QLabel()
        info = QFormLayout()
        info.addRow("Daemon:", self.daemon)
        info.addRow("Branch:", self.branch)
        info.addRow("Status:", self.status)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Keyword", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.position = QComboBox()
        self.move_button = QPushButton("Move")
        self.controls = self._build_controls()

        self.body = QWidget()
        body = QVBoxLayout(self.body)
        body.setContentsMargins(0, 0, 0, 0)
        body.addLayout(info)
        body.addWidget(self.table, 1)
        body.addWidget(self.controls)

        self.hint = QLabel("Click a component in the diagram.")
        self.hint.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.hint)
        layout.addWidget(self.body, 1)

        source.status_changed.connect(self._on_status)
        source.values_changed.connect(self._on_values)
        self.set_node(None)

    def _build_controls(self) -> QGroupBox:
        # Placeholders until the GUI can command daemons
        controls = QGroupBox("Control")
        row = QHBoxLayout(controls)
        row.addWidget(QLabel("Named position:"))
        row.addWidget(self.position, 1)
        row.addWidget(self.move_button)
        controls.setEnabled(False)
        controls.setToolTip("Not connected to daemons yet")
        return controls

    def set_node(self, node_id: Optional[str]) -> None:
        """Show `node_id`, or the hint when it is None."""
        self.node_id = node_id
        self.hint.setVisible(node_id is None)
        self.body.setVisible(node_id is not None)
        self.pop_out.setEnabled(node_id is not None)
        if node_id is None:
            self.title.setText("")
            return
        node = NODES_BY_ID[node_id]
        self.title.setText(node.title or node_id)
        self.daemon.setText(node.daemon or "none")
        self.branch.setText(node.branch)
        self._on_status(node_id, self.source.status(node_id))
        self._on_values(node_id, self.source.values.get(node_id, {}))

    def _on_status(self, node_id: str, status: Status) -> None:
        if node_id == self.node_id:
            self.status.setText(status.value if NODES_BY_ID[node_id].daemon else "n/a")

    def _on_values(self, node_id: str, values: dict) -> None:
        if node_id != self.node_id:
            return
        self.table.setRowCount(len(values))
        for row, (key, value) in enumerate(sorted(values.items())):
            self.table.setItem(row, 0, QTableWidgetItem(key))
            self.table.setItem(row, 1, QTableWidgetItem(str(value)))
