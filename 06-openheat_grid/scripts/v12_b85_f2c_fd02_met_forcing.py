"""Recover or generate FD02 SOLWEIG meteorological forcing files for B8.5-F2c.

Inputs:
    configs/v12/systemb_b85_f2c_fd02_met_forcing.yaml
    Existing FD01 v09 met forcing text files used only as schema templates.
    data/calibration/v09_historical_forecast_by_station_hourly.csv
    B8.5-F2b and B8.5-F0 compact readiness artifacts declared in the config.

Outputs:
    docs/v12/OpenHeat_SystemB_B8_5_F2c_fd02_met_forcing_CN.md
    outputs/v12_surrogate/b8_5_f2c_met_forcing/b85_f2c_source_inventory.csv
    outputs/v12_surrogate/b8_5_f2c_met_forcing/b85_f2c_template_schema_inventory.csv
    outputs/v12_surrogate/b8_5_f2c_met_forcing/b85_f2c_fd02_weather_rows.csv
    outputs/v12_surrogate/b8_5_f2c_met_forcing/b85_f2c_generated_met_forcing_manifest.csv
    outputs/v12_surrogate/b8_5_f2c_met_forcing/b85_f2c_met_forcing_validation.csv
    outputs/v12_surrogate/b8_5_f2c_met_forcing/b85_f2c_readiness_projection.csv
    outputs/v12_surrogate/b8_5_f2c_met_forcing/b85_f2c_next_remap_roots.yaml
    outputs/v12_surrogate/b8_5_f2c_met_forcing/B8_5_F2C_STATUS.md
    C:/OpenHeat-local/solweig/met_forcing/b85_f2c/v09_met_forcing_2026_05_08_S128_hHH.txt

Saved metrics:
    Source inventory, template schema and formatting inventory, matched FD02
    S128 station-hour weather rows, generated/recovered local-only met forcing
    manifest with hashes, text read-back validation, and a projected F2b/F2a
    readiness count after FD02 met forcing recovery.

This script does not run QGIS, run SOLWEIG, create/copy/open rasters,
copy/open svfs.zip, create AOI-wide predictions, compute local WBGT, create
hazard_score/risk_score, create System A/B coupling outputs, stage files, or
commit files. Generated met forcing text files are written only to the
configured local path outside the Git worktree.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f2c_fd02_met_forcing.yaml"

YES = "yes"
NO = "no"
PASS = "PASS"
FAIL = "FAIL"
GENERATED_LOCAL_ONLY = "GENERATED_LOCAL_ONLY"
RECOVERED_EXISTING_LOCAL = "RECOVERED_EXISTING_LOCAL"
PARTIAL_MET_FORCING = "PARTIAL_MET_FORCING"
BLOCKED_TEMPLATE_SCHEMA = "BLOCKED_TEMPLATE_SCHEMA"
BLOCKED_WEATHER_SOURCE = "BLOCKED_WEATHER_SOURCE"
FAILED = "FAILED"

SCHEMA_OK = "TEMPLATE_SCHEMA_OK"
SCHEMA_BLOCKED = "BLOCKED_TEMPLATE_SCHEMA"
WEATHER_OK = "WEATHER_SOURCE_OK"
WEATHER_BLOCKED = "BLOCKED_WEATHER_SOURCE"
VALIDATION_PASS = "PASS"
VALIDATION_FAIL = "FAIL"
NOT_WRITTEN = "NOT_WRITTEN"

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
REQUIRED_TEMPLATE_COLUMNS = set(UMEP_COLUMNS)
REQUIRED_WEATHER_COLUMNS = (
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "cloud_cover",
)
OPTIONAL_WEATHER_COLUMNS = (
    "shortwave_3h_mean",
    "precipitation",
    "rain",
)


@dataclass(frozen=True)
class CandidateRoot:
    """Configured source root used for text-file discovery only."""

    root_alias: str
    root_path: Path
    root_kind: str
    notes: str


@dataclass(frozen=True)
class TemplateSchema:
    """Inferred UMEP met forcing schema from an existing FD01 text file."""

    source_alias: str
    source_path: Path
    header: str
    columns: tuple[str, ...]
    data_row_count: int
    line_count: int
    formats: dict[str, str]
    status: str
    notes: str


@dataclass(frozen=True)
class WeatherSelection:
    """Matched weather rows for the target station/date/hours."""

    source_alias: str
    source_path: Path
    rows_by_hour: dict[int, dict[str, Any]]
    status: str
    notes: str


@dataclass(frozen=True)
class F2cResult:
    """Return object for the B8.5-F2c met forcing recovery lane."""

    decision_status: str
    generated_or_recovered_count: int
    template_source: str
    weather_source: str
    projected_ready_run_count: int
    remaining_blockers: str
    files_created: list[Path]


def now_stamp() -> str:
    """Return a local timestamp for reports."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean(value: Any) -> str:
    """Return a compact single-line string."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def path_text(path: Path | str) -> str:
    """Return a stable slash-separated path string."""
    return Path(path).as_posix()


def parse_scalar(value: str) -> Any:
    """Parse the small YAML scalar subset used by this config."""
    stripped = value.strip()
    if stripped == "[]":
        return []
    lowered = stripped.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"yes", "no"}:
        return lowered
    if lowered in {"null", "none", "~"}:
        return None
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        return stripped.strip("\"'")


def read_simple_yaml(path: Path) -> dict[str, Any]:
    """Read the simple nested YAML shape used by OpenHeat configs."""
    lines = [
        line.rstrip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for idx, line in enumerate(lines):
        indent = len(line) - len(line.lstrip(" "))
        text = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if text.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"Unsupported YAML list placement: {line}")
            item_text = text[2:].strip()
            if ":" in item_text:
                key, _, raw_value = item_text.partition(":")
                item: dict[str, Any] = {key.strip(): parse_scalar(raw_value.strip())}
                parent.append(item)
                stack.append((indent, item))
            else:
                parent.append(parse_scalar(item_text))
            continue
        key, _, raw_value = text.partition(":")
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            if not isinstance(parent, dict):
                raise ValueError(f"Unsupported YAML mapping placement: {line}")
            parent[key] = parse_scalar(raw_value)
            continue
        next_container: Any = {}
        for future in lines[idx + 1 :]:
            future_indent = len(future) - len(future.lstrip(" "))
            future_text = future.strip()
            if future_indent <= indent:
                break
            next_container = [] if future_text.startswith("- ") else {}
            break
        if not isinstance(parent, dict):
            raise ValueError(f"Unsupported YAML parent for key: {line}")
        parent[key] = next_container
        stack.append((indent, next_container))
    return root


def read_config(path: Path) -> dict[str, Any]:
    """Load YAML config, preferring PyYAML with a no-dependency fallback."""
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Config did not parse to a mapping: {path}")
        return loaded
    except ImportError:
        return read_simple_yaml(path)


def repo_path(value: str | Path) -> Path:
    """Resolve a path relative to the OpenHeat project subdirectory."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def git_root() -> Path:
    """Return the Git root for the current OpenHeat worktree."""
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        return Path(completed.stdout.strip()).resolve()
    return ROOT.resolve()


