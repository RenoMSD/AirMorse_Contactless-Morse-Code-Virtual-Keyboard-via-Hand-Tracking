from airmorse.config import AppConfig, SharedSettings, load_config, save_config
from airmorse.gesture.pinch import TAU_PINCH_MAX


def test_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    original = AppConfig(tau_pinch=0.22, tau_commit=1.1, inject_keys=True, always_on_top=True, camera_index=2, compact_mode=True)
    save_config(path, original)
    loaded = load_config(path)
    assert loaded.tau_pinch == 0.22
    assert loaded.tau_commit == 1.1
    assert loaded.inject_keys is True
    assert loaded.always_on_top is True
    assert loaded.camera_index == 2
    assert loaded.compact_mode is True


def test_out_of_range_values_are_clamped(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        '{"tau_pinch": 9, "tau_commit": 0.1, "inject_keys": "yes", "camera_index": -3}',
        encoding="utf-8",
    )
    loaded = load_config(path)
    assert loaded.tau_pinch == TAU_PINCH_MAX
    assert loaded.tau_commit == 0.5
    assert loaded.inject_keys is False
    assert loaded.camera_index == 0


def test_missing_and_corrupt_files_use_defaults(tmp_path):
    assert load_config(tmp_path / "missing.json") == AppConfig()
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    assert load_config(broken) == AppConfig()


def test_shared_settings_update():
    settings = SharedSettings(AppConfig())
    settings.set_tau_pinch(0.25)
    assert settings.snapshot()[0] == 0.25
    settings.set_tau_pinch(5)
    assert settings.snapshot()[0] == TAU_PINCH_MAX
