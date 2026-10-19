import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture
def app():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_window_shows_committed_s(app, tmp_path):
    from airmorse.gesture.pinch import INDEX_TIP
    from airmorse.ui.main_window import MainWindow

    window = MainWindow(start_camera=False, config_file=tmp_path / "config.json")
    clock = 0.0
    for _ in range(3):
        window._dispatch(window.engine.on_finger(INDEX_TIP, clock))
        clock += 0.2
    window._dispatch(window.engine.poll(clock + 0.8))
    assert window.engine.preview == "S"
    assert window.preview.text() == "S"
    assert window.keyboard._active == "S"
    assert window.engine.buffer == ""
    window.close()
    window.deleteLater()
    app.processEvents()


def test_unknown_sequence_warns_without_text(app, tmp_path):
    from airmorse.gesture.pinch import INDEX_TIP
    from airmorse.ui.main_window import MainWindow

    window = MainWindow(start_camera=False, config_file=tmp_path / "config.json")
    clock = 0.0
    for _ in range(6):
        window._dispatch(window.engine.on_finger(INDEX_TIP, clock))
        clock += 0.05
    window._dispatch(window.engine.poll(clock + 1))
    assert window.engine.preview == ""
    assert window.error_label.text() == "Unknown sequence ......"
    window.close()
    window.deleteLater()
    app.processEvents()


def test_sliders_change_thresholds_immediately(app, tmp_path):
    from airmorse.ui.main_window import MainWindow

    window = MainWindow(start_camera=False, config_file=tmp_path / "config.json")
    window.pinch_slider.setValue(25)
    window.commit_slider.setValue(120)
    assert window.settings.snapshot()[0] == pytest.approx(0.25)
    assert window.engine.tau_commit == pytest.approx(1.2)
    window.close()
    window.deleteLater()
    app.processEvents()


def test_compact_toggle_switches_views_and_persists(app, tmp_path):
    from airmorse.config import load_config
    from airmorse.ui.main_window import MINI_IDLE_OPACITY, MainWindow

    config_file = tmp_path / "config.json"
    window = MainWindow(start_camera=False, config_file=config_file)
    window.show()
    window.compact_button.click()
    assert window.compact
    assert window.full_page.isHidden() and not window.mini.isHidden()
    assert window.height() < 600
    assert window.windowOpacity() == pytest.approx(MINI_IDLE_OPACITY, abs=0.01)
    assert load_config(config_file).compact_mode is True

    tall = window.height()
    window.mini.chart_toggle.click()
    assert not window.mini.chart_open
    assert window.height() < tall

    window.mini.expand_button.click()
    assert not window.compact
    assert window.mini.isHidden() and not window.full_page.isHidden()
    assert window.windowOpacity() == pytest.approx(1.0)
    assert load_config(config_file).compact_mode is False
    window.close()
    window.deleteLater()
    app.processEvents()


def test_compact_view_tracks_buffer_and_text(app, tmp_path):
    from airmorse.gesture.pinch import INDEX_TIP, MIDDLE_TIP
    from airmorse.ui.main_window import MainWindow

    window = MainWindow(start_camera=False, config_file=tmp_path / "config.json")
    window.set_compact(True)
    window._dispatch(window.engine.on_finger(INDEX_TIP, 0.0))
    assert window.mini.grid.state_of("E") == "match"
    assert window.mini.grid.state_of("R") == "prefix"
    assert window.mini.grid.state_of("T") == "dim"
    window._dispatch(window.engine.on_finger(MIDDLE_TIP, 0.1))
    window._dispatch(window.engine.on_finger(INDEX_TIP, 0.2))
    assert window.mini.buffer_label.text() == "· – ·"
    assert window.mini.match_label.text() == "R"
    window._dispatch(window.engine.poll(2.0))
    assert window.mini.output.text() == "R"
    assert window.mini.grid.state_of("T") == "normal"

    window.mini.copy_button.click()
    assert app.clipboard().text() == "R"
    window.mini.clear_button.click()
    assert window.engine.preview == ""
    assert window.mini.output.text() == ""
    window.close()
    window.deleteLater()
    app.processEvents()


def test_compact_sliders_mirror_full_sliders(app, tmp_path):
    from airmorse.ui.main_window import MainWindow

    window = MainWindow(start_camera=False, config_file=tmp_path / "config.json")
    window.mini.commit_slider.setValue(120)
    assert window.commit_slider.value() == 120
    assert window.engine.tau_commit == pytest.approx(1.2)
    window.pinch_slider.setValue(25)
    assert window.mini.pinch_slider.value() == 25
    assert window.mini.pinch_value.text() == "0.25"
    window.close()
    window.deleteLater()
    app.processEvents()
