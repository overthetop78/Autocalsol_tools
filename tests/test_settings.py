from pathlib import Path

from src.utils.settings import create_settings, settings_file_path


def test_settings_are_written_to_visible_ini(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("AUTOCALSOL_CONFIG_DIR", str(config_dir))

    settings = create_settings()
    settings.setValue("conversion/source_dir", str(tmp_path / "sources"))
    settings.sync()

    assert settings_file_path() == config_dir / "settings.ini"
    assert settings_file_path().is_file()
    assert "source_dir" in settings_file_path().read_text(encoding="utf-8")
