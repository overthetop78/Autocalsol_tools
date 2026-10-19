from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings


APPLICATION_NAME = "AutocalsolTools"


@dataclass(frozen=True, slots=True)
class ApplicationDirectories:
    root: Path
    data: Path
    output: Path


def application_directories(root: Path | None = None) -> ApplicationDirectories:
    """Create the fixed data/output folders used by Duplicate Finder."""
    if root is None:
        root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]
    data = root / "data"
    output = root / "output"
    data.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    return ApplicationDirectories(root=root, data=data, output=output)


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
            target.setValue(key, value)