def is_relative_to(path: Path, parent: Path) -> bool:
    """Return whether path resolves inside parent."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV into dictionaries."""
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """Write a UTF-8 CSV artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def sha256_file(path: Path) -> str:
    """Return a file SHA-256 hash."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def maybe_float(value: Any) -> float | None:
    """Parse a numeric field or return None."""
    text = clean(value)
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def format_number(value: float | int, style: str) -> str:
    """Format a generated value using the template token style."""
    if style.startswith("float:"):
        decimals = int(style.split(":", 1)[1])
        return f"{float(value):.{decimals}f}"
    return str(int(round(float(value))))


def infer_format(token: str) -> str:
    """Infer integer or fixed-decimal formatting from a template token."""
    if "." not in token:
        return "int"
    return f"float:{len(token.rsplit('.', 1)[1])}"


def target_hours(config: dict[str, Any]) -> list[int]:
    """Return configured target hours."""
    return [int(hour) for hour in config["target_hours_sgt"]]


def date_yyyymmdd(date_value: str) -> str:
    """Convert YYYY-MM-DD to YYYY_MM_DD."""
    return date_value.replace("-", "_")


def template_relative_path(config: dict[str, Any], hour: int) -> Path:
    """Return the configured FD01 template path for an hour."""
    pattern = str(config["template_relative_pattern"])
    text = pattern.format(
        date_yyyymmdd=date_yyyymmdd(str(config["template_source_date"])),
        station_id=str(config["template_station_id"]),
        hour_sgt=hour,
    )
    return Path(text)


def target_filename(config: dict[str, Any], hour: int) -> str:
    """Return the normalized target FD02 met forcing filename."""
    return str(config["target_filename_pattern"]).format(hour_sgt=hour)


def local_output_path(config: dict[str, Any], hour: int) -> Path:
    """Return the local-only generated met forcing path for an hour."""
    return Path(str(config["local_met_output_root"])) / target_filename(config, hour)


def candidate_roots(config: dict[str, Any]) -> list[CandidateRoot]:
    """Return candidate roots in configured template-search order."""
    root_items = config.get("candidate_roots", [])
    by_alias = {
        str(item["root_alias"]): CandidateRoot(
            root_alias=str(item["root_alias"]),
            root_path=Path(str(item["root_path"])),
            root_kind=str(item.get("root_kind", "")),
            notes=str(item.get("notes", "")),
        )
        for item in root_items
    }
    roots: list[CandidateRoot] = []
    for alias in config.get("template_search_roots", []):
        if str(alias) in by_alias:
            roots.append(by_alias[str(alias)])
    return roots


def parse_template_file(path: Path, source_alias: str) -> TemplateSchema:
    """Infer schema and formatting from a UMEP met forcing text template."""
    if not path.exists():
        return TemplateSchema(
            source_alias=source_alias,
            source_path=path,
            header="",
            columns=(),
            data_row_count=0,
            line_count=0,
            formats={},
            status=SCHEMA_BLOCKED,
            notes="template file missing",
        )
    text = path.read_text(encoding="utf-8-sig").splitlines()
    lines = [line.strip() for line in text if line.strip()]
    if not lines or not lines[0].startswith("%"):
        return TemplateSchema(
            source_alias=source_alias,
            source_path=path,
            header=lines[0] if lines else "",
            columns=(),
            data_row_count=0,
            line_count=len(lines),
            formats={},
            status=SCHEMA_BLOCKED,
            notes="template header missing or does not start with %",
        )
    header = lines[0]
    columns = tuple(header.lstrip("%").split())
    data_rows = [line for line in lines[1:] if not line.startswith("%")]
    if not data_rows:
        return TemplateSchema(
            source_alias=source_alias,
            source_path=path,
            header=header,
            columns=columns,
            data_row_count=0,
            line_count=len(lines),
            formats={},
            status=SCHEMA_BLOCKED,
            notes="template has no data rows",
        )
    first_tokens = data_rows[0].split()
    format_ok = len(first_tokens) == len(columns)
    row_counts_ok = all(len(row.split()) == len(columns) for row in data_rows)
    required_ok = REQUIRED_TEMPLATE_COLUMNS.issubset(set(columns))
    duplicate_note = "duplicate_rows=yes" if len(set(data_rows)) == 1 else "duplicate_rows=no"
    status = SCHEMA_OK if format_ok and row_counts_ok and required_ok else SCHEMA_BLOCKED
    notes = []
    if not format_ok:
        notes.append("first data row column count mismatch")
    if not row_counts_ok:
        notes.append("one or more data rows have mismatched column counts")
    if not required_ok:
        missing = sorted(REQUIRED_TEMPLATE_COLUMNS.difference(columns))
        notes.append(f"missing required UMEP columns: {','.join(missing)}")
    notes.append(duplicate_note)
    formats = {
        column: infer_format(token)
        for column, token in zip(columns, first_tokens)
    }
    return TemplateSchema(
        source_alias=source_alias,
        source_path=path,
        header=header,
        columns=columns,
        data_row_count=len(data_rows),
        line_count=len(lines),
        formats=formats,
        status=status,
        notes="; ".join(notes),
    )


