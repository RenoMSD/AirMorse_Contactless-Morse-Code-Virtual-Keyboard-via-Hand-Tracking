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
