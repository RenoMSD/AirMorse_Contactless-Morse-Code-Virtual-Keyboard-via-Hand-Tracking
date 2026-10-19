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
    assert window.error_label.text() == "Chuỗi không hợp lệ ......"
    window.close()
    window.deleteLater()
    app.processEvents()


def test_capture_starts_off_and_ignores_gestures(app, tmp_path):
    from airmorse.gesture.pinch import INDEX_TIP
    from airmorse.ui.main_window import MainWindow

    window = MainWindow(start_camera=False, config_file=tmp_path / "config.json")
    assert window.capture_box.isChecked() is False
    window._ingest_finger(INDEX_TIP, 0.0)
    assert window.engine.buffer == ""
    assert window.engine.preview == ""

    window.capture_box.setChecked(True)
    window._ingest_finger(INDEX_TIP, 1.0)
    assert window.engine.buffer == "."

    window.capture_box.setChecked(False)
    assert window.engine.buffer == ""
    assert window.engine.preview == ""
    window._ingest_finger(INDEX_TIP, 2.0)
    window._poll_commit()
    assert window.engine.preview == ""
    window.close()
    window.deleteLater()
    app.processEvents()


def test_thumbs_up_starts_capture_and_thumbs_down_stops_it(app, tmp_path):
    from airmorse.gesture.pinch import INDEX_TIP
    from airmorse.gesture.thumb import THUMB_DOWN, THUMB_UP
    from airmorse.ui.main_window import MainWindow

    window = MainWindow(start_camera=False, config_file=tmp_path / "config.json")
    window._handle_tokens([(THUMB_UP, 0.0)])
    assert window.capture_box.isChecked() is True
    assert window.engine.preview == ""

    window._dispatch(window.engine.on_finger(INDEX_TIP, 1.0))
    assert window.engine.buffer == "."
    window._handle_tokens([(THUMB_DOWN, 2.0), (INDEX_TIP, 2.0)])
    assert window.capture_box.isChecked() is False
    assert window.engine.buffer == ""
    assert window.engine.preview == ""
    window.close()
    window.deleteLater()
    app.processEvents()


def test_enter_adds_a_newline_and_flashes_the_key(app, tmp_path):
    from airmorse.gesture.pinch import ENTER, INDEX_TIP
    from airmorse.ui.main_window import MainWindow

    window = MainWindow(start_camera=False, config_file=tmp_path / "config.json")
    window._dispatch(window.engine.on_finger(INDEX_TIP, 0.0))
    window._dispatch(window.engine.on_finger(ENTER, 0.1))
    assert window.preview.text() == "E\n"
    assert window.keyboard._active == "\n"
    assert window.engine.buffer == ""
    window.close()
    window.deleteLater()
    app.processEvents()


def test_newline_prosign_flashes_enter(app, tmp_path):
    from airmorse.gesture.pinch import INDEX_TIP, MIDDLE_TIP
    from airmorse.ui.main_window import MainWindow

    window = MainWindow(start_camera=False, config_file=tmp_path / "config.json")
    clock = 0.0
    for symbol in ".-.-":
        finger = INDEX_TIP if symbol == "." else MIDDLE_TIP
        window._dispatch(window.engine.on_finger(finger, clock))
        clock += 0.05
    window._dispatch(window.engine.poll(clock + 0.8))
    assert window.preview.text() == "\n"
    assert window.keyboard._active == "\n"
    window.close()
    window.deleteLater()
    app.processEvents()


def test_lowercase_toggle_changes_new_letters_only(app, tmp_path):
    from airmorse.gesture.pinch import INDEX_TIP
    from airmorse.ui.main_window import MainWindow

    window = MainWindow(start_camera=False, config_file=tmp_path / "config.json")
    window.capture_box.setChecked(True)
    assert window.case_box.isChecked() is True
    window._dispatch(window.engine.on_finger(INDEX_TIP, 0.0))
    window._dispatch(window.engine.poll(0.8))
    assert window.preview.text() == "E"

    window.case_box.setChecked(False)
    assert window.keyboard._uppercase is False
    assert window.preview.text() == "E"
    window._dispatch(window.engine.on_finger(INDEX_TIP, 2.0))
    window._dispatch(window.engine.poll(3.0))
    assert window.preview.text() == "Ee"
    assert window.keyboard._active == "E"
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