def discover_templates(
    config: dict[str, Any],
) -> tuple[TemplateSchema | None, list[dict[str, Any]], list[dict[str, Any]]]:
    """Discover FD01 templates and return a selected schema plus inventory rows."""
    inventory_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    selected: TemplateSchema | None = None
    for root in candidate_roots(config):
        root_exists = root.root_path.exists()
        source_rows.append(
            {
                "source_alias": root.root_alias,
                "source_kind": f"template_root:{root.root_kind}",
                "path_display": path_text(root.root_path),
                "path_exists": YES if root_exists else NO,
                "matched_rows": "",
                "matched_hours": "",
                "usable_for_template": "",
                "usable_for_weather": NO,
                "selected": NO,
                "notes": root.notes,
            }
        )
        found_for_root: list[TemplateSchema] = []
        for hour in target_hours(config):
            template_path = root.root_path / template_relative_path(config, hour)
            schema = parse_template_file(template_path, root.root_alias)
            found_for_root.append(schema)
            inventory_rows.append(
                {
                    "template_source_alias": root.root_alias,
                    "template_path_display": path_text(template_path),
                    "hour_sgt": hour,
                    "file_exists": YES if template_path.exists() else NO,
                    "file_size_bytes": template_path.stat().st_size if template_path.exists() else "",
                    "sha256": sha256_file(template_path) if template_path.exists() else "",
                    "header": schema.header,
                    "column_count": len(schema.columns),
                    "columns": " ".join(schema.columns),
                    "data_row_count": schema.data_row_count,
                    "line_count": schema.line_count,
                    "duplicate_rows": YES if "duplicate_rows=yes" in schema.notes else NO,
                    "required_columns_present": YES
                    if REQUIRED_TEMPLATE_COLUMNS.issubset(set(schema.columns))
                    else NO,
                    "schema_status": schema.status,
                    "notes": schema.notes,
                }
            )
        ok_for_root = [schema for schema in found_for_root if schema.status == SCHEMA_OK]
        if selected is None and len(ok_for_root) == len(target_hours(config)):
            selected = ok_for_root[0]
            for row in source_rows:
                if row["source_alias"] == root.root_alias:
                    row["usable_for_template"] = YES
                    row["selected"] = YES
                    row["matched_hours"] = ",".join(str(hour) for hour in target_hours(config))
        elif ok_for_root:
            for row in source_rows:
                if row["source_alias"] == root.root_alias:
                    row["usable_for_template"] = YES
                    row["matched_hours"] = ",".join(
                        str(schema.source_path.name.rsplit("_h", 1)[-1].split(".")[0])
                        for schema in ok_for_root
                    )
        else:
            for row in source_rows:
                if row["source_alias"] == root.root_alias:
                    row["usable_for_template"] = NO
    return selected, inventory_rows, source_rows


def row_date_hour(row: dict[str, str]) -> tuple[str, int] | None:
    """Extract SGT date and hour without converting away from local offset."""
    if clean(row.get("date_sgt")) and clean(row.get("hour_sgt")):
        hour = maybe_float(row.get("hour_sgt"))
        if hour is not None:
            return clean(row["date_sgt"])[:10], int(hour)
    for column in ("time_sgt", "timestamp_sgt"):
        value = clean(row.get(column))
        if len(value) >= 13 and value[10] in {" ", "T"}:
            hour = maybe_float(value[11:13])
            if hour is not None:
                return value[:10], int(hour)
    return None


def numeric_mean(rows: list[dict[str, str]], column: str) -> float | None:
    """Return the mean numeric value for a column across matched source rows."""
    values = [maybe_float(row.get(column)) for row in rows]
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def collapse_weather_rows(
    rows: list[dict[str, str]],
    station_id: str,
    target_date: str,
    hours: list[int],
) -> dict[int, dict[str, Any]]:
    """Collapse source rows to one station-hour weather record per requested hour."""
    groups: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if clean(row.get("station_id")) != station_id:
            continue
        extracted = row_date_hour(row)
        if extracted is None:
            continue
        date_value, hour = extracted
        if date_value == target_date and hour in hours:
            groups[hour].append(row)

    collapsed: dict[int, dict[str, Any]] = {}
    numeric_columns = list(REQUIRED_WEATHER_COLUMNS) + list(OPTIONAL_WEATHER_COLUMNS)
    for hour in hours:
        hour_rows = groups.get(hour, [])
        if not hour_rows:
            continue
        first = hour_rows[0]
        record: dict[str, Any] = {
            "station_id": station_id,
            "date": target_date,
            "hour_sgt": hour,
            "time_sgt": clean(first.get("time_sgt") or first.get("timestamp_sgt")),
            "n_source_rows": len(hour_rows),
        }
        for column in numeric_columns:
            if column in first:
                record[column] = numeric_mean(hour_rows, column)
        collapsed[hour] = record
    return collapsed


def validate_weather_rows(rows_by_hour: dict[int, dict[str, Any]], hours: list[int]) -> tuple[str, str]:
    """Validate that all requested hours and required weather variables exist."""
    missing_hours = [hour for hour in hours if hour not in rows_by_hour]
    if missing_hours:
        return WEATHER_BLOCKED, f"missing target station-hours: {missing_hours}"
    missing_values: list[str] = []
    for hour in hours:
        row = rows_by_hour[hour]
        for column in REQUIRED_WEATHER_COLUMNS:
            if row.get(column) is None:
                missing_values.append(f"h{hour:02d}:{column}")
    if missing_values:
        return WEATHER_BLOCKED, "missing required weather values: " + ",".join(missing_values)
    return WEATHER_OK, "all target station-hours and required weather fields present"


def discover_weather(
    config: dict[str, Any],
) -> tuple[WeatherSelection | None, list[dict[str, Any]]]:
    """Discover configured weather sources and select the first usable one."""
    source_rows: list[dict[str, Any]] = []
    selected: WeatherSelection | None = None
    hours = target_hours(config)
    station_id = str(config["target_station_id"])
    target_date = str(config["target_date"])
    for item in config.get("weather_sources", []):
        alias = str(item["source_alias"])
        path = repo_path(str(item["path"]))
        exists = path.exists()
        matched_rows = 0
        matched_hours = ""
        status = "missing_source"
        notes = str(item.get("source_kind", ""))
        rows_by_hour: dict[int, dict[str, Any]] = {}
        if exists:
            rows = read_csv_rows(path)
            rows_by_hour = collapse_weather_rows(rows, station_id, target_date, hours)
            matched_rows = sum(int(row["n_source_rows"]) for row in rows_by_hour.values())
            matched_hours = ",".join(str(hour) for hour in sorted(rows_by_hour))
            status, notes = validate_weather_rows(rows_by_hour, hours)
        if selected is None and exists and status == WEATHER_OK:
            selected = WeatherSelection(
                source_alias=alias,
                source_path=path,
                rows_by_hour=rows_by_hour,
                status=status,
                notes=notes,
            )
        source_rows.append(
            {
                "source_alias": alias,
                "source_kind": str(item.get("source_kind", "")),
                "path_display": path_text(path),
                "path_exists": YES if exists else NO,
                "matched_rows": matched_rows if exists else "",
                "matched_hours": matched_hours,
                "usable_for_template": NO,
                "usable_for_weather": YES if status == WEATHER_OK else NO,
                "selected": YES if selected is not None and selected.source_alias == alias else NO,
                "notes": notes,
            }
        )
    return selected, source_rows


