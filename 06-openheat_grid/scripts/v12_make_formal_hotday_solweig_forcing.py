"""
OpenHeat v1.2: build formal-hot-day UMEP SOLWEIG met forcing files.

Inputs:
    --input CSV path. If omitted, the script tries these paths in order:
        data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_v091.csv
        data/calibration/v11/v11_station_weather_pairs_v091.csv
        data/calibration/v09_historical_forecast_by_station_hourly.csv
    --station station_id, default S128.
    --hours comma-separated SGT hours, default 13,15.
    --date optional YYYY-MM-DD local date. If omitted, the script selects a
        complete no-rain preferred formal hot day by mean shortwave radiation,
        then official WBGT if available, then air temperature.
    --out-dir output directory for single-hour UMEP met files.

Outputs when --write is passed:
    data/solweig/v12_formal_hotday_forcing/v12_formal_hotday_S128_h13.txt
    data/solweig/v12_formal_hotday_forcing/v12_formal_hotday_S128_h15.txt
    outputs/v12_solweig_typology_pilot/formal_hotday_forcing/formal_hotday_forcing_QA.csv
    outputs/v12_solweig_typology_pilot/formal_hotday_forcing/formal_hotday_forcing_QA.md

Saved metrics:
    The QA CSV and Markdown record the selected source CSV, local date, station,
    hour, source row counts collapsed into each station-hour weather record,
    required weather fields, optional rain/cloud/WBGT fields, Kdiff/Kdir values,
    output files, selection mode, and any global-only radiation warning.

This script only writes UMEP meteorological forcing and QA summaries. It does
not run QGIS or SOLWEIG, generate rasters, build hazard/risk maps, convert Tmrt
to WBGT, or train surrogate/ML models.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


DEFAULT_INPUTS = (
    Path("data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_v091.csv"),
    Path("data/calibration/v11/v11_station_weather_pairs_v091.csv"),
    Path("data/calibration/v09_historical_forecast_by_station_hourly.csv"),
)
DEFAULT_OUT_DIR = Path("data/solweig/v12_formal_hotday_forcing")
QA_DIR = Path("outputs/v12_solweig_typology_pilot/formal_hotday_forcing")

TIME_COLUMNS = ("time_sgt", "timestamp_sgt")
REQUIRED_WEATHER_COLUMNS = (
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "shortwave_radiation",
)
RADIATION_COLUMNS = ("diffuse_radiation", "direct_radiation")
OPTIONAL_COLUMNS = (
    "cloud_cover",
    "diffuse_radiation",
    "direct_radiation",
    "rain",
    "official_wbgt_c",
)
UMEP_COLUMNS = (
    "iy",
    "id",
    "it",
    "imin",
    "qn",
    "qh",
    "qe",
    "qs",
    "qf",
    "U",
    "RH",
    "Tair",
    "pres",
    "rain",
    "kdown",
    "snow",
    "ldown",
    "fcld",
    "wuh",
    "xsmd",
    "lai_hr",
    "Kdiff",
    "Kdir",
    "Wd",
)
UMEP_HEADER = (
    "%iy id it imin qn qh qe qs qf U RH Tair pres rain kdown snow ldown "
    "fcld wuh xsmd lai_hr Kdiff Kdir Wd"
)
SELECTION_MODE = "max_shortwave_then_wbgt"


@dataclass(frozen=True)
class SelectionResult:
    input_path: Path
    time_column: str
    station: str
    hours: tuple[int, ...]
    selected_date: str
    selection_mode: str
    hourly_rows: pd.DataFrame
    warnings: tuple[str, ...]


def parse_hours(value: str) -> tuple[int, ...]:
    """Parse a comma-separated hour list while preserving requested order."""
    try:
        hours = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid --hours value: {value!r}") from exc

    if not hours:
        raise argparse.ArgumentTypeError("--hours must include at least one hour")
    bad_hours = [hour for hour in hours if hour < 0 or hour > 23]
    if bad_hours:
        raise argparse.ArgumentTypeError(f"Hours must be between 0 and 23: {bad_hours}")
    if len(set(hours)) != len(hours):
        raise argparse.ArgumentTypeError(f"Duplicate hours are not allowed: {value!r}")
    return hours


def existing_default_input() -> Path:
    """Return the first existing default input path."""
    for path in DEFAULT_INPUTS:
        if path.exists():
            return path
    searched = "\n  - ".join(str(path) for path in DEFAULT_INPUTS)
    raise FileNotFoundError(f"No default input CSV found. Searched:\n  - {searched}")


def resolve_input_path(input_path: str | None) -> Path:
    """Resolve an explicit input path or the first existing default CSV."""
    if input_path:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Input CSV not found: {path}")
        return path
    return existing_default_input()


def find_time_column(columns: Iterable[str]) -> str:
    """Find the accepted local timestamp column."""
    column_set = set(columns)
    for column in TIME_COLUMNS:
        if column in column_set:
            return column
    raise KeyError(f"Input CSV must contain one of {TIME_COLUMNS}; got no local time column")


def validate_columns(df: pd.DataFrame, allow_global_only: bool) -> None:
    """Validate required fields before selection and forcing generation."""
    missing = [column for column in ("station_id", *REQUIRED_WEATHER_COLUMNS) if column not in df.columns]
    if missing:
        raise KeyError(f"Input CSV is missing required columns: {missing}")

    missing_radiation = [column for column in RADIATION_COLUMNS if column not in df.columns]
    if missing_radiation and not allow_global_only:
        raise KeyError(
            "Input CSV is missing SOLWEIG direct/diffuse radiation columns "
            f"{missing_radiation}. Pass --allow-global-only to write Kdiff=-999 and Kdir=-999."
        )


def load_hourly_weather(
    input_path: Path,
    station: str,
    hours: tuple[int, ...],
    allow_global_only: bool,
) -> tuple[pd.DataFrame, str]:
    """Load, filter, and collapse source rows to one weather record per local date/hour."""
    df = pd.read_csv(input_path, low_memory=False).copy()
    time_column = find_time_column(df.columns)
    validate_columns(df, allow_global_only=allow_global_only)

    df["_local_time"] = pd.to_datetime(df[time_column], errors="coerce")
    if df["_local_time"].isna().all():
        raise ValueError(f"Could not parse any local timestamps from column {time_column!r}")

    df = df[df["station_id"].astype(str).eq(station)].copy()
    if df.empty:
        raise ValueError(f"Station {station} not found in {input_path}")

    df["_local_date"] = df["_local_time"].dt.date.astype(str)
    df["_hour"] = df["_local_time"].dt.hour
    df = df[df["_hour"].isin(hours)].copy()
    if df.empty:
        raise ValueError(f"No rows for station {station} at requested hours {list(hours)}")

    numeric_columns = [
        column
        for column in (*REQUIRED_WEATHER_COLUMNS, *OPTIONAL_COLUMNS)
        if column in df.columns
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    grouped = df.groupby(["_local_date", "_hour"], as_index=False, sort=True)
    hourly = grouped[numeric_columns].mean()
    hourly["n_source_rows"] = grouped.size()["size"].to_numpy()
    if "rain" in df.columns:
        rain_stats = grouped["rain"].agg(rain_min="min", rain_max="max")
        hourly = hourly.merge(rain_stats, on=["_local_date", "_hour"], how="left")

    missing_values = [
        column
        for column in REQUIRED_WEATHER_COLUMNS
        if hourly[column].isna().any()
    ]
    if missing_values:
        raise ValueError(
            "Required weather columns contain missing values after station-hour collapse: "
            f"{missing_values}"
        )

    return hourly, time_column


def complete_dates(hourly: pd.DataFrame, hours: tuple[int, ...]) -> list[str]:
    """Return dates where all requested hours are present."""
    requested = set(hours)
    complete = []
    for date_value, date_rows in hourly.groupby("_local_date"):
        if requested.issubset(set(date_rows["_hour"].astype(int))):
            complete.append(str(date_value))
    return sorted(complete)


def order_hours(hourly: pd.DataFrame, hours: tuple[int, ...]) -> pd.DataFrame:
    """Sort selected rows in the user's requested hour order."""
    hour_order = {hour: index for index, hour in enumerate(hours)}
    ordered = hourly.copy()
    ordered["_hour_order"] = ordered["_hour"].map(hour_order)
    return ordered.sort_values("_hour_order").drop(columns=["_hour_order"]).reset_index(drop=True)


