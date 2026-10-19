from __future__ import annotations

import csv
from datetime import datetime

import pandas as pd

from autocalsol_tools.converter import ConversionOptions, _annual_frame
from autocalsol_tools.models import LoadCurvePoint


def point(timestamp: datetime, value: float = 1000, unit: str = "Watt") -> LoadCurvePoint:
    return LoadCurvePoint("123", "Site", timestamp, value, unit, "test", "Courbe", 2)


def test_common_year_has_exact_autocalsol_size():
    frame, duplicates, missing, step = _annual_frame(
        [point(datetime(2025, 1, 1, 0, 0)), point(datetime(2025, 1, 1, 0, 30))],
        2025,
        False,
        ConversionOptions(),
    )
    assert len(frame) == 17_520
    assert duplicates == 0
    assert missing == 17_518
    assert step == 30
    assert frame.iloc[-1]["datetime"] == pd.Timestamp("2025-12-31 23:30:00")


def test_leap_year_has_exact_autocalsol_size():
    frame, *_ = _annual_frame(
        [point(datetime(2024, 2, 29, 12, 0))], 2024, False, ConversionOptions()
    )
    assert len(frame) == 17_568


def test_five_minute_values_are_averaged_by_half_hour():
    points = [point(datetime(2025, 1, 1, 0, minute), minute) for minute in range(0, 30, 5)]
    frame, *_ = _annual_frame(points, 2025, False, ConversionOptions())
    assert frame.iloc[0]["valeur"] == 12.5


def test_duplicate_timestamps_are_averaged():
    frame, duplicates, *_ = _annual_frame(
        [point(datetime(2025, 1, 1), 100), point(datetime(2025, 1, 1), 300)],
        2025,
        False,
        ConversionOptions(),
    )
    assert duplicates == 1
    assert frame.iloc[0]["valeur"] == 200


def test_all_supported_output_steps_have_exact_annual_size():
    for step in (5, 10, 15, 30, 60):
        frame, *_ = _annual_frame(
            [point(datetime(2025, 1, 1), 100)],
            2025,
            False,
            ConversionOptions(output_step_minutes=step),
        )
        assert len(frame) == 365 * 24 * (60 // step)
        assert frame.iloc[-1]["datetime"] == pd.Timestamp(
            datetime(2025, 12, 31, 23, 60 - step)
        )

