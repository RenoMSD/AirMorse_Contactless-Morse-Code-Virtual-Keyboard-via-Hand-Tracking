import os

import pytest
from PyQt6.QtCore import QPoint, QRect

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture
def app():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_mini_widget_collapsed_and_expanded_dimensions(app):
    from airmorse.ui.mini_widget import (
        MINI_HEIGHT_COLLAPSED,
        MINI_HEIGHT_EXPANDED,
        MINI_WIDTH,
        MiniWidget,
    )

    widget = MiniWidget()
    assert widget.is_expanded is False
    assert widget.width() == MINI_WIDTH
    assert widget.height() == MINI_HEIGHT_COLLAPSED
    assert widget.morse_drawer.isHidden() is True

    widget.toggle_expanded()
    assert widget.is_expanded is True
    assert widget.width() == MINI_WIDTH
    assert widget.height() == MINI_HEIGHT_EXPANDED
    assert widget.morse_drawer.isHidden() is False
    assert "Thu gọn" in widget.toggle_drawer_btn.text()

    widget.set_expanded(False)
    assert widget.is_expanded is False
    assert widget.height() == MINI_HEIGHT_COLLAPSED
    assert "Mở bảng mã" in widget.toggle_drawer_btn.text()
    widget.close()
    widget.deleteLater()
    app.processEvents()


def test_mini_widget_edge_flash_feedback_colors(app):
    from airmorse.ui.mini_widget import (
        COLOR_DASH,
        COLOR_DELETE,
        COLOR_DOT,
        COLOR_ENTER,
        MiniWidget,
    )

    widget = MiniWidget()
    assert widget.edge_flash_color is None

    widget.flash_edge_for_event("symbol", ".")
    assert widget.edge_flash_color == COLOR_DOT

    widget.flash_edge_for_event("symbol", "-")
    assert widget.edge_flash_color == COLOR_DASH

    widget.flash_edge_for_event("space", " ")
    assert widget.edge_flash_color == COLOR_ENTER

    widget.flash_edge_for_event("backspace", "A")
    assert widget.edge_flash_color == COLOR_DELETE

    widget._clear_edge_flash()
    assert widget.edge_flash_color is None
    widget.close()
    widget.deleteLater()
    app.processEvents()


def test_mini_widget_dynamic_opacity(app):
    from airmorse.ui.mini_widget import ACTIVE_OPACITY, IDLE_OPACITY, MiniWidget

    widget = MiniWidget()
    assert widget.windowOpacity() == pytest.approx(IDLE_OPACITY, abs=0.02)

    widget.set_hand_present(True)
    assert widget.windowOpacity() == pytest.approx(ACTIVE_OPACITY, abs=0.02)

    widget.set_hand_present(False)
    assert widget.windowOpacity() == pytest.approx(IDLE_OPACITY, abs=0.02)
    widget.close()
    widget.deleteLater()
    app.processEvents()


def test_magnetic_window_snapping_to_corners():
    from airmorse.ui.mini_widget import compute_snap_position

    screen = QRect(0, 0, 1920, 1080)
    # Near top-left corner (< 20px from left and top)
    rect_tl = QRect(8, 14, 340, 160)
    pos_tl = compute_snap_position(rect_tl, screen, margin=20, corner_padding=12)
    assert pos_tl == QPoint(12, 12)

    # Near bottom-right corner (< 20px from right and bottom)
    rect_br = QRect(1920 - 340 - 10, 1080 - 160 - 5, 340, 160)
    pos_br = compute_snap_position(rect_br, screen, margin=20, corner_padding=12)
    assert pos_br == QPoint(1920 - 340 - 12, 1080 - 160 - 12)

    # Far from edges -> stays where placed
    rect_mid = QRect(500, 400, 340, 160)
    pos_mid = compute_snap_position(rect_mid, screen, margin=20, corner_padding=12)
    assert pos_mid == QPoint(500, 400)


def test_dashboard_and_mini_mode_switching_and_overlay(app, tmp_path):
    from airmorse.gesture.pinch import INDEX_TIP, MIDDLE_TIP
    from airmorse.ui.main_window import MainWindow

    window = MainWindow(start_camera=False, config_file=tmp_path / "config.json")
    window.show()
    assert window.is_mini_mode is False

    # Switch to Mini mode
    window.enter_mini_mode()
    assert window.is_mini_mode is True
    assert window.isVisible() is False

    # Feed Morse R (.-.) and check both Dashboard overlay & MiniWidget signal
    window.capture_box.setChecked(True)
    window._ingest_finger(INDEX_TIP, 1.0)
    window._ingest_finger(MIDDLE_TIP, 1.1)
    window._ingest_finger(INDEX_TIP, 1.2)
    window._refresh_overlay(1.5)

    assert "· — ·" in window.overlay_signal_label.text()
    assert "(Ký tự: R)" in window.overlay_signal_label.text()
    assert "· — ·" in window.mini_widget.signal_label.text()
    assert "[R]" in window.mini_widget.signal_label.text()
    assert window.commit_bar.ratio > 0.0
    assert window.mini_widget.commit_bar.ratio > 0.0

    # Expand back to Full Dashboard
    window.exit_mini_mode()
    assert window.is_mini_mode is False
    assert window.isVisible() is True

    window.close()
    window.deleteLater()
    app.processEvents()