def build_umep_record(weather_row: dict[str, Any]) -> dict[str, float | int]:
    """Build one UMEP SOLWEIG met forcing record from a source weather row."""
    target_date = str(weather_row["date"])
    local_time = datetime.strptime(f"{target_date} {int(weather_row['hour_sgt']):02d}:00", "%Y-%m-%d %H:%M")
    rain_value = weather_row.get("precipitation")
    if rain_value is None:
        rain_value = weather_row.get("rain")
    if rain_value is None:
        rain_value = 0.0
    cloud_cover = float(weather_row["cloud_cover"])
    return {
        "iy": local_time.year,
        "id": int(local_time.strftime("%j")),
        "it": int(weather_row["hour_sgt"]),
        "imin": 0,
        "qn": -999,
        "qh": -999,
        "qe": -999,
        "qs": -999,
        "qf": -999,
        "U": round(max(float(weather_row["wind_speed_10m"]), 0.5), 3),
        "RH": round(float(weather_row["relative_humidity_2m"]), 1),
        "Tair": round(float(weather_row["temperature_2m"]), 2),
        "pres": 1010,
        "rain": round(float(rain_value), 3),
        "kdown": round(float(weather_row["shortwave_radiation"]), 1),
        "snow": 0,
        "ldown": -999,
        "fcld": round(cloud_cover / 100.0, 3),
        "wuh": -999,
        "xsmd": -999,
        "lai_hr": -999,
        "Kdiff": round(float(weather_row["diffuse_radiation"]), 1),
        "Kdir": round(float(weather_row["direct_radiation"]), 1),
        "Wd": 270,
    }


def row_to_line(record: dict[str, float | int], schema: TemplateSchema) -> str:
    """Format one UMEP record in the same whitespace style as the template."""
    return " ".join(
        format_number(record[column], schema.formats.get(column, "int"))
        for column in schema.columns
    )