def select_date_rows(
    hourly: pd.DataFrame,
    hours: tuple[int, ...],
    explicit_date: str | None,
) -> tuple[str, pd.DataFrame, tuple[str, ...]]:
    """Select the explicit date or rank complete candidate dates."""
    warnings: list[str] = []
    dates = complete_dates(hourly, hours)
    if explicit_date:
        if explicit_date not in dates:
            found = sorted(hourly.loc[hourly["_local_date"].eq(explicit_date), "_hour"].astype(int).unique())
            raise ValueError(
                f"Date {explicit_date} does not contain all requested hours {list(hours)}. "
                f"Found hours: {found}"
            )
        selected = hourly[hourly["_local_date"].eq(explicit_date)]
        return explicit_date, order_hours(selected, hours), tuple(warnings)

    if not dates:
        available = sorted(hourly["_local_date"].unique().tolist())[:10]
        raise ValueError(
            f"No dates contain all requested hours {list(hours)}. "
            f"Example available dates after filtering: {available}"
        )

    candidates = hourly[hourly["_local_date"].isin(dates)].copy()
    ranked_source = candidates
    if "rain" in candidates.columns and "rain_max" in candidates.columns:
        rain_by_date = candidates.groupby("_local_date")["rain_max"].max()
        dry_dates = rain_by_date[rain_by_date.abs().le(1e-9)].index.tolist()
        if dry_dates:
            ranked_source = candidates[candidates["_local_date"].isin(dry_dates)].copy()
        else:
            warnings.append(
                "No complete candidate date has rain == 0 for all requested hours; "
                "selected from all complete dates."
            )

    aggregations = {
        "mean_shortwave_radiation": ("shortwave_radiation", "mean"),
        "mean_temperature_2m": ("temperature_2m", "mean"),
    }
    if "official_wbgt_c" in ranked_source.columns:
        aggregations["mean_official_wbgt_c"] = ("official_wbgt_c", "mean")

    ranking = ranked_source.groupby("_local_date").agg(**aggregations).reset_index()
    sort_columns = ["mean_shortwave_radiation"]
    ascending = [False]
    if "mean_official_wbgt_c" in ranking.columns:
        sort_columns.append("mean_official_wbgt_c")
        ascending.append(False)
    sort_columns.extend(["mean_temperature_2m", "_local_date"])
    ascending.extend([False, True])
    ranking = ranking.sort_values(sort_columns, ascending=ascending, na_position="last")

    selected_date = str(ranking.iloc[0]["_local_date"])
    selected = ranked_source[ranked_source["_local_date"].eq(selected_date)]
    return selected_date, order_hours(selected, hours), tuple(warnings)


