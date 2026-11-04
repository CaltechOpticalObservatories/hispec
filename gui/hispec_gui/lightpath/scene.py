"""Draws the light path layout as a QGraphicsScene, and the view that shows it."""
from functools import lru_cache
from typing import Dict, Iterable, List, Optional

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QPainter, QPainterPath,
                           QPen, QPolygonF, QTransform)
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsPathItem, QGraphicsScene,
                               QGraphicsView, QStyle)

from .layout import LINES, NODES, Line, Node
from .state import Status
from .theme import LIGHT, Theme

STATUS_DOT = 6.5


class NodeItem(QGraphicsItem):
    """A mechanism, fibre port, source or switch; grey unless on the lit path."""

    def __init__(self, node: Node, theme: Theme):
        super().__init__()
        self.node = node
        self.theme = theme
        self.status = Status.UNKNOWN
        self.lit = False
        self.setPos(*node.pos)
        self.setZValue(1)
        self.whole: Optional["NodeItem"] = None     # set by the scene for parts
        if node.kind != "join":
            self.setFlag(QGraphicsItem.ItemIsSelectable, node.part_of is None)
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip(node.title +
                            (f"\n{node.daemon}" if node.daemon else "\nno daemon"))

    def set_status(self, status: Status) -> None:
        """Change the status light."""
        self.status = status
        self.update()

    def set_lit(self, lit: bool) -> None:
        """Colour the node if the lit path passes through it, else grey it."""
        self.lit = lit
        self.update()

    def set_theme(self, theme: Theme) -> None:
        """Redraw in another theme."""
        self.theme = theme
        self.update()

    def _rect(self) -> QRectF:
        w, h = self.node.size
        return QRectF(-w / 2, -h / 2, w, h)

    def boundingRect(self) -> QRectF:  # pylint: disable=invalid-name
        """Leave room round the node for the selection and status light."""
        return self._rect().adjusted(-9, -9, 9, 9)

    def shape(self) -> QPainterPath:
        """Clickable area: the circle or box itself."""
        path = QPainterPath()
        if self.node.kind == "stage":
            path.addEllipse(self._rect())
        else:
            path.addRect(self._rect())
        return path

    def paint(self, painter: QPainter, option, widget=None) -> None:  # pylint: disable=unused-argument
        """Draw the node for its kind, with status light and selection."""
        kind = self.node.kind
        if kind == "join":
            return
        rect = self._rect()
        if kind == "stage":
            self._paint_stage(painter, rect)
        elif kind == "port":
            self._paint_box(painter, rect, self.theme.lit, 6)
        elif kind == "box":
            self._paint_box(painter, rect, self.theme.tint, 4)
        elif kind == "panel":
            self._paint_panel(painter, rect)
        elif kind == "junction":
            # Always green, to mark a switch; outlined on the path so it stands
            # out from the green line through it
            border = self.theme.text if self.lit else self.theme.off_border
            painter.setPen(QPen(QColor(border), 2 if self.lit else 1))
            painter.setBrush(QColor(self.theme.lit["cal"]))
            painter.drawRect(rect)
        if self.node.daemon and kind != "junction":
            # Too small for a light, and the side panel shows the status
            self._paint_status(painter, rect)
        if option.state & QStyle.State_Selected or (self.whole and self.whole.isSelected()):
            pen = QPen(QColor(self.theme.text), 2.5, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            self._outline(painter, rect.adjusted(-5, -5, 5, 5))

    def _outline(self, painter: QPainter, rect: QRectF) -> None:
        if self.node.kind == "stage":
            painter.drawEllipse(rect)
        else:
            painter.drawRoundedRect(rect, 6, 6)

    def _colors(self, fills):
        """Fill, border and text colours for this node in its lit state."""
        theme, branch = self.theme, self.node.branch
        if not self.lit:
            return QColor(theme.off_fill), QColor(theme.off_border), QColor(theme.off_text)
        fill = QColor(fills[branch])
        text = theme.on_lit[branch] if fills is theme.lit else theme.text
        return fill, QColor(theme.text), QColor(text)

    def _paint_stage(self, painter: QPainter, rect: QRectF) -> None:
        fill, border, text = self._colors(self.theme.lit)
        if not self.lit:
            fill = QColor(self.theme.neutral_fill)
        painter.setPen(QPen(border, 3 if self.lit else 2))
        painter.setBrush(fill)
        painter.drawEllipse(rect)
        painter.setFont(_fitted_font(self.node.label, rect.adjusted(5, 5, -5, -5), 15))
        painter.setPen(text)
        painter.drawText(rect, Qt.AlignCenter, self.node.label)

    def _paint_box(self, painter: QPainter, rect: QRectF, fills, radius) -> None:
        fill, border, text = self._colors(fills)
        painter.setPen(QPen(border, 2 if self.lit else 1.5))
        painter.setBrush(QBrush(fill))
        painter.drawRoundedRect(rect, radius, radius)
        painter.setFont(_fitted_font(self.node.label, rect.adjusted(4, 2, -4, -2), 17))
        painter.setPen(text)
        painter.drawText(rect, Qt.AlignCenter, self.node.label)

    def _paint_panel(self, painter: QPainter, rect: QRectF) -> None:
        theme = self.theme
        rows = list(self.node.rows) + [self.node.label]
        height = rect.height() / len(rows)
        painter.setFont(_font(15))
        border = QPen(QColor(theme.text), 2) if self.lit else QPen(QColor(theme.off_border), 1)
        for i, row in enumerate(rows):
            cell = QRectF(rect.left(), rect.top() + i * height, rect.width(), height - 2)
            painter.setPen(border)
            painter.setBrush(QColor(theme.neutral_fill))
            painter.drawRoundedRect(cell, 3, 3)
            painter.setPen(QColor(theme.text if self.lit else theme.off_text))
            last = i == len(rows) - 1
            painter.drawText(cell.adjusted(6, 0, 0, 0),
                             (Qt.AlignCenter if last else Qt.AlignLeft | Qt.AlignVCenter),
                             row)

    def _paint_status(self, painter: QPainter, rect: QRectF) -> None:
        # Shape as well as colour: circle ok, diamond moving, square fault,
        # hollow circle unknown
        centre, r = QPointF(rect.right() - 2, rect.top() + 2), STATUS_DOT
        color = QColor(self.theme.status[self.status.value])
        painter.setPen(QPen(QColor(self.theme.background), 1.5))
        painter.setBrush(color)
        if self.status is Status.MOVING:
            painter.drawPolygon(QPolygonF([centre + QPointF(dx, dy) for dx, dy in
                                           ((0, -r - 1), (r + 1, 0), (0, r + 1), (-r - 1, 0))]))
        elif self.status is Status.FAULT:
            painter.drawRect(QRectF(centre.x() - r, centre.y() - r, 2 * r, 2 * r))
        elif self.status is Status.OK:
            painter.drawEllipse(centre, r, r)
        else:
            painter.setPen(QPen(color, 2.5))
            painter.setBrush(QColor(self.theme.background))
            painter.drawEllipse(centre, r - 1, r - 1)


class LineItem(QGraphicsPathItem):
    """A fibre or beam: coloured and wide on the lit path, thin and grey off it."""

    def __init__(self, line: Line, nodes: Dict[str, Node], theme: Theme):
        super().__init__()
        self.line = line
        self.theme = theme
        self.lit = False
        path = QPainterPath(QPointF(*nodes[line.a].pos))
        for point in line.points:
            path.lineTo(*point)
        path.lineTo(*nodes[line.b].pos)
        self.setPath(path)
        self._restyle()

    def set_lit(self, lit: bool) -> None:
        """Colour this line if it is on the lit path, else grey it."""
        self.lit = lit
        self._restyle()

    def set_theme(self, theme: Theme) -> None:
        """Redraw in another theme."""
        self.theme = theme
        self._restyle()

    def _restyle(self) -> None:
        color = self.theme.lit[self.line.beam] if self.lit else self.theme.off_line
        pen = QPen(QColor(color), 8 if self.lit else 5)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        self.setPen(pen)
        # Lit lines sit above grey ones where they cross
        self.setZValue(0.5 if self.lit else 0)

    def boundingRect(self) -> QRectF:  # pylint: disable=invalid-name
        """Leave room for the casing, which is wider than the pen."""
        return super().boundingRect().adjusted(-2, -2, 2, 2)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        """Draw the line, over a darker casing when lit if the theme has one."""
        if self.lit and self.theme.casing:
            casing = QPen(self.pen())
            casing.setColor(QColor(self.theme.casing))
            casing.setWidthF(self.pen().widthF() + 3)
            painter.setPen(casing)
            painter.drawPath(self.path())
        super().paint(painter, option, widget)


class LightPathScene(QGraphicsScene):
    """The whole diagram. Emits node_selected with a node id, or None."""

    node_selected = Signal(object)

    def __init__(self, nodes: Iterable[Node] = NODES, lines: Iterable[Line] = LINES,
                 theme: Theme = LIGHT, parent=None):
        super().__init__(parent)
        self.node_items: Dict[str, NodeItem] = {}
        self.line_items: List[LineItem] = []
        for node in nodes:
            item = NodeItem(node, theme)
            self.node_items[node.id] = item
            self.addItem(item)
        by_id = {nid: item.node for nid, item in self.node_items.items()}
        for line in lines:
            item = LineItem(line, by_id, theme)
            self.line_items.append(item)
            self.addItem(item)
        self.parts = [item for item in self.node_items.values() if item.node.part_of]
        for item in self.parts:
            item.whole = self.node_items[item.node.part_of]
        self.setSceneRect(self.itemsBoundingRect().adjusted(-10, -10, 10, 10))
        self.set_theme(theme)
        self.selectionChanged.connect(self._on_selection)

    def set_theme(self, theme: Theme) -> None:
        """Redraw everything in `theme`."""
        self.theme = theme
        self.setBackgroundBrush(QColor(theme.background))
        for item in [*self.node_items.values(), *self.line_items]:
            item.set_theme(theme)

    def set_status(self, node_id: str, status: Status) -> None:
        """Update the status light on a node, if it is in the diagram."""
        item = self.node_items.get(node_id)
        if item is not None:
            item.set_status(status)

    def set_path(self, path: List[str]) -> None:
        """Light the lines between consecutive nodes of `path`, and the nodes."""
        pairs = {frozenset(pair) for pair in zip(path, path[1:])}
        on_path = set(path)
        on_path |= {item.node.part_of for item in self.parts if item.node.id in on_path}
        for item in self.line_items:
            item.set_lit(frozenset((item.line.a, item.line.b)) in pairs)
        for node_id, item in self.node_items.items():
            item.set_lit(node_id in on_path)

    def select(self, node_id: Optional[str]) -> None:
        """Select a node by id, or clear the selection."""
        self.clearSelection()
        if node_id is not None:
            self.node_items[node_id].setSelected(True)

    def whole_at(self, pos: QPointF) -> Optional[NodeItem]:
        """The clickable node at `pos`: the whole, if it is a part."""
        item = self.itemAt(pos, QTransform())
        if not isinstance(item, NodeItem) or item.node.kind == "join":
            return None
        return item.whole or item

    def mousePressEvent(self, event) -> None:  # pylint: disable=invalid-name
        """Clicking a part selects the whole it belongs to."""
        item = self.itemAt(event.scenePos(), QTransform())
        if isinstance(item, NodeItem) and item.whole is not None:
            self.select(item.whole.node.id)
            event.accept()
            return
        super().mousePressEvent(event)

    def _on_selection(self) -> None:
        for item in self.parts:
            item.update()
        items = self.selectedItems()
        self.node_selected.emit(items[0].node.id if items else None)


class LightPathView(QGraphicsView):
    """Shows the scene, fitted until the user zooms in.

    A mouse wheel zooms, a trackpad pinch zooms and two-finger scrolls, and
    dragging the background pans. Emits node_activated on a double click.
    """

    node_activated = Signal(str)
    MAX_ZOOM = 4.0      # relative to fitted

    def __init__(self, scene: LightPathScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setMinimumSize(800, 340)
        self._fitted = True

    def fit(self) -> None:
        """Show the whole diagram, and keep it fitted as the window resizes."""
        self._fitted = True
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def zoom(self, factor: float) -> None:
        """Scale by `factor`, between fitted and MAX_ZOOM times fitted."""
        fitted = self._fitted_scale()
        scale = self.transform().m11() * factor
        if scale <= fitted * 1.001:
            self.fit()
            return
        self._fitted = False
        factor = min(scale, fitted * self.MAX_ZOOM) / self.transform().m11()
        self.scale(factor, factor)

    def _fitted_scale(self) -> float:
        # fitInView leaves a 2 pixel margin
        rect, view = self.sceneRect(), self.viewport().rect().adjusted(2, 2, -2, -2)
        return min(view.width() / rect.width(), view.height() / rect.height())

    def resizeEvent(self, event) -> None:  # pylint: disable=invalid-name
        """Keep the whole diagram in view, unless zoomed in."""
        super().resizeEvent(event)
        if self._fitted:
            self.fit()

    def wheelEvent(self, event) -> None:  # pylint: disable=invalid-name
        """A mouse wheel, or Ctrl with a trackpad, zooms; a trackpad alone scrolls."""
        trackpad = not event.pixelDelta().isNull()
        if trackpad and not event.modifiers() & Qt.ControlModifier:
            super().wheelEvent(event)
            return
        self.zoom(1.2 ** (event.angleDelta().y() / 120))

    def viewportEvent(self, event) -> bool:  # pylint: disable=invalid-name
        """Pinching a trackpad zooms."""
        if (event.type() == QEvent.NativeGesture
                and event.gestureType() == Qt.ZoomNativeGesture):
            self.zoom(1 + event.value())
            return True
        return super().viewportEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # pylint: disable=invalid-name
        """Double clicking a node pops it out."""
        item = self.scene().whole_at(self.mapToScene(event.position().toPoint()))
        if item is not None:
            self.node_activated.emit(item.node.id)
        super().mouseDoubleClickEvent(event)


def _font(pixels: int) -> QFont:
    font = QFont()
    font.setPixelSize(pixels)
    font.setBold(True)
    return font


@lru_cache(maxsize=None)
def _fitted_size(text: str, width: float, height: float, largest: int) -> int:
    for pixels in range(largest, 7, -1):
        bounds = QFontMetricsF(_font(pixels)).boundingRect(
            QRectF(0, 0, 10000, 10000), Qt.AlignCenter, text)
        if bounds.width() <= width and bounds.height() <= height:
            return pixels
    return 8


def _fitted_font(text: str, rect: QRectF, largest: int) -> QFont:
    """The largest bold font, up to `largest` pixels, that fits `text` in `rect`."""
    return _font(_fitted_size(text, rect.width(), rect.height(), largest))
