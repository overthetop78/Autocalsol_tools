from __future__ import annotations

import calendar
import csv
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd

from .loader import load_curve_points
from .models import ExportResult, LoadCurvePoint
from .normalization import normalized_text, safe_filename


ProgressCallback = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class ConversionOptions:
    output_step_minutes: int = 30
    legacy_csv_multiplier: float = 1000.0
    fill_method: str = "ffill_bfill"
    round_to_integer: bool = True


def convert_to_autocalsol(
    input_path: str | Path,
    output_directory: str | Path,
    *,
    options: ConversionOptions | None = None,
    progress: ProgressCallback | None = None,
) -> list[ExportResult]:
    source = Path(input_path)
    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=True)
    settings = options or ConversionOptions()
    points, _, load_warnings = load_curve_points(source, progress=progress)

    if progress:
        progress(f"Étape 3/3 — Consolidation de {len(points):,} mesure(s) par compteur…".replace(",", " "))
    groups: dict[str, list[LoadCurvePoint]] = {}
    for point in points:
        groups.setdefault(point.meter_id, []).append(point)

    if progress:
        progress(f"{len(groups)} compteur(s) détecté(s). Création des fichiers CSV…")

    results: list[ExportResult] = []
    for meter_id, meter_points in sorted(groups.items()):
        label = Counter(point.label for point in meter_points).most_common(1)[0][0]
        for year in sorted({point.timestamp.year for point in meter_points}):
            annual_points = [point for point in meter_points if point.timestamp.year == year]
            if progress:
                progress(f"Préparation du compteur {meter_id}, année {year}…")
            frame, duplicate_count, missing_count, source_step = _annual_frame(
                annual_points, year, source.suffix.casefold() == ".csv", settings
            )
            step_label = "1h" if settings.output_step_minutes == 60 else f"{settings.output_step_minutes}min"
            filename = f"{safe_filename(label)}_{safe_filename(meter_id)}_{year}_{step_label}_Autocalsol.csv"
            output_path = _unique_path(destination / filename)
            _write_autocalsol_csv(frame, output_path, settings.round_to_integer)
            if progress:
                progress(f"Fichier créé : {output_path.name} ({len(frame):,} lignes)".replace(",", " "))
            warnings = list(load_warnings)
            if duplicate_count:
                warnings.append(
                    f"{duplicate_count} horodatage(s) en double consolidé(s) par moyenne."
                )
            results.append(
                ExportResult(
                    path=output_path,
                    meter_id=meter_id,
                    label=label,
                    year=year,
                    row_count=len(frame),
                    source_points=len(annual_points),
                    duplicate_points=duplicate_count,
                    missing_points=missing_count,
                    source_step_minutes=source_step,
                    warnings=warnings,
                )
            )
    return results


def _annual_frame(
    points: list[LoadCurvePoint],
    year: int,
    legacy_csv: bool,
    options: ConversionOptions,
) -> tuple[pd.DataFrame, int, int, int | None]:
    raw = pd.DataFrame(
        {
            "datetime": [point.timestamp for point in points],
            "value": [_normalized_unit_value(point, legacy_csv, options) for point in points],
        }
    ).sort_values("datetime")
    if raw.empty:
        raise ValueError(f"Aucune mesure pour {year}")

    counts = raw.groupby("datetime").size()
    duplicate_count = int((counts - 1).clip(lower=0).sum())
    exact = raw.groupby("datetime", sort=True)["value"].mean()
    source_step = _source_step_minutes(exact.index)

    step = options.output_step_minutes
    if step not in {5, 10, 15, 30, 60}:
        raise ValueError(f"Pas de sortie non supporté : {step} minutes")
    # Les mesures en watts sont moyennées dans chaque créneau demandé. Une
    # série moins fine produit des trous, ensuite complétés comme add_missing_times.
    bucketed = exact.groupby(exact.index.floor(f"{step}min")).mean()
    start = datetime(year, 1, 1)
    end = datetime(year, 12, 31, 23, 60 - step)
    expected = pd.date_range(start=start, end=end, freq=f"{step}min")
    reindexed = bucketed.reindex(expected)
    missing_count = int(reindexed.isna().sum())

    if options.fill_method == "ffill_bfill":
        completed = reindexed.ffill().bfill()
    elif options.fill_method == "interpolate":
        completed = reindexed.interpolate(method="time").ffill().bfill()
    elif options.fill_method == "zero":
        completed = reindexed.fillna(0)
    else:
        raise ValueError(f"Méthode de remplissage inconnue : {options.fill_method}")
    if completed.isna().any():
        raise ValueError(f"Impossible de compléter l'année {year}")

    expected_count = (366 if calendar.isleap(year) else 365) * 24 * (60 // step)
    if len(completed) != expected_count:
        raise AssertionError(f"Nombre de lignes annuel incorrect : {len(completed)}")
    frame = pd.DataFrame({"datetime": expected, "valeur": completed.to_numpy()})
    return frame, duplicate_count, missing_count, source_step


def _normalized_unit_value(
    point: LoadCurvePoint,
    legacy_csv: bool,
    options: ConversionOptions,
) -> float:
    unit = normalized_text(point.unit).replace(" ", "")
    if unit in {"kw", "kwh"}:
        return point.value * 1000.0
    if unit in {"w", "watt", "watts", "wh"}:
        return point.value
    if legacy_csv:
        return point.value * options.legacy_csv_multiplier
    return point.value


def _source_step_minutes(index: pd.DatetimeIndex) -> int | None:
    if len(index) < 2:
        return None
    differences = index.to_series().diff().dropna().dt.total_seconds().div(60)
    positive = differences[differences > 0]
    if positive.empty:
        return None
    return int(round(float(positive.mode().iloc[0])))


def _write_autocalsol_csv(frame: pd.DataFrame, path: Path, round_to_integer: bool) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, delimiter=";", lineterminator="\n")
        writer.writerow(("date", "heure", "valeur"))
        for timestamp, value in frame[["datetime", "valeur"]].itertuples(index=False, name=None):
            output_value: int | str
            if round_to_integer:
                output_value = int(round(float(value)))
            else:
                output_value = format(float(value), ".12g").replace(".", ",")
            writer.writerow((timestamp.strftime("%d/%m/%Y"), timestamp.strftime("%H:%M:%S"), output_value))


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_stem(f"{path.stem}_{counter}")
        if not candidate.exists():
            return candidate
        counter += 1