def validate_selected_radiation(selected: pd.DataFrame, allow_global_only: bool) -> tuple[str, ...]:
    """Validate direct/diffuse columns or return warnings for global-only fallback."""
    warnings: list[str] = []
    missing_or_empty = [
        column
        for column in RADIATION_COLUMNS
        if column not in selected.columns or selected[column].isna().any()
    ]
    if not missing_or_empty:
        return tuple(warnings)

    message = (
        "Selected rows are missing direct/diffuse radiation values "
        f"{missing_or_empty}; Kdiff and Kdir will be written as -999."
    )
    if not allow_global_only:
        raise ValueError(message + " Pass --allow-global-only to continue.")

    warnings.append(message)
    return tuple(warnings)


def optional_number(row: pd.Series, column: str, fallback: float) -> float:
    """Return an optional numeric field with fallback for absent/NaN values."""
    if column not in row.index or pd.isna(row[column]):
        return fallback
    return float(row[column])


def build_umep_row(row: pd.Series, allow_global_only: bool) -> dict[str, float | int]:
    """Build one UMEP SOLWEIG met row from a selected station-hour record."""
    local_time = pd.Timestamp(f"{row['_local_date']} {int(row['_hour']):02d}:00:00")
    cloud_cover = optional_number(row, "cloud_cover", fallback=-999.0)
    fcld = -999.0 if cloud_cover == -999.0 else round(cloud_cover / 100.0, 3)

    if allow_global_only and (
        "diffuse_radiation" not in row.index
        or "direct_radiation" not in row.index
        or pd.isna(row.get("diffuse_radiation"))
        or pd.isna(row.get("direct_radiation"))
    ):
        kdiff = -999.0
        kdir = -999.0
    else:
        kdiff = round(float(row["diffuse_radiation"]), 1)
        kdir = round(float(row["direct_radiation"]), 1)

    return {
        "iy": int(local_time.year),
        "id": int(local_time.dayofyear),
        "it": int(local_time.hour),
        "imin": 0,
        "qn": -999,
        "qh": -999,
        "qe": -999,
        "qs": -999,
        "qf": -999,
        "U": round(max(float(row["wind_speed_10m"]), 0.5), 3),
        "RH": round(float(row["relative_humidity_2m"]), 1),
        "Tair": round(float(row["temperature_2m"]), 2),
        "pres": 1010,
        "rain": round(optional_number(row, "rain", fallback=0.0), 3),
        "kdown": round(float(row["shortwave_radiation"]), 1),
        "snow": 0,
        "ldown": -999,
        "fcld": fcld,
        "wuh": -999,
        "xsmd": -999,
        "lai_hr": -999,
        "Kdiff": kdiff,
        "Kdir": kdir,
        "Wd": 270,
    }