def write_local_met_files(
    config: dict[str, Any],
    schema: TemplateSchema,
    weather: WeatherSelection,
) -> list[dict[str, Any]]:
    """Write local-only two-row UMEP met files and return weather QA rows."""
    if not bool(config.get("write_local_met_files", False)):
        return []
    if bool(config.get("write_into_repo", False)):
        raise ValueError("Refusing to write met forcing files into the Git worktree.")
    output_root = Path(str(config["local_met_output_root"]))
    if is_relative_to(output_root, git_root()):
        raise ValueError(f"Refusing local met output root inside Git worktree: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    weather_rows: list[dict[str, Any]] = []
    for hour in target_hours(config):
        weather_row = weather.rows_by_hour[hour]
        record = build_umep_record(weather_row)
        line = row_to_line(record, schema)
        out_path = local_output_path(config, hour)
        out_path.write_text(f"{schema.header}\n{line}\n{line}\n", encoding="utf-8")
        weather_rows.append(
            {
                "forcing_day_id": config["forcing_day_id"],
                "date": config["target_date"],
                "hour_sgt": hour,
                "station_id": config["target_station_id"],
                "weather_source_alias": weather.source_alias,
                "weather_source_path": path_text(weather.source_path),
                "time_sgt": weather_row.get("time_sgt", ""),
                "n_source_rows": weather_row.get("n_source_rows", ""),
                "temperature_2m": weather_row.get("temperature_2m", ""),
                "relative_humidity_2m": weather_row.get("relative_humidity_2m", ""),
                "wind_speed_10m": weather_row.get("wind_speed_10m", ""),
                "shortwave_radiation": weather_row.get("shortwave_radiation", ""),
                "shortwave_3h_mean": weather_row.get("shortwave_3h_mean", ""),
                "cloud_cover": weather_row.get("cloud_cover", ""),
                "direct_radiation": weather_row.get("direct_radiation", ""),
                "diffuse_radiation": weather_row.get("diffuse_radiation", ""),
                "precipitation": weather_row.get("precipitation", ""),
                "rain_written": record["rain"],
                "generated_iy": record["iy"],
                "generated_day_of_year": record["id"],
                "generated_hour_sgt": record["it"],
                "generated_U": record["U"],
                "generated_RH": record["RH"],
                "generated_Tair": record["Tair"],
                "generated_kdown": record["kdown"],
                "generated_fcld": record["fcld"],
                "generated_Kdiff": record["Kdiff"],
                "generated_Kdir": record["Kdir"],
                "local_output_path_display": path_text(out_path),
                "notes": "Rain/precipitation absent in selected source is written as 0 following the v09 template convention.",
            }
        )
    return weather_rows


def build_weather_rows_without_writing(
    config: dict[str, Any],
    weather: WeatherSelection,
) -> list[dict[str, Any]]:
    """Build FD02 weather-row QA records when generation is blocked."""
    rows: list[dict[str, Any]] = []
    for hour in target_hours(config):
        row = weather.rows_by_hour.get(hour, {})
        rows.append(
            {
                "forcing_day_id": config["forcing_day_id"],
                "date": config["target_date"],
                "hour_sgt": hour,
                "station_id": config["target_station_id"],
                "weather_source_alias": weather.source_alias,
                "weather_source_path": path_text(weather.source_path),
                "time_sgt": row.get("time_sgt", ""),
                "n_source_rows": row.get("n_source_rows", ""),
                "temperature_2m": row.get("temperature_2m", ""),
                "relative_humidity_2m": row.get("relative_humidity_2m", ""),
                "wind_speed_10m": row.get("wind_speed_10m", ""),
                "shortwave_radiation": row.get("shortwave_radiation", ""),
                "shortwave_3h_mean": row.get("shortwave_3h_mean", ""),
                "cloud_cover": row.get("cloud_cover", ""),
                "direct_radiation": row.get("direct_radiation", ""),
                "diffuse_radiation": row.get("diffuse_radiation", ""),
                "precipitation": row.get("precipitation", ""),
                "rain_written": "",
                "generated_iy": "",
                "generated_day_of_year": "",
                "generated_hour_sgt": "",
                "generated_U": "",
                "generated_RH": "",
                "generated_Tair": "",
                "generated_kdown": "",
                "generated_fcld": "",
                "generated_Kdiff": "",
                "generated_Kdir": "",
                "local_output_path_display": path_text(local_output_path(config, hour)),
                "notes": "Weather source discovered but met file generation was blocked.",
            }
        )
    return rows


def validate_met_file(path: Path, schema: TemplateSchema, expected_hour: int, target_date: str) -> dict[str, Any]:
    """Read back one generated/recovered met file and validate text schema."""
    if not path.exists():
        return {
            "hour_sgt": expected_hour,
            "path_display": path_text(path),
            "file_exists": NO,
            "line_count": "",
            "expected_line_count": schema.line_count,
            "header_matches": NO,
            "column_count_matches": NO,
            "data_row_count_matches": NO,
            "duplicate_rows": NO,
            "required_fields_present": NO,
            "date_hour_matches": NO,
            "validation_status": VALIDATION_FAIL,
            "notes": "file missing",
        }
    lines = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    header_matches = bool(lines and lines[0] == schema.header)
    data_rows = [line for line in lines[1:] if not line.startswith("%")]
    column_counts_match = all(len(row.split()) == len(schema.columns) for row in data_rows)
    data_count_match = len(data_rows) == schema.data_row_count
    duplicate_rows = len(set(data_rows)) == 1 if data_rows else False
    required_present = REQUIRED_TEMPLATE_COLUMNS.issubset(set(schema.columns))
    date_hour_matches = False
    notes: list[str] = []
    if data_rows and column_counts_match:
        first = dict(zip(schema.columns, data_rows[0].split()))
        expected_doy = int(datetime.strptime(target_date, "%Y-%m-%d").strftime("%j"))
        date_hour_matches = (
            int(float(first["iy"])) == int(target_date[:4])
            and int(float(first["id"])) == expected_doy
            and int(float(first["it"])) == expected_hour
        )
    checks = [
        header_matches,
        column_counts_match,
        data_count_match,
        duplicate_rows,
        required_present,
        date_hour_matches,
    ]
    if not header_matches:
        notes.append("header mismatch")
    if not column_counts_match:
        notes.append("column count mismatch")
    if not data_count_match:
        notes.append("data row count differs from template")
    if not duplicate_rows:
        notes.append("data rows are not duplicated")
    if not date_hour_matches:
        notes.append("date/hour fields do not match target")
    return {
        "hour_sgt": expected_hour,
        "path_display": path_text(path),
        "file_exists": YES,
        "line_count": len(lines),
        "expected_line_count": schema.line_count,
        "header_matches": YES if header_matches else NO,
        "column_count_matches": YES if column_counts_match else NO,
        "data_row_count_matches": YES if data_count_match else NO,
        "duplicate_rows": YES if duplicate_rows else NO,
        "required_fields_present": YES if required_present else NO,
        "date_hour_matches": YES if date_hour_matches else NO,
        "validation_status": VALIDATION_PASS if all(checks) else VALIDATION_FAIL,
        "notes": "; ".join(notes) if notes else "schema and target date/hour validated",
    }


def validate_met_files(config: dict[str, Any], schema: TemplateSchema | None) -> list[dict[str, Any]]:
    """Validate all target local met forcing files."""
    if schema is None:
        return [
            {
                "hour_sgt": hour,
                "path_display": path_text(local_output_path(config, hour)),
                "file_exists": YES if local_output_path(config, hour).exists() else NO,
                "line_count": "",
                "expected_line_count": "",
                "header_matches": NO,
                "column_count_matches": NO,
                "data_row_count_matches": NO,
                "duplicate_rows": NO,
                "required_fields_present": NO,
                "date_hour_matches": NO,
                "validation_status": NOT_WRITTEN,
                "notes": "template schema unavailable",
            }
            for hour in target_hours(config)
        ]
    return [
        validate_met_file(local_output_path(config, hour), schema, hour, str(config["target_date"]))
        for hour in target_hours(config)
    ]


def build_manifest_rows(
    config: dict[str, Any],
    schema: TemplateSchema | None,
    weather: WeatherSelection | None,
    validation_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build the generated/recovered met forcing manifest."""
    validation_by_hour = {int(row["hour_sgt"]): row for row in validation_rows}
    rows: list[dict[str, Any]] = []
    for hour in target_hours(config):
        path = local_output_path(config, hour)
        exists = path.exists()
        notes = ["local-only; do not stage or commit"]
        if hour == 16:
            notes.append("normalized upstream typo v09_met_foring to v09_met_forcing")
        if schema is None:
            notes.append("template schema unavailable")
        if weather is None:
            notes.append("weather source unavailable")
        rows.append(
            {
                "forcing_day_id": config["forcing_day_id"],
                "date": config["target_date"],
                "hour_sgt": hour,
                "station_id": config["target_station_id"],
                "local_output_path_display": path_text(path),
                "file_exists": YES if exists else NO,
                "file_size_bytes": path.stat().st_size if exists else "",
                "sha256": sha256_file(path) if exists else "",
                "template_source_alias": schema.source_alias if schema else "",
                "weather_source_alias": weather.source_alias if weather else "",
                "schema_status": schema.status if schema else SCHEMA_BLOCKED,
                "validation_status": validation_by_hour.get(hour, {}).get("validation_status", NOT_WRITTEN),
                "commit_safe": NO,
                "notes": "; ".join(notes),
            }
        )
    return rows


def source_inventory_existing_fd02_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Inventory existing normalized and typo FD02 met files under candidate roots."""
    rows: list[dict[str, Any]] = []
    for root in candidate_roots(config):
        matched: list[str] = []
        for hour in target_hours(config):
            normalized_rel = Path("data/solweig") / target_filename(config, hour)
            normalized = root.root_path / normalized_rel
            if normalized.exists():
                matched.append(f"h{hour:02d}:normalized")
            if hour == 16:
                typo = root.root_path / str(config["upstream_typo_h16_relative_path"])
                if typo.exists():
                    matched.append("h16:typo")
        rows.append(
            {
                "source_alias": f"{root.root_alias}_fd02_existing_met",
                "source_kind": "existing_fd02_met_forcing_discovery",
                "path_display": path_text(root.root_path),
                "path_exists": YES if root.root_path.exists() else NO,
                "matched_rows": len(matched),
                "matched_hours": ",".join(matched),
                "usable_for_template": NO,
                "usable_for_weather": NO,
                "selected": NO,
                "notes": "Exact normalized FD02 paths plus h16 typo path checked; files are not copied.",
            }
        )
    local_root = Path(str(config["local_met_output_root"]))
    local_matches = [
        f"h{hour:02d}"
        for hour in target_hours(config)
        if local_output_path(config, hour).exists()
    ]
    rows.append(
        {
            "source_alias": "b85_f2c_local_met_output_root",
            "source_kind": "local_generated_met_forcing_root",
            "path_display": path_text(local_root),
            "path_exists": YES if local_root.exists() else NO,
            "matched_rows": len(local_matches),
            "matched_hours": ",".join(local_matches),
            "usable_for_template": NO,
            "usable_for_weather": NO,
            "selected": NO,
            "notes": "Local-only generated/recovered target root; generated text files are not commit-safe.",
        }
    )
    return rows


def run_matrix_counts(config: dict[str, Any], valid_hours: set[int]) -> tuple[int, int, int]:
    """Return total runs, FD02 runs, and valid FD02 runs from the F0 matrix."""
    matrix_path = repo_path(str(config["inputs"]["f0_run_matrix"]))
    if not matrix_path.exists():
        return 480, 240, len(valid_hours) * 48
    rows = read_csv_rows(matrix_path)
    total = len(rows)
    fd02_rows = [
        row
        for row in rows
        if clean(row.get("forcing_day_id")) == str(config["forcing_day_id"])
    ]
    valid_fd02 = [
        row
        for row in fd02_rows
        if maybe_float(row.get("hour_sgt")) is not None
        and int(float(clean(row.get("hour_sgt")))) in valid_hours
    ]
    return total, len(fd02_rows), len(valid_fd02)


def previous_ready_count(config: dict[str, Any]) -> int:
    """Read the F2b readiness count if available, otherwise use the known FD01 half."""
    status_path = repo_path(str(config["inputs"]["f2b_status"]))
    if not status_path.exists():
        return 240
    text = status_path.read_text(encoding="utf-8", errors="replace")
    marker = "F2b ready runs if output root created and QGIS check passes:"
    for line in text.splitlines():
        if marker in line:
            digits = "".join(ch if ch.isdigit() or ch == "/" else " " for ch in line)
            first = digits.strip().split()[0] if digits.strip().split() else ""
            if "/" in first:
                return int(first.split("/", 1)[0])
    return 240


def build_readiness_projection(
    config: dict[str, Any],
    validation_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, str]:
    """Build a one-row readiness projection after local met generation."""
    valid_hours = {
        int(row["hour_sgt"])
        for row in validation_rows
        if row.get("validation_status") == VALIDATION_PASS
    }
    total_runs, fd02_runs, valid_fd02_runs = run_matrix_counts(config, valid_hours)
    previous_ready = previous_ready_count(config)
    projected_after = min(total_runs, previous_ready + valid_fd02_runs)
    missing_met_hours = [hour for hour in target_hours(config) if hour not in valid_hours]
    blockers = ["local_output_root_needs_create", "qgis_algorithm_manual_check"]
    if missing_met_hours:
        blockers.append("missing_or_invalid_fd02_met_forcing_hours:" + ",".join(f"h{hour:02d}" for hour in missing_met_hours))
    rows = [
        {
            "forcing_day_id": config["forcing_day_id"],
            "total_runs": total_runs,
            "fd02_run_rows": fd02_runs,
            "validated_met_hours": ",".join(f"h{hour:02d}" for hour in sorted(valid_hours)),
            "validated_met_file_count": len(valid_hours),
            "projected_ready_runs_if_output_root_created_and_qgis_check_passes": previous_ready,
            "projected_ready_runs_after_fd02_met_generation": projected_after,
            "projected_file_assets_ready_after_fd02_met_generation": projected_after,
            "remaining_blockers": "; ".join(blockers),
            "notes": "Projection only; QGIS/SOLWEIG not run and local output root/manual QGIS checks remain outside this lane.",
        }
    ]
    return rows, projected_after, "; ".join(blockers)


def write_next_remap_roots(config: dict[str, Any], manifest_rows: list[dict[str, Any]], path: Path) -> None:
    """Write a small YAML handoff for the next F2b/F2a remap pass."""
    lines = [
        "b85_f2c_next_remap_roots_version: systemb_b85_f2c_next_remap_roots_v0_1",
        "lane: B8.5-F2c",
        "qgis_executed: no",
        "solweig_executed: no",
        "generated_met_files_commit_safe: no",
        "root_aliases:",
        "  - root_alias: b85_f2c_local_met_forcing",
        f"    root_path: {path_text(Path(str(config['local_met_output_root'])))}",
        "    root_kind: local_generated_met_forcing_root",
        "    commit_safe_to_reference: yes",
        "    notes: Local-only FD02 met forcing text root. Do not stage generated txt files.",
        "target_met_forcing_files:",
    ]
    for row in manifest_rows:
        lines.extend(
            [
                f"  - hour_sgt: {row['hour_sgt']}",
                f"    station_id: {row['station_id']}",
                f"    date: {row['date']}",
                f"    local_output_path: {row['local_output_path_display']}",
                f"    sha256: {row['sha256']}",
                "    commit_safe: no",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def table_lines(rows: list[dict[str, Any]], columns: list[str]) -> list[str]:
    """Return simple Markdown table lines."""
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(clean(row.get(column, "")) for column in columns) + " |")
    return lines


def write_status(
    config: dict[str, Any],
    result_status: str,
    manifest_rows: list[dict[str, Any]],
    readiness_rows: list[dict[str, Any]],
    files_created: list[Path],
    path: Path,
) -> None:
    """Write the B8.5-F2c English status file."""
    generated_count = sum(1 for row in manifest_rows if row.get("validation_status") == VALIDATION_PASS)
    readiness = readiness_rows[0] if readiness_rows else {}
    lines = [
        "# B8.5-F2c Status",
        "",
        f"Generated: {now_stamp()}",
        "",
        "## Status",
        "",
        f"`{result_status}`",
        "",
        "## Scope",
        "",
        "FD02 SOLWEIG meteorological forcing recovery/generation only. QGIS/SOLWEIG was not run. No rasters were created, copied, or opened. `svfs.zip` was not copied or opened. Generated met forcing files are local-only and not commit-safe. This is not B9, not local WBGT, not risk, and not System A/B coupling.",
        "",
        "## Key Results",
        "",
        f"- Generated or recovered validated met files: `{generated_count}/5`",
        f"- Template source: `{manifest_rows[0].get('template_source_alias', '') if manifest_rows else ''}`",
        f"- Weather source: `{manifest_rows[0].get('weather_source_alias', '') if manifest_rows else ''}`",
        f"- Projected ready runs after FD02 met generation: `{readiness.get('projected_ready_runs_after_fd02_met_generation', '')}/{readiness.get('total_runs', '')}`",
        f"- Remaining blockers: `{readiness.get('remaining_blockers', '')}`",
        "- H16 upstream typo handling: `v09_met_foring_..._h16.txt` normalized to `v09_met_forcing_..._h16.txt`.",
        "- Official WBGT target values were not used to generate forcing fields; the selected template does not include WBGT as an input column.",
        "",
        "## Manifest",
        "",
        *table_lines(
            manifest_rows,
            [
                "hour_sgt",
                "file_exists",
                "file_size_bytes",
                "schema_status",
                "validation_status",
                "commit_safe",
            ],
        ),
        "",
        "## Files Created / Modified",
        "",
        *[f"- `{path_text(path)}`" for path in files_created],
        "",
        "## Caveats",
        "",
        "Meteorological correctness is not claimed beyond reproducing the selected source station-hour rows into the inferred UMEP text schema and validating the generated files by read-back. The next step is to rerun F2b/F2a readiness with the local met root and the local SOLWEIG output root, then perform the QGIS manual check outside this lane.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_cn_doc(
    config: dict[str, Any],
    result_status: str,
    manifest_rows: list[dict[str, Any]],
    readiness_rows: list[dict[str, Any]],
    path: Path,
) -> None:
    """Write the UTF-8 Chinese handoff note."""
    generated_count = sum(1 for row in manifest_rows if row.get("validation_status") == VALIDATION_PASS)
    readiness = readiness_rows[0] if readiness_rows else {}
    lines = [
        "# OpenHeat System B B8.5-F2c FD02 met forcing 说明",
        "",
        f"生成时间：{now_stamp()}",
        "",
        "## 结论",
        "",
        f"本轮状态为 `{result_status}`。目标是为 `FD02_humid_hot_cloudy_or_diffuse_20260508` 生成或恢复 S128 在 2026-05-08 的 10、12、13、15、16 点 SOLWEIG met forcing 文本文件。",
        "",
        f"- 已通过本地文本校验的 met forcing 文件：`{generated_count}/5`。",
        f"- 模板来源：`{manifest_rows[0].get('template_source_alias', '') if manifest_rows else ''}`，使用 FD01 的 v09 单小时 met forcing 文件推断列顺序、表头和格式。",
        f"- 天气来源：`{manifest_rows[0].get('weather_source_alias', '') if manifest_rows else ''}`，按 `station_id=S128` 和 SGT 日期/小时匹配。",
        f"- FD02 生成后的 projected ready runs：`{readiness.get('projected_ready_runs_after_fd02_met_generation', '')}/{readiness.get('total_runs', '')}`。",
        f"- 剩余 blocker：`{readiness.get('remaining_blockers', '')}`。",
        "",
        "## 安全边界",
        "",
        "- 本轮没有运行 QGIS。",
        "- 本轮没有运行 SOLWEIG。",
        "- 本轮没有创建、复制或打开 raster。",
        "- 本轮没有复制或打开 `svfs.zip`。",
        "- 生成的 met forcing 文件只在 `C:/OpenHeat-local/solweig/met_forcing/b85_f2c`，属于 local-only 文件，不能提交到 Git。",
        "- 本轮不是 B9，不生成 AOI-wide prediction。",
        "- 本轮不生成 local WBGT、`hazard_score`、`risk_score`，也不生成 System A/B coupling 输出。",
        "",
        "## 文件命名修正",
        "",
        "上游记录里可能出现 `v09_met_foring_2026_05_08_S128_h16.txt` 的拼写错误。本轮统一规范为 `v09_met_forcing_2026_05_08_S128_h16.txt`，并在 manifest notes 中记录该修正。",
        "",
        "## 方法说明",
        "",
        "脚本先从既有 FD01 v09 met forcing 文件读取 UMEP 表头、列顺序、数据行数量和格式。只有模板 schema 可用、且 FD02/S128/目标小时天气行完整时，才写出本地 met forcing 文件。每个单小时文件保留 FD01 模板的两行相同数据行约定，用于避免旧版 SOLWEIG 对单行 metdata 的维度问题。",
        "",
        "天气变量来自站点小时天气源，不使用 official WBGT target 来生成 forcing 字段；当前模板也不包含 WBGT 输入列。因此这里不能被解释为局地 WBGT 校准，也不能被解释为风险模型。",
        "",
        "## 下一步",
        "",
        "下一步是用本轮 `b85_f2c_next_remap_roots.yaml` 中的 local met root 重新跑 F2b/F2a readiness，同时准备本地 SOLWEIG output root，并在人工环境中做 QGIS/UMEP algorithm manual check。只有这些检查通过后，才进入后续人工 QGIS/SOLWEIG 执行。",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def enforce_scope(config: dict[str, Any]) -> None:
    """Fail fast if config asks this lane to exceed F2c boundaries."""
    if bool(config.get("execute_qgis_or_solweig", False)):
        raise ValueError("Refusing to run QGIS or SOLWEIG in B8.5-F2c.")
    if bool(config.get("open_or_copy_rasters", False)):
        raise ValueError("Refusing to open or copy rasters in B8.5-F2c.")
    if bool(config.get("write_into_repo", False)):
        raise ValueError("Refusing to write generated met forcing files into the repo.")


def output_paths(config: dict[str, Any]) -> dict[str, Path]:
    """Return configured output paths."""
    return {key: repo_path(value) for key, value in config["outputs"].items() if key != "out_dir"}


def run(config_path: Path = DEFAULT_CONFIG) -> F2cResult:
    """Run the F2c met forcing recovery/generation workflow."""
    config = read_config(config_path)
    enforce_scope(config)
    paths = output_paths(config)

    selected_schema, template_rows, template_source_rows = discover_templates(config)
    weather, weather_source_rows = discover_weather(config)
    source_rows = (
        template_source_rows
        + source_inventory_existing_fd02_rows(config)
        + weather_source_rows
    )

    if selected_schema is None:
        decision_status = BLOCKED_TEMPLATE_SCHEMA
        weather_rows = (
            build_weather_rows_without_writing(config, weather)
            if weather is not None
            else []
        )
    elif weather is None:
        decision_status = BLOCKED_WEATHER_SOURCE
        weather_rows = []
    else:
        weather_rows = write_local_met_files(config, selected_schema, weather)
        decision_status = GENERATED_LOCAL_ONLY

    validation_rows = validate_met_files(config, selected_schema)
    if decision_status == GENERATED_LOCAL_ONLY:
        valid_count = sum(1 for row in validation_rows if row.get("validation_status") == VALIDATION_PASS)
        if valid_count == 0:
            decision_status = FAILED
        elif valid_count < len(target_hours(config)):
            decision_status = PARTIAL_MET_FORCING
    elif decision_status in {BLOCKED_TEMPLATE_SCHEMA, BLOCKED_WEATHER_SOURCE}:
        valid_count = sum(1 for row in validation_rows if row.get("validation_status") == VALIDATION_PASS)
        if 0 < valid_count < len(target_hours(config)):
            decision_status = PARTIAL_MET_FORCING
        elif valid_count == len(target_hours(config)):
            decision_status = RECOVERED_EXISTING_LOCAL

    manifest_rows = build_manifest_rows(config, selected_schema, weather, validation_rows)
    readiness_rows, projected_ready, blockers = build_readiness_projection(config, validation_rows)

    write_csv_rows(
        paths["source_inventory"],
        source_rows,
        [
            "source_alias",
            "source_kind",
            "path_display",
            "path_exists",
            "matched_rows",
            "matched_hours",
            "usable_for_template",
            "usable_for_weather",
            "selected",
            "notes",
        ],
    )
    write_csv_rows(
        paths["template_schema_inventory"],
        template_rows,
        [
            "template_source_alias",
            "template_path_display",
            "hour_sgt",
            "file_exists",
            "file_size_bytes",
            "sha256",
            "header",
            "column_count",
            "columns",
            "data_row_count",
            "line_count",
            "duplicate_rows",
            "required_columns_present",
            "schema_status",
            "notes",
        ],
    )
    weather_fieldnames = [
        "forcing_day_id",
        "date",
        "hour_sgt",
        "station_id",
        "weather_source_alias",
        "weather_source_path",
        "time_sgt",
        "n_source_rows",
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "shortwave_radiation",
        "shortwave_3h_mean",
        "cloud_cover",
        "direct_radiation",
        "diffuse_radiation",
        "precipitation",
        "rain_written",
        "generated_iy",
        "generated_day_of_year",
        "generated_hour_sgt",
        "generated_U",
        "generated_RH",
        "generated_Tair",
        "generated_kdown",
        "generated_fcld",
        "generated_Kdiff",
        "generated_Kdir",
        "local_output_path_display",
        "notes",
    ]
    write_csv_rows(paths["fd02_weather_rows"], weather_rows, weather_fieldnames)
    write_csv_rows(
        paths["generated_met_forcing_manifest"],
        manifest_rows,
        [
            "forcing_day_id",
            "date",
            "hour_sgt",
            "station_id",
            "local_output_path_display",
            "file_exists",
            "file_size_bytes",
            "sha256",
            "template_source_alias",
            "weather_source_alias",
            "schema_status",
            "validation_status",
            "commit_safe",
            "notes",
        ],
    )
    write_csv_rows(
        paths["met_forcing_validation"],
        validation_rows,
        [
            "hour_sgt",
            "path_display",
            "file_exists",
            "line_count",
            "expected_line_count",
            "header_matches",
            "column_count_matches",
            "data_row_count_matches",
            "duplicate_rows",
            "required_fields_present",
            "date_hour_matches",
            "validation_status",
            "notes",
        ],
    )
    write_csv_rows(
        paths["readiness_projection"],
        readiness_rows,
        [
            "forcing_day_id",
            "total_runs",
            "fd02_run_rows",
            "validated_met_hours",
            "validated_met_file_count",
            "projected_ready_runs_if_output_root_created_and_qgis_check_passes",
            "projected_ready_runs_after_fd02_met_generation",
            "projected_file_assets_ready_after_fd02_met_generation",
            "remaining_blockers",
            "notes",
        ],
    )
    write_next_remap_roots(config, manifest_rows, paths["next_remap_roots"])

    files_created = [
        paths["source_inventory"],
        paths["template_schema_inventory"],
        paths["fd02_weather_rows"],
        paths["generated_met_forcing_manifest"],
        paths["met_forcing_validation"],
        paths["readiness_projection"],
        paths["next_remap_roots"],
        paths["status"],
        paths["canonical_note_cn"],
    ]
    write_status(config, decision_status, manifest_rows, readiness_rows, files_created, paths["status"])
    write_cn_doc(config, decision_status, manifest_rows, readiness_rows, paths["canonical_note_cn"])

    generated_or_recovered = sum(1 for row in manifest_rows if row.get("validation_status") == VALIDATION_PASS)
    template_source = selected_schema.source_alias if selected_schema else ""
    weather_source = weather.source_alias if weather else ""
    return F2cResult(
        decision_status=decision_status,
        generated_or_recovered_count=generated_or_recovered,
        template_source=template_source,
        weather_source=weather_source,
        projected_ready_run_count=projected_ready,
        remaining_blockers=blockers,
        files_created=files_created,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Recover/generate FD02 SOLWEIG met forcing text files locally only. "
            "Does not run QGIS/SOLWEIG or touch raster/SVF assets."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="F2c YAML config path.")
    return parser


def main() -> int:
    """Run from the command line."""
    args = build_parser().parse_args()
    result = run(repo_path(args.config))
    print(f"Decision status: {result.decision_status}")
    print(f"Generated or recovered met forcing files: {result.generated_or_recovered_count}/5")
    print(f"Template source: {result.template_source or 'none'}")
    print(f"Weather source: {result.weather_source or 'none'}")
    print(f"Projected ready runs after FD02 met generation: {result.projected_ready_run_count}/480")
    print(f"Remaining blockers: {result.remaining_blockers}")
    print("QGIS/SOLWEIG executed: no")
    print("Files created:")
    for path in result.files_created:
        print(f"- {path_text(path)}")
    return 0 if result.decision_status != FAILED else 1


if __name__ == "__main__":
    raise SystemExit(main())
