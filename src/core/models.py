from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LoadCurvePoint:
    meter_id: str
    label: str
    timestamp: datetime
    value: float
    unit: str
    source: str
    sheet: str
    row_number: int


@dataclass(frozen=True, slots=True)
class DetectedTable:
    source: Path
    sheet: str
    header_row: int
    columns: tuple[str, ...]
    estimated_rows: int


@dataclass(slots=True)
class ExportResult:
    path: Path
    meter_id: str
    label: str
    year: int
    row_count: int
    source_points: int
    duplicate_points: int
    missing_points: int
    source_step_minutes: int | None
    warnings: list[str] = field(default_factory=list)