def row_to_line(record: dict[str, float | int]) -> str:
    """Format one UMEP record in the same whitespace-delimited style as v09."""
    frame = pd.DataFrame([record], columns=UMEP_COLUMNS)
    return frame.to_csv(sep=" ", index=False, header=False, float_format="%.3f").strip()


def forcing_path(out_dir: Path, station: str, hour: int) -> Path:
    """Return the v12 formal-hot-day forcing path for a station/hour."""
    return out_dir / f"v12_formal_hotday_{station}_h{hour:02d}.txt"


def write_forcing_files(
    selected: pd.DataFrame,
    out_dir: Path,
    station: str,
    allow_global_only: bool,
) -> list[dict[str, float | int | str]]:
    """Write one two-row UMEP file per selected hour and return QA records."""
    out_dir.mkdir(parents=True, exist_ok=True)
    qa_records: list[dict[str, float | int | str]] = []
    for _, row in selected.iterrows():
        hour = int(row["_hour"])
        record = build_umep_row(row, allow_global_only=allow_global_only)
        line = row_to_line(record)
        out_path = forcing_path(out_dir, station, hour)
        out_path.write_text(f"{UMEP_HEADER}\n{line}\n{line}\n", encoding="utf-8")

        qa_record: dict[str, float | int | str] = {
            "selected_date": str(row["_local_date"]),
            "station_id": station,
            "hour_sgt": hour,
            "n_source_rows": int(row["n_source_rows"]),
            "temperature_2m": round(float(row["temperature_2m"]), 3),
            "relative_humidity_2m": round(float(row["relative_humidity_2m"]), 3),
            "wind_speed_10m": round(float(row["wind_speed_10m"]), 3),
            "shortwave_radiation": round(float(row["shortwave_radiation"]), 3),
            "Kdiff_written": record["Kdiff"],
            "Kdir_written": record["Kdir"],
            "forcing_file": str(out_path),
        }
        for column in ("cloud_cover", "rain", "official_wbgt_c", "rain_min", "rain_max"):
            if column in row.index and not pd.isna(row[column]):
                qa_record[column] = round(float(row[column]), 3)
        qa_records.append(qa_record)
    return qa_records


def build_qa_records(
    result: SelectionResult,
    out_dir: Path,
    allow_global_only: bool,
) -> list[dict[str, float | int | str]]:
    """Build QA records without writing forcing files."""
    qa_records: list[dict[str, float | int | str]] = []
    for _, row in result.hourly_rows.iterrows():
        record = build_umep_row(row, allow_global_only=allow_global_only)
        qa_record: dict[str, float | int | str] = {
            "input_path": str(result.input_path),
            "time_column": result.time_column,
            "selection_mode": result.selection_mode,
            "selected_date": result.selected_date,
            "station_id": result.station,
            "hour_sgt": int(row["_hour"]),
            "n_source_rows": int(row["n_source_rows"]),
            "temperature_2m": round(float(row["temperature_2m"]), 3),
            "relative_humidity_2m": round(float(row["relative_humidity_2m"]), 3),
            "wind_speed_10m": round(float(row["wind_speed_10m"]), 3),
            "shortwave_radiation": round(float(row["shortwave_radiation"]), 3),
            "Kdiff_written": record["Kdiff"],
            "Kdir_written": record["Kdir"],
            "forcing_file": str(forcing_path(out_dir, result.station, int(row["_hour"]))),
            "qa_warnings": " | ".join(result.warnings),
        }
        for column in ("cloud_cover", "rain", "official_wbgt_c", "rain_min", "rain_max"):
            if column in row.index and not pd.isna(row[column]):
                qa_record[column] = round(float(row[column]), 3)
        qa_records.append(qa_record)
    return qa_records


