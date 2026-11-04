"""Tests for the light path GUI layout and window, on Qt's offscreen platform."""
import os
from collections import Counter

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

# pylint: disable=wrong-import-position
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from hispec_gui.lightpath.layout import LINES, NODES, NODES_BY_ID
from hispec_gui.lightpath.state import MOCK_PATHS, MockSource, Status
from hispec_gui.lightpath.theme import DARK, LIGHT
from hispec_gui.lightpath.window import LightPathWindow


@pytest.fixture(name="window", scope="module")
def fixture_window():
    """A window on a started mock source."""
    app = QApplication.instance() or QApplication([])
    source = MockSource()
    window = LightPathWindow(source)
    window.show()
    source.start()
    yield window
    window.close()
    app.processEvents()


def test_node_ids_are_unique():
    """Every node id is used once."""
    duplicates = [nid for nid, n in Counter(node.id for node in NODES).items() if n > 1]
    assert not duplicates


def test_lines_join_known_nodes():
    """Every line starts and ends at a node in the layout."""
    for line in LINES:
        assert line.a in NODES_BY_ID, line
        assert line.b in NODES_BY_ID, line


def test_mock_paths_follow_lines():
    """Each step of a mock path is along a line, so the whole path lights."""
    joined = {frozenset((line.a, line.b)) for line in LINES}
    for name, path in MOCK_PATHS.items():
        for step in zip(path, path[1:]):
            assert frozenset(step) in joined, (name, step)


def test_starts_grey_with_the_panel_hidden(window):
    """Nothing is lit until a path is chosen, and the details panel is off."""
    assert not any(item.lit for item in window.scene.line_items)
    assert not any(item.lit for item in window.scene.node_items.values())
    assert window.dock.isHidden()


def test_selecting_a_node_shows_it_in_the_panel(window):
    """Clicking a node fills the side panel with its daemon."""
    window.scene.select("lsm")
    assert window.panel.title.text() == "LSM"
    assert window.panel.daemon.text() == "hsfei.lsm"
    window.scene.select(None)
    assert window.panel.node_id is None


def test_fibre_ports_are_titled_and_served_by_tib(window):
    """The fibre ports belong to the TIB daemon, and say so when selected."""
    window.scene.select("sci_red")
    assert window.panel.title.text() == "TIB Red Science"
    assert window.panel.daemon.text() == "hsfibers.tib"
    window.scene.select("lantern")
    assert window.panel.title.text() == "TIB Blue Lantern"
    window.scene.select(None)


@pytest.mark.parametrize("node_id, title, daemon", [
    ("ld2_red", "TIB Red LD2", "hsfibers.tib"),
    ("bpd", "TIB Blue BPD", "hsfibers.tib"),
    ("j_gc", "CS Red Switch", "hsfibers.csred"),
    ("j_cath", "CS Blue Switch", "hsfibers.csblue"),
    ("as_red", "AS Red", "hsfibers.asred"),
    ("as_blue", "AS Blue", "hsfibers.asblue"),
])
def test_fibers_daemons(node_id, title, daemon):
    """The fibre subsystem's nodes name their hsfibers daemon."""
    node = NODES_BY_ID[node_id]
    assert (node.title, node.daemon) == (title, daemon)


def test_clicking_is_or_slit_block_selects_the_spectrograph(window):
    """IS and slit block belong to their SPEC box, so clicking them selects it."""
    for part, whole in (("slit_red", "spec_red"), ("is_blue", "spec_blue")):
        point = window.view.mapFromScene(QPointF(*NODES_BY_ID[part].pos))
        QTest.mouseClick(window.view.viewport(), Qt.LeftButton, pos=point)
        assert window.panel.node_id == whole
    window.scene.select(None)


def test_status_reaches_the_diagram(window):
    """A status from the source shows on the node's light."""
    window.source.status_changed.emit("ms", Status.FAULT)
    assert window.scene.node_items["ms"].status is Status.FAULT


def test_mock_path_lights_lines(window):
    """Choosing a mock path lights the lines along it and nothing else."""
    window.source.set_path("Science → Blue")
    lit = {(item.line.a, item.line.b) for item in window.scene.line_items
           if item.pen().widthF() > 5}
    assert ("k_piaa", "bpiaa") in lit
    assert ("k_fam_blue", "sci_blue") in lit
    assert ("k_fam_blue", "lantern") not in lit
    assert ("k_piaa", "rpiaa") not in lit
    window.source.set_path("None")
    assert all(item.pen().widthF() == 5 for item in window.scene.line_items)


def test_spectrograph_lights_from_slit_block_or_is(window):
    """Light reaching a slit block or IS lights its spectrograph."""
    items = window.scene.node_items
    window.source.set_path("Science → Red")
    assert items["spec_red"].lit and not items["spec_blue"].lit
    window.source.set_path("Blackbody → IS Red")
    assert items["spec_red"].lit
    window.source.set_path("None")
    assert not items["spec_red"].lit


def test_pop_out_opens_one_window_per_node(window):
    """Popping out a node twice raises the same window."""
    window.pop_out("adc")
    first = window.popups["adc"]
    window.pop_out("adc")
    assert window.popups["adc"] is first
    assert first.node_id == "adc"


def test_dark_mode_switches_the_whole_window(window):
    """Toggling dark mode recolours the diagram and the widgets."""
    window.dark_mode.setChecked(True)
    assert window.scene.theme is DARK
    assert window.scene.backgroundBrush().color().name() == DARK.background
    assert QApplication.instance().palette().base().color().name() == DARK.background
    window.dark_mode.setChecked(False)
    assert window.scene.theme is LIGHT


def test_zoom_stays_between_fitted_and_max(window):
    """Zooming out never goes below fitted, and zooming in is capped."""
    view = window.view
    view.fit()
    fitted = view.transform().m11()
    view.zoom(0.5)
    assert view.transform().m11() == pytest.approx(fitted)
    view.zoom(100)
    assert view.transform().m11() == pytest.approx(fitted * view.MAX_ZOOM)
    view.fit()
    assert view.transform().m11() == pytest.approx(fitted)
