from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSettings


APPLICATION_NAME = "AutocalsolTools"


def settings_file_path() -> Path:
    """Return the visible per-user INI file used by the application."""
    if override := os.environ.get("AUTOCALSOL_CONFIG_DIR"):
        return Path(override) / "settings.ini"
    if appdata := os.environ.get("APPDATA"):
        root = Path(appdata)
    elif config_home := os.environ.get("XDG_CONFIG_HOME"):
        root = Path(config_home)
    else:
        root = Path.home() / ".config"
    return root / APPLICATION_NAME / "settings.ini"


def create_settings() -> QSettings:
    path = settings_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    settings = QSettings(str(path), QSettings.Format.IniFormat)
    if not settings.contains("general/ini_initialized"):
        _migrate_legacy_directory_settings(settings)
        settings.setValue("general/ini_initialized", True)
        settings.sync()
    return settings


def default_work_directory() -> Path:
    documents = Path.home() / "Documents"
    return (documents if documents.is_dir() else Path.home()) / "Autocalsol Tools"


def _migrate_legacy_directory_settings(target: QSettings) -> None:
    """Copy useful folders/options from the former registry settings.

    Deliberately excludes selected source files and duplicate file lists: the
    application remembers directories, never the user's input files.
    """
    legacy = QSettings(APPLICATION_NAME, APPLICATION_NAME)
    allowed_keys = (
        "conversion/source_dir",
        "conversion/output_dir",
        "conversion/step",
        "duplicates/source_dir",
        "duplicates/output_dir",
        "duplicates/recursive",
        "duplicates/business_mode",
        "duplicates/trim",
        "duplicates/lowercase",
        "duplicates/ignore_zero",
        "duplicates/ignore_unnamed",
        "duplicates/selected_columns",
    )
    for key in allowed_keys:
        if legacy.contains(key):
            value = legacy.value(key)
            if key == "duplicates/output_dir" and _is_old_application_output(value):
                continue
            target.setValue(key, value)


def _is_old_application_output(value: object) -> bool:
    path = Path(str(value))
    return path.name.casefold() == "output" and path.parent.name.casefold() == APPLICATION_NAME.casefold()