def write_qa_outputs(qa_records: list[dict[str, float | int | str]], warnings: tuple[str, ...]) -> None:
    """Write machine-readable CSV plus short Markdown QA summary."""
    QA_DIR.mkdir(parents=True, exist_ok=True)
    qa_csv = QA_DIR / "formal_hotday_forcing_QA.csv"
    qa_md = QA_DIR / "formal_hotday_forcing_QA.md"
    frame = pd.DataFrame(qa_records)
    frame.to_csv(qa_csv, index=False)

    lines = [
        "# v12 formal-hot-day SOLWEIG forcing QA",
        "",
        "This summary documents meteorological forcing only. It does not validate local WBGT, "
        "run SOLWEIG, generate rasters, create hazard/risk maps, convert Tmrt to WBGT, "
        "or train a surrogate model.",
        "",
    ]
    if qa_records:
        first = qa_records[0]
        lines.extend(
            [
                f"- Input CSV: `{first['input_path']}`",
                f"- Time column: `{first['time_column']}`",
                f"- Station: `{first['station_id']}`",
                f"- Selected date: `{first['selected_date']}`",
                f"- Selection mode: `{first['selection_mode']}`",
                f"- QA CSV: `{qa_csv}`",
                "",
            ]
        )

    lines.append("## Warnings")
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None.")
    lines.extend(["", "## Selected Hours", ""])

    table_columns = [
        "hour_sgt",
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "shortwave_radiation",
        "Kdiff_written",
        "Kdir_written",
        "forcing_file",
    ]
    lines.append("| " + " | ".join(table_columns) + " |")
    lines.append("| " + " | ".join("---" for _ in table_columns) + " |")
    for record in qa_records:
        lines.append("| " + " | ".join(str(record.get(column, "")) for column in table_columns) + " |")

    qa_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def preview_selection(qa_records: list[dict[str, float | int | str]], warnings: tuple[str, ...]) -> None:
    """Print selected rows for dry-run review."""
    print("[selection]")
    if qa_records:
        first = qa_records[0]
        print(f"input_path = {first['input_path']}")
        print(f"time_column = {first['time_column']}")
        print(f"station_id = {first['station_id']}")
        print(f"selected_date = {first['selected_date']}")
        print(f"selection_mode = {first['selection_mode']}")
    if warnings:
        print("[warnings]")
        for warning in warnings:
            print(f"- {warning}")
    preview_columns = [
        "hour_sgt",
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "shortwave_radiation",
        "cloud_cover",
        "rain",
        "official_wbgt_c",
        "Kdiff_written",
        "Kdir_written",
        "n_source_rows",
        "forcing_file",
    ]
    frame = pd.DataFrame(qa_records)
    visible_columns = [column for column in preview_columns if column in frame.columns]
    print(frame[visible_columns].to_string(index=False))


def make_selection(args: argparse.Namespace) -> SelectionResult:
    """Load data and make the formal-hot-day selection."""
    input_path = resolve_input_path(args.input)
    hourly, time_column = load_hourly_weather(
        input_path=input_path,
        station=args.station,
        hours=args.hours,
        allow_global_only=args.allow_global_only,
    )
    selected_date, selected_rows, selection_warnings = select_date_rows(
        hourly=hourly,
        hours=args.hours,
        explicit_date=args.date,
    )
    radiation_warnings = validate_selected_radiation(
        selected_rows,
        allow_global_only=args.allow_global_only,
    )
    return SelectionResult(
        input_path=input_path,
        time_column=time_column,
        station=args.station,
        hours=args.hours,
        selected_date=selected_date,
        selection_mode=args.selection_mode,
        hourly_rows=selected_rows,
        warnings=(*selection_warnings, *radiation_warnings),
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Build v12 formal-hot-day single-hour UMEP SOLWEIG met forcing files "
            "for requested station/hours."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Input CSV path. If omitted, tries the registered v11/v09 defaults in order.",
    )
    parser.add_argument("--station", default="S128", help="station_id to use as forcing source.")
    parser.add_argument("--hours", default=parse_hours("13,15"), type=parse_hours, help="Comma-separated SGT hours.")
    parser.add_argument("--date", default=None, help="Optional YYYY-MM-DD local date to force.")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, type=Path, help="Directory for UMEP met files.")
    parser.add_argument(
        "--selection-mode",
        default=SELECTION_MODE,
        choices=[SELECTION_MODE],
        help="Date selection rule used when --date is omitted.",
    )
    parser.add_argument(
        "--allow-global-only",
        action="store_true",
        help="Allow missing direct/diffuse radiation by writing Kdiff=-999 and Kdir=-999 with QA warning.",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", action="store_true", help="Print selected rows and write nothing.")
    mode_group.add_argument("--write", action="store_true", help="Write forcing files and QA outputs.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    result = make_selection(args)
    qa_records = build_qa_records(
        result=result,
        out_dir=args.out_dir,
        allow_global_only=args.allow_global_only,
    )
    preview_selection(qa_records, result.warnings)

    if args.write:
        write_forcing_files(
            selected=result.hourly_rows,
            out_dir=args.out_dir,
            station=result.station,
            allow_global_only=args.allow_global_only,
        )
        write_qa_outputs(qa_records, result.warnings)
        print(f"[OK] wrote {len(qa_records)} forcing files to {args.out_dir}")
        print(f"[OK] wrote QA outputs to {QA_DIR}")
    else:
        print("[DRY-RUN] No files written. Pass --write to create forcing and QA outputs.")


if __name__ == "__main__":
    main()
