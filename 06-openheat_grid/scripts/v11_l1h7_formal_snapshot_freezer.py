#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the System A A-L1H.7 formal snapshot freezer package.

Inputs:
    - configs/v11/systema_l1h7_formal_snapshot_freezer.yaml
    - A-L1H.5 output schema CSV.
    - A-L1H.6 expected input schema CSV and status Markdown.
    - Compact CSV, CSV.GZ, and Parquet candidate tables under configured
      formal/prospective search roots.

Outputs:
    - Candidate/input inventories.
    - Safe column-mapping candidates.
    - Required-schema, forbidden-column, freeze-readiness, manifest-schema,
      frozen-manifest, and validation CSVs.
    - Dry-run/write-snapshot command templates.
    - English report, Chinese documentation note, and lane status.

Saved metrics:
    - Candidate row counts, prospective row counts, station counts, ge31/ge33
      support, model/version metadata, optional P_ge31 metadata, source
      checksum, schema status, forbidden-column status, and freeze readiness.

This lane does not train models, change A-L1H.5 contract decisions, change
A-L1H.6 promotion gates, modify archive collectors, read raw archives, create
station-adjusted WBGT, create local 100 m WBGT, create risk/hazard scores,
create System A/B coupling outputs, or fabricate snapshot rows.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import math
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - used only in lean runtimes.
    yaml = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]

READY_STATUS = "A_L1H7_READY_TO_FREEZE"
WAITING_STATUS = "A_L1H7_WAITING_FOR_FORMAL_INPUT"
BLOCKED_SCHEMA_STATUS = "A_L1H7_BLOCKED_SCHEMA"
BLOCKED_FORBIDDEN_STATUS = "A_L1H7_BLOCKED_FORBIDDEN_COLUMNS"
SNAPSHOT_FROZEN_PASS_STATUS = "A_L1H7_SNAPSHOT_FROZEN_PASS"
FAILED_STATUS = "FAILED"

DEFAULT_REQUIRED_COLUMNS = [
    "timestamp_sgt",
    "timestamp_utc",
    "station_id",
    "official_wbgt_c",
    "wbgt_a_c",
    "wbgt_a_model_id",
    "wbgt_a_version",
    "is_retrospective_or_prospective",
    "quality_flag",
]

DEFAULT_OPTIONAL_COLUMNS = [
    "p_ge31_optional",
    "p_ge31_model_id_optional",
    "p_ge31_threshold_policy_optional",
    "p_ge33_optional",
    "expected_exceedance_ge31_optional",
    "prediction_interval_low_optional",
    "prediction_interval_high_optional",
    "lead_time_hours_optional",
]

DEFAULT_FORBIDDEN_COLUMNS = [
    "cell_id",
    "local_wbgt_c",
    "delta_wbgt_cell",
    "station_adjusted_wbgt_c",
    "risk_score",
    "hazard_score",
]

SAFE_ALIAS_CANDIDATES = {
    "timestamp_sgt": ["timestamp", "datetime_sgt", "valid_time_sgt"],
    "timestamp_utc": ["timestamp_utc", "valid_time_utc"],
    "station_id": ["station", "station_code"],
    "official_wbgt_c": ["official_wbgt", "wbgt_obs_c"],
    "wbgt_a_c": ["model_score", "wbgt_a", "pred_wbgt_a_c"],
}


@dataclass(frozen=True)
class TablePreview:
    """In-memory preview of a compact candidate table."""

    path: Path
    file_type: str
    bytes: int
    rows: list[dict[str, Any]]
    columns: list[str]
    read_status: str
    error: str = ""


@dataclass(frozen=True)
class MappingDecision:
    """One target-column mapping decision for one candidate table."""

    target_column: str
    required_or_optional: str
    source_column: str
    mapping_status: str
    reason: str


@dataclass
class CandidateAssessment:
    """Schema, safety, and readiness assessment for one compact table."""

    preview: TablePreview
    mappings: list[MappingDecision]
    required_columns: list[str]
    optional_columns: list[str]
    forbidden_columns: list[str]
    likely_schema_role: str
    detection_status: str
    readiness_status: str
    readiness_reason: str
    missing_required_columns: list[str]
    ambiguous_required_columns: list[str]
    present_forbidden_columns: list[str]
    mapped_required_count: int
    optional_columns_present: list[str]
    n_rows: int
    n_prospective_rows: int
    n_stations: int
    n_ge31: int
    n_ge33: int
    wbgt_a_model_id: str
    wbgt_a_version: str
    p_ge31_model_id: str
    source_sha256: str
    check_rows: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class FreezerResult:
    """Headline result returned by the A-L1H.7 freezer."""

    status: str
    candidate_tables_scanned: int
    best_candidate_path: str
    freeze_mode: str
    n_rows: str
    n_prospective_rows: str
    n_ge31: str
    n_ge33: str
    schema_status: str
    forbidden_column_status: str
    downstream_l1h6_rerun_command: str
    output_paths: list[Path]


def rel(path: Path) -> str:
    """Return a project-relative POSIX path when possible."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(raw_path: str | Path) -> Path:
    """Resolve an absolute or project-relative path."""
    path = Path(raw_path)
    return path if path.is_absolute() else ROOT / path


def parse_scalar(value: str) -> Any:
    """Parse the scalar subset used by explicit lane YAML configs."""
    value = value.strip()
    if value in {"", "null", "Null", "NULL"}:
        return None
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the narrow YAML subset used by this lane's explicit config."""
    raw_lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        raw_lines.append((indent, raw.strip()))

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(raw_lines):
            return {}, index
        if raw_lines[index][1].startswith("- "):
            values: list[Any] = []
            while index < len(raw_lines):
                line_indent, stripped = raw_lines[index]
                if line_indent != indent or not stripped.startswith("- "):
                    break
                item = stripped[2:].strip()
                index += 1
                if not item:
                    if index < len(raw_lines):
                        nested, index = parse_block(index, raw_lines[index][0])
                        values.append(nested)
                    continue
                key, separator, value = item.partition(":")
                if separator:
                    item_dict: dict[str, Any] = {}
                    if value.strip():
                        item_dict[key.strip()] = parse_scalar(value)
                    elif index < len(raw_lines) and raw_lines[index][0] > line_indent:
                        nested, index = parse_block(index, raw_lines[index][0])
                        item_dict[key.strip()] = nested
                    else:
                        item_dict[key.strip()] = {}
                    values.append(item_dict)
                else:
                    values.append(parse_scalar(item))
            return values, index

        mapping: dict[str, Any] = {}
        while index < len(raw_lines):
            line_indent, stripped = raw_lines[index]
            if line_indent != indent or stripped.startswith("- "):
                break
            key, separator, value = stripped.partition(":")
            if not separator:
                raise ValueError(f"Unexpected YAML line: {stripped}")
            index += 1
            if value.strip():
                mapping[key.strip()] = parse_scalar(value)
            elif index < len(raw_lines) and raw_lines[index][0] > line_indent:
                nested, index = parse_block(index, raw_lines[index][0])
                mapping[key.strip()] = nested
            else:
                mapping[key.strip()] = {}
        return mapping, index

    parsed, _ = parse_block(0, 0)
    if not isinstance(parsed, dict):
        raise ValueError("Config root must be a mapping.")
    return parsed


def load_config(path: Path) -> dict[str, Any]:
    """Load the explicit A-L1H.7 YAML config."""
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(text)
    else:
        loaded = parse_simple_yaml(text)
    if not isinstance(loaded, dict):
        raise ValueError("Config root must be a mapping.")
    return loaded


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a compact UTF-8 CSV as dictionaries."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> Path:
    """Write a UTF-8 CSV with stable column order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
    return path


def write_text(path: Path, text: str) -> Path:
    """Write UTF-8 text with LF newlines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return path


def markdown_cell(value: Any) -> str:
    """Escape a compact Markdown table cell."""
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ")


def markdown_table(rows: list[dict[str, Any]], columns: list[str], limit: int | None = None) -> str:
    """Render a compact Markdown table."""
    display_rows = rows if limit is None else rows[:limit]
    if not display_rows:
        return "_No rows available._"
    widths = [len(column) for column in columns]
    body: list[list[str]] = []
    for row in display_rows:
        values = [markdown_cell(row.get(column, "")) for column in columns]
        body.append(values)
        for index, value in enumerate(values):
            widths[index] = max(widths[index], len(value))

    def render(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[index]) for index, value in enumerate(values)) + " |"

    separator = "| " + " | ".join("-" * width for width in widths) + " |"
    return "\n".join([render(columns), separator, *(render(row) for row in body)])


def git_branch() -> str:
    """Return the active git branch."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def file_type_for(path: Path) -> str:
    """Return a compact table file type label."""
    suffixes = [suffix.lower() for suffix in path.suffixes]
    if suffixes[-2:] == [".csv", ".gz"]:
        return ".csv.gz"
    return path.suffix.lower()


def is_allowed_compact(path: Path, allowed_extensions: Iterable[str]) -> bool:
    """Return whether a path has an allowed compact table extension."""
    file_type = file_type_for(path)
    allowed = {str(item).lower() for item in allowed_extensions}
    return file_type in allowed


def path_text(path: Path) -> str:
    """Return normalized lowercase project-relative path text."""
    return rel(path).replace("\\", "/").lower()


def should_skip_path(path: Path, config: dict[str, Any]) -> bool:
    """Skip raw, live, patch, raster, System B, and SOLWEIG paths."""
    text = path_text(path)
    patterns = [str(pattern).replace("\\", "/").lower() for pattern in config.get("skip_path_patterns", [])]
    return any(pattern in text for pattern in patterns)


def discover_candidate_tables(config: dict[str, Any]) -> list[Path]:
    """Discover compact candidate tables under configured roots only."""
    roots = [resolve_path(raw) for raw in config.get("candidate_search_roots", [])]
    allowed_extensions = config.get("allowed_compact_extensions", [".csv", ".csv.gz", ".parquet"])
    seen: set[Path] = set()
    tables: list[Path] = []
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if should_skip_path(path, config):
                continue
            if not is_allowed_compact(path, allowed_extensions):
                continue
            tables.append(path)
    return sorted(tables, key=lambda item: rel(item))


def read_table_preview(path: Path, config: dict[str, Any]) -> TablePreview:
    """Read schema and rows from a compact table without touching raw archives."""
    file_type = file_type_for(path)
    byte_count = path.stat().st_size
    large_file_guard = int(config.get("large_file_guard_bytes", 50_000_000))
    if byte_count > large_file_guard:
        return TablePreview(
            path=path,
            file_type=file_type,
            bytes=byte_count,
            rows=[],
            columns=[],
            read_status="SKIPPED_TOO_LARGE",
            error=f"bytes>{large_file_guard}",
        )
    try:
        if file_type == ".parquet":
            try:
                import pandas as pd  # type: ignore[import-not-found]
            except ModuleNotFoundError:
                return TablePreview(path, file_type, byte_count, [], [], "READ_FAILED", "pandas_missing_for_parquet")
            frame = pd.read_parquet(path)
            return TablePreview(
                path=path,
                file_type=file_type,
                bytes=byte_count,
                rows=frame.to_dict(orient="records"),
                columns=[str(column) for column in frame.columns],
                read_status="READ_OK",
            )
        if file_type == ".csv.gz":
            with gzip.open(path, "rt", encoding="utf-8-sig", errors="replace", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = [dict(row) for row in reader]
                return TablePreview(path, file_type, byte_count, rows, [str(column) for column in (reader.fieldnames or [])], "READ_OK")
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [dict(row) for row in reader]
            return TablePreview(path, file_type, byte_count, rows, [str(column) for column in (reader.fieldnames or [])], "READ_OK")
    except Exception as exc:  # pragma: no cover - defensive for future snapshots.
        return TablePreview(path, file_type, byte_count, [], [], "READ_FAILED", str(exc))


def load_schema_contract(config: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """Load required, optional, and forbidden columns from A-L1H.6/A-L1H.5."""
    l1h6_rows = read_csv_rows(resolve_path(config["l1h6_required_schema_path"]))
    required = [
        row["column_name"]
        for row in l1h6_rows
        if row.get("required_or_optional", "").strip().lower() == "required" and row.get("column_name")
    ]
    optional = [
        row["column_name"]
        for row in l1h6_rows
        if row.get("required_or_optional", "").strip().lower() == "optional" and row.get("column_name")
    ]
    l1h5_rows = read_csv_rows(resolve_path(config["l1h5_output_schema_path"]))
    forbidden = [
        row["column_name"]
        for row in l1h5_rows
        if row.get("column_group", "").strip().lower() == "forbidden" and row.get("column_name")
    ]
    return required or DEFAULT_REQUIRED_COLUMNS, optional or DEFAULT_OPTIONAL_COLUMNS, forbidden or DEFAULT_FORBIDDEN_COLUMNS


def lower_column_map(columns: list[str]) -> dict[str, list[str]]:
    """Map lowercase column names to original names."""
    mapping: dict[str, list[str]] = {}
    for column in columns:
        mapping.setdefault(column.strip().lower(), []).append(column)
    return mapping


def sample_values(preview: TablePreview, column: str, limit: int = 25) -> list[str]:
    """Return non-empty sample values for a column."""
    values: list[str] = []
    for row in preview.rows:
        value = str(row.get(column, "")).strip()
        if value:
            values.append(value)
        if len(values) >= limit:
            break
    return values


def has_sgt_timezone_semantics(preview: TablePreview, source_column: str) -> bool:
    """Return whether a timestamp alias clearly carries SGT semantics."""
    lowered = source_column.lower()
    if lowered in {"datetime_sgt", "valid_time_sgt"}:
        return True
    timezone_columns = {"timezone", "tz", "time_zone"}
    for column in preview.columns:
        if column.strip().lower() in timezone_columns:
            values = [value.lower() for value in sample_values(preview, column)]
            if values and all(value in {"sgt", "asia/singapore", "+08", "+08:00", "utc+8", "utc+08:00"} for value in values):
                return True
    values = sample_values(preview, source_column)
    clear_tokens = ("+08:00", "+0800", "sgt", "asia/singapore")
    return bool(values) and all(any(token in value.lower() for token in clear_tokens) for value in values)


def has_contract_source_context(preview: TablePreview) -> bool:
    """Return whether a WBGT_A alias has clear model/version context."""
    lower_map = lower_column_map(preview.columns)
    return "wbgt_a_model_id" in lower_map and "wbgt_a_version" in lower_map


def decide_mapping_for_target(
    target: str,
    required_or_optional: str,
    preview: TablePreview,
) -> MappingDecision:
    """Choose an exact or safe alias mapping for one target column."""
    lower_map = lower_column_map(preview.columns)
    target_lower = target.lower()
    if target_lower in lower_map:
        sources = lower_map[target_lower]
        if len(sources) == 1:
            return MappingDecision(target, required_or_optional, sources[0], "EXACT", "Target column is present.")
        return MappingDecision(target, required_or_optional, ";".join(sources), "AMBIGUOUS_MAPPING", "Duplicate case-insensitive target columns.")

    safe_sources: list[str] = []
    ambiguous_sources: list[str] = []
    for alias in SAFE_ALIAS_CANDIDATES.get(target, []):
        alias_lower = alias.lower()
        if alias_lower not in lower_map:
            continue
        sources = lower_map[alias_lower]
        if len(sources) != 1:
            ambiguous_sources.extend(sources)
            continue
        source = sources[0]
        if target == "timestamp_sgt" and not has_sgt_timezone_semantics(preview, source):
            ambiguous_sources.append(source)
            continue
        if target == "wbgt_a_c" and not has_contract_source_context(preview):
            ambiguous_sources.append(source)
            continue
        safe_sources.append(source)

    if len(safe_sources) == 1 and not ambiguous_sources:
        return MappingDecision(target, required_or_optional, safe_sources[0], "SAFE_ALIAS", "Alias is allowed and context is clear.")
    if len(safe_sources) == 1:
        return MappingDecision(
            target,
            required_or_optional,
            safe_sources[0],
            "SAFE_ALIAS",
            f"Alias is allowed and context is clear; ignored ambiguous aliases={';'.join(ambiguous_sources)}.",
        )
    if len(safe_sources) > 1:
        return MappingDecision(target, required_or_optional, ";".join(safe_sources), "AMBIGUOUS_MAPPING", "Multiple safe alias sources.")
    if ambiguous_sources:
        return MappingDecision(target, required_or_optional, ";".join(ambiguous_sources), "AMBIGUOUS_MAPPING", "Alias exists but timezone/contract semantics are not clear.")
    return MappingDecision(target, required_or_optional, "", "MISSING", "No exact column or safe alias.")


def build_mappings(preview: TablePreview, required: list[str], optional: list[str]) -> list[MappingDecision]:
    """Build mapping decisions for required and optional target columns."""
    decisions: list[MappingDecision] = []
    for target in required:
        decisions.append(decide_mapping_for_target(target, "required", preview))
    for target in optional:
        decisions.append(decide_mapping_for_target(target, "optional", preview))
    return decisions


def mapping_source(mappings: list[MappingDecision], target: str) -> str:
    """Return the source column for a successful mapping."""
    for mapping in mappings:
        if mapping.target_column == target and mapping.mapping_status in {"EXACT", "SAFE_ALIAS"}:
            return mapping.source_column
    return ""


def to_float(value: Any) -> float | None:
    """Convert a value to float when possible."""
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    text = str(value).strip()
    if text in {"", "NA", "NaN", "nan", "None", "null"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def non_empty(value: Any) -> bool:
    """Return whether a value is non-empty for schema metadata checks."""
    return str(value if value is not None else "").strip() not in {"", "NA", "NaN", "nan", "None", "null"}


def is_prospective_label(value: Any) -> bool:
    """Identify prospective rows without accepting retrospective rows."""
    text = str(value if value is not None else "").strip().lower()
    return "prospective" in text or text in {"future", "forecast", "formal_prospective"}


def distinct_non_empty(rows: list[dict[str, Any]], column: str) -> set[str]:
    """Return distinct non-empty values in a source column."""
    if not column:
        return set()
    return {str(row.get(column, "")).strip() for row in rows if non_empty(row.get(column, ""))}


def all_non_empty(rows: list[dict[str, Any]], column: str) -> bool:
    """Return whether all rows have a non-empty value for a column."""
    return bool(rows) and bool(column) and all(non_empty(row.get(column, "")) for row in rows)


def all_numeric(rows: list[dict[str, Any]], column: str) -> bool:
    """Return whether all rows have numeric values for a column."""
    return bool(rows) and bool(column) and all(to_float(row.get(column)) is not None for row in rows)


def check_row(candidate_path: str, check_id: str, check_group: str, status: str, detail: str) -> dict[str, Any]:
    """Build one validation/check row."""
    return {
        "candidate_path": candidate_path,
        "check_id": check_id,
        "check_group": check_group,
        "check_status": status,
        "detail": detail,
    }


def sha256_file(path: Path) -> str:
    """Return a SHA256 checksum when feasible."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_schema_role(preview: TablePreview, mapped_required_count: int, required_count: int) -> str:
    """Classify likely schema role from columns and path context."""
    text = path_text(preview.path)
    if mapped_required_count == required_count:
        return "formal_snapshot_schema_candidate"
    if mapped_required_count >= 3:
        return "partial_schema_bridge_candidate"
    if any(token in text for token in ("formal_snapshot", "prospective_snapshot", "v11_archive_formal_beta", "v11_beta_formal")):
        return "formal_path_schema_unknown"
    return "inventory_or_validation_output"


def assess_candidate(
    preview: TablePreview,
    required: list[str],
    optional: list[str],
    forbidden: list[str],
    config: dict[str, Any],
) -> CandidateAssessment:
    """Assess one compact table against the A-L1H.6 required schema."""
    mappings = build_mappings(preview, required, optional) if preview.read_status == "READ_OK" else []
    forbidden_lower = {column.lower() for column in forbidden}
    present_forbidden = [column for column in preview.columns if column.strip().lower() in forbidden_lower]
    missing_required = [
        mapping.target_column
        for mapping in mappings
        if mapping.required_or_optional == "required" and mapping.mapping_status == "MISSING"
    ]
    ambiguous_required = [
        mapping.target_column
        for mapping in mappings
        if mapping.required_or_optional == "required" and mapping.mapping_status == "AMBIGUOUS_MAPPING"
    ]
    mapped_required_count = sum(
        1
        for mapping in mappings
        if mapping.required_or_optional == "required" and mapping.mapping_status in {"EXACT", "SAFE_ALIAS"}
    )
    optional_present = [
        mapping.target_column
        for mapping in mappings
        if mapping.required_or_optional == "optional" and mapping.mapping_status in {"EXACT", "SAFE_ALIAS"}
    ]
    role = classify_schema_role(preview, mapped_required_count, len(required))

    label_col = mapping_source(mappings, "is_retrospective_or_prospective")
    station_col = mapping_source(mappings, "station_id")
    official_col = mapping_source(mappings, "official_wbgt_c")
    wbgt_a_col = mapping_source(mappings, "wbgt_a_c")
    model_col = mapping_source(mappings, "wbgt_a_model_id")
    version_col = mapping_source(mappings, "wbgt_a_version")
    quality_col = mapping_source(mappings, "quality_flag")
    p_model_col = mapping_source(mappings, "p_ge31_model_id_optional")

    prospective_rows = [row for row in preview.rows if is_prospective_label(row.get(label_col, ""))]
    support_rows = prospective_rows
    n_ge31 = sum(1 for row in support_rows if (to_float(row.get(official_col)) or -math.inf) >= 31.0)
    n_ge33 = sum(1 for row in support_rows if (to_float(row.get(official_col)) or -math.inf) >= 33.0)
    n_stations = len(distinct_non_empty(support_rows or preview.rows, station_col))
    source_sha = ""
    if preview.read_status == "READ_OK":
        try:
            source_sha = sha256_file(preview.path)
        except OSError:
            source_sha = ""

    checks: list[dict[str, Any]] = []
    candidate_path = rel(preview.path)
    checks.append(
        check_row(
            candidate_path,
            "required_columns_present_or_safely_mapped",
            "schema",
            "PASS" if not missing_required and not ambiguous_required and mapped_required_count == len(required) else "FAIL",
            f"missing={';'.join(missing_required) or 'none'}; ambiguous={';'.join(ambiguous_required) or 'none'}",
        )
    )
    checks.append(
        check_row(
            candidate_path,
            "forbidden_columns_absent",
            "safety",
            "PASS" if not present_forbidden else "FAIL",
            ";".join(present_forbidden) or "none",
        )
    )
    checks.append(
        check_row(
            candidate_path,
            "minimum_prospective_rows",
            "support",
            "PASS" if len(prospective_rows) >= int(config["minimum_prospective_rows"]) else "FAIL",
            f"n_prospective_rows={len(prospective_rows)}; minimum={config['minimum_prospective_rows']}",
        )
    )
    checks.append(
        check_row(
            candidate_path,
            "minimum_ge31_events",
            "support",
            "PASS" if n_ge31 >= int(config["minimum_ge31_events"]) else "FAIL",
            f"n_ge31={n_ge31}; minimum={config['minimum_ge31_events']}",
        )
    )
    checks.append(
        check_row(
            candidate_path,
            "ge33_event_support_reported",
            "support",
            "PASS" if n_ge33 >= int(config["minimum_ge33_events_for_promotion"]) else "INFO",
            f"n_ge33={n_ge33}; promotion_minimum={config['minimum_ge33_events_for_promotion']}",
        )
    )
    checks.append(
        check_row(
            candidate_path,
            "official_wbgt_c_numeric",
            "schema",
            "PASS" if all_numeric(prospective_rows, official_col) else "FAIL",
            "official_wbgt_c numeric for prospective rows" if official_col else "official_wbgt_c missing",
        )
    )
    checks.append(
        check_row(
            candidate_path,
            "wbgt_a_c_numeric",
            "schema",
            "PASS" if all_numeric(prospective_rows, wbgt_a_col) else "FAIL",
            "wbgt_a_c numeric for prospective rows" if wbgt_a_col else "wbgt_a_c missing",
        )
    )
    checks.append(
        check_row(
            candidate_path,
            "model_version_metadata_present",
            "metadata",
            "PASS" if all_non_empty(prospective_rows, model_col) and all_non_empty(prospective_rows, version_col) else "FAIL",
            "wbgt_a_model_id and wbgt_a_version non-null for prospective rows",
        )
    )
    checks.append(
        check_row(
            candidate_path,
            "quality_flag_present",
            "metadata",
            "PASS" if all_non_empty(prospective_rows, quality_col) else "FAIL",
            "quality_flag non-null for prospective rows",
        )
    )
    checks.append(
        check_row(
            candidate_path,
            "retrospective_prospective_label_present",
            "metadata",
            "PASS" if label_col and prospective_rows else "FAIL",
            f"label_column={label_col or 'missing'}; n_prospective_rows={len(prospective_rows)}",
        )
    )

    if preview.read_status != "READ_OK":
        detection_status = preview.read_status
        readiness_status = "NOT_READ"
        readiness_reason = preview.error or preview.read_status
    elif present_forbidden:
        detection_status = "FORBIDDEN_COLUMNS_PRESENT"
        readiness_status = "BLOCKED_FORBIDDEN_COLUMNS"
        readiness_reason = f"forbidden_columns={';'.join(present_forbidden)}"
    elif ambiguous_required:
        detection_status = "AMBIGUOUS_MAPPING"
        readiness_status = "BLOCKED_SCHEMA"
        readiness_reason = f"ambiguous_required={';'.join(ambiguous_required)}"
    elif missing_required:
        detection_status = "SCHEMA_INVALID" if role != "inventory_or_validation_output" else "NOT_FORMAL_SNAPSHOT_SCHEMA"
        readiness_status = "BLOCKED_SCHEMA" if role != "inventory_or_validation_output" else "WAITING_FOR_FORMAL_INPUT"
        readiness_reason = f"missing_required={';'.join(missing_required)}"
    elif not all_numeric(prospective_rows, official_col) or not all_numeric(prospective_rows, wbgt_a_col):
        detection_status = "SCHEMA_INVALID"
        readiness_status = "BLOCKED_SCHEMA"
        readiness_reason = "official_wbgt_c and wbgt_a_c must be numeric for prospective rows"
    elif not all_non_empty(prospective_rows, model_col) or not all_non_empty(prospective_rows, version_col):
        detection_status = "SCHEMA_INVALID"
        readiness_status = "BLOCKED_SCHEMA"
        readiness_reason = "model/version metadata missing in prospective rows"
    elif not all_non_empty(prospective_rows, quality_col) or not label_col or not prospective_rows:
        detection_status = "SCHEMA_INVALID"
        readiness_status = "BLOCKED_SCHEMA"
        readiness_reason = "quality_flag or prospective label missing in prospective rows"
    elif len(prospective_rows) < int(config["minimum_prospective_rows"]) or n_ge31 < int(config["minimum_ge31_events"]):
        detection_status = "INSUFFICIENT_PROSPECTIVE_SUPPORT"
        readiness_status = "WAITING_FOR_FORMAL_INPUT"
        readiness_reason = (
            f"n_prospective_rows={len(prospective_rows)}; n_ge31={n_ge31}; "
            f"minimum_rows={config['minimum_prospective_rows']}; minimum_ge31={config['minimum_ge31_events']}"
        )
    else:
        detection_status = "FREEZE_READY"
        readiness_status = "READY_TO_FREEZE"
        readiness_reason = "All required schema, safety, support, numeric, metadata, quality, and label checks passed."

    return CandidateAssessment(
        preview=preview,
        mappings=mappings,
        required_columns=required,
        optional_columns=optional,
        forbidden_columns=forbidden,
        likely_schema_role=role,
        detection_status=detection_status,
        readiness_status=readiness_status,
        readiness_reason=readiness_reason,
        missing_required_columns=missing_required,
        ambiguous_required_columns=ambiguous_required,
        present_forbidden_columns=present_forbidden,
        mapped_required_count=mapped_required_count,
        optional_columns_present=optional_present,
        n_rows=len(preview.rows),
        n_prospective_rows=len(prospective_rows),
        n_stations=n_stations,
        n_ge31=n_ge31,
        n_ge33=n_ge33,
        wbgt_a_model_id=";".join(sorted(distinct_non_empty(prospective_rows, model_col))) if model_col else "",
        wbgt_a_version=";".join(sorted(distinct_non_empty(prospective_rows, version_col))) if version_col else "",
        p_ge31_model_id=";".join(sorted(distinct_non_empty(prospective_rows, p_model_col))) if p_model_col else "",
        source_sha256=source_sha,
        check_rows=checks,
    )


def make_input_inventory(config: dict[str, Any], candidate_tables: list[Path]) -> list[dict[str, Any]]:
    """Create the configured input/search inventory."""
    rows: list[dict[str, Any]] = []
    for input_id in ["l1h5_output_schema_path", "l1h6_required_schema_path", "l1h6_status_path"]:
        path = resolve_path(config[input_id])
        rows.append(
            {
                "input_id": input_id,
                "input_role": "configured_dependency",
                "path": rel(path),
                "exists": path.exists(),
                "file_type": path.suffix.lower() if path.is_file() else "directory",
                "bytes": path.stat().st_size if path.exists() and path.is_file() else "",
                "searched": "no",
                "notes": "A-L1H.5/A-L1H.6 dependency; read for schema/status context only.",
            }
        )
    for index, raw_root in enumerate(config.get("candidate_search_roots", []), start=1):
        root = resolve_path(raw_root)
        rows.append(
            {
                "input_id": f"candidate_search_root_{index}",
                "input_role": "configured_candidate_root",
                "path": rel(root),
                "exists": root.exists(),
                "file_type": "directory",
                "bytes": "",
                "searched": "yes" if root.exists() else "no",
                "notes": "Searched only for allowed compact CSV/CSV.GZ/Parquet files.",
            }
        )
    rows.append(
        {
            "input_id": "candidate_tables_scanned",
            "input_role": "derived_inventory_count",
            "path": "",
            "exists": "",
            "file_type": "",
            "bytes": "",
            "searched": "yes",
            "notes": str(len(candidate_tables)),
        }
    )
    return rows


def make_candidate_inventory(assessments: list[CandidateAssessment]) -> list[dict[str, Any]]:
    """Create candidate table inventory rows."""
    rows: list[dict[str, Any]] = []
    for assessment in assessments:
        preview = assessment.preview
        rows.append(
            {
                "path": rel(preview.path),
                "file_type": preview.file_type,
                "bytes": preview.bytes,
                "row_count": assessment.n_rows if preview.read_status == "READ_OK" else "",
                "columns": ";".join(preview.columns),
                "likely_schema_role": assessment.likely_schema_role,
                "detection_status": assessment.detection_status,
            }
        )
    return rows


def make_mapping_rows(assessments: list[CandidateAssessment]) -> list[dict[str, Any]]:
    """Create safe/ambiguous/missing mapping output rows."""
    rows: list[dict[str, Any]] = []
    for assessment in assessments:
        for mapping in assessment.mappings:
            rows.append(
                {
                    "candidate_path": rel(assessment.preview.path),
                    "target_column": mapping.target_column,
                    "required_or_optional": mapping.required_or_optional,
                    "source_column": mapping.source_column,
                    "mapping_status": mapping.mapping_status,
                    "reason": mapping.reason,
                }
            )
    return rows


def make_required_schema_rows(assessments: list[CandidateAssessment]) -> list[dict[str, Any]]:
    """Create required/optional schema check rows."""
    rows: list[dict[str, Any]] = []
    for assessment in assessments:
        for mapping in assessment.mappings:
            if mapping.required_or_optional == "required":
                check_status = "PASS" if mapping.mapping_status in {"EXACT", "SAFE_ALIAS"} else "FAIL"
            else:
                check_status = "PASS" if mapping.mapping_status in {"EXACT", "SAFE_ALIAS"} else "OPTIONAL_ABSENT"
                if mapping.mapping_status == "AMBIGUOUS_MAPPING":
                    check_status = "FAIL"
            rows.append(
                {
                    "candidate_path": rel(assessment.preview.path),
                    "target_column": mapping.target_column,
                    "required_or_optional": mapping.required_or_optional,
                    "source_column": mapping.source_column,
                    "mapping_status": mapping.mapping_status,
                    "check_status": check_status,
                    "reason": mapping.reason,
                }
            )
    return rows


def make_forbidden_rows(assessments: list[CandidateAssessment]) -> list[dict[str, Any]]:
    """Create forbidden-column check rows."""
    rows: list[dict[str, Any]] = []
    for assessment in assessments:
        present_lower = {column.lower(): column for column in assessment.present_forbidden_columns}
        for forbidden in assessment.forbidden_columns:
            present = forbidden.lower() in present_lower
            rows.append(
                {
                    "candidate_path": rel(assessment.preview.path),
                    "forbidden_column": forbidden,
                    "present": "yes" if present else "no",
                    "check_status": "FAIL" if present else "PASS",
                    "reason": present_lower.get(forbidden.lower(), "absent"),
                }
            )
    return rows


def make_freeze_readiness_rows(assessments: list[CandidateAssessment]) -> list[dict[str, Any]]:
    """Create freeze-readiness check rows."""
    rows: list[dict[str, Any]] = []
    for assessment in assessments:
        rows.extend(assessment.check_rows)
        rows.append(
            check_row(
                rel(assessment.preview.path),
                "freeze_readiness_decision",
                "decision",
                assessment.readiness_status,
                assessment.readiness_reason,
            )
        )
    return rows


def make_manifest_schema_rows() -> list[dict[str, Any]]:
    """Return the frozen snapshot manifest schema."""
    return [
        {"field_name": "snapshot_id", "type": "string", "required": "yes", "description": "Stable identifier for the freeze attempt or written snapshot."},
        {"field_name": "created_at", "type": "datetime_utc", "required": "yes", "description": "UTC creation timestamp for the manifest row."},
        {"field_name": "source_table_path", "type": "path", "required": "when_candidate_exists", "description": "Compact source candidate table path."},
        {"field_name": "frozen_table_path", "type": "path", "required": "when_written", "description": "Written frozen CSV.GZ/Parquet path when freeze_mode=write_snapshot."},
        {"field_name": "n_rows", "type": "integer", "required": "when_candidate_exists", "description": "Total source row count."},
        {"field_name": "n_prospective_rows", "type": "integer", "required": "when_candidate_exists", "description": "Prospective rows identified by provenance label."},
        {"field_name": "n_stations", "type": "integer", "required": "when_candidate_exists", "description": "Distinct station IDs in prospective rows."},
        {"field_name": "n_ge31", "type": "integer", "required": "when_candidate_exists", "description": "Official WBGT >=31 C events in prospective rows."},
        {"field_name": "n_ge33", "type": "integer", "required": "when_candidate_exists", "description": "Official WBGT >=33 C events in prospective rows."},
        {"field_name": "wbgt_a_model_id", "type": "string", "required": "yes", "description": "Frozen WBGT_A model identifier values."},
        {"field_name": "wbgt_a_version", "type": "string", "required": "yes", "description": "Frozen WBGT_A version values."},
        {"field_name": "p_ge31_model_id", "type": "string", "required": "if_present", "description": "Optional P_ge31 model identifier values when present."},
        {"field_name": "source_sha256", "type": "sha256", "required": "if_feasible", "description": "Checksum of the source compact table."},
        {"field_name": "frozen_sha256", "type": "sha256", "required": "when_written", "description": "Checksum of the written frozen table."},
        {"field_name": "status", "type": "categorical", "required": "yes", "description": "A-L1H.7 decision status."},
        {"field_name": "claim_boundary", "type": "string", "required": "yes", "description": "Snapshot-freezer claim boundary."},
    ]


def utc_timestamp() -> str:
    """Return a compact UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def snapshot_id(config: dict[str, Any]) -> str:
    """Return a snapshot id for this run."""
    prefix = str(config.get("snapshot_id_prefix", "systema_l1h7_formal_snapshot"))
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def freeze_mode(config: dict[str, Any]) -> str:
    """Return effective freeze mode."""
    return str(config.get("freeze_mode") or config.get("freeze_mode_default") or "dry_run")


def canonical_rows(assessment: CandidateAssessment) -> tuple[list[str], list[dict[str, Any]]]:
    """Return canonical rows using exact or safe alias mappings."""
    columns = assessment.required_columns + [
        column
        for column in assessment.optional_columns
        if mapping_source(assessment.mappings, column)
    ]
    rows: list[dict[str, Any]] = []
    for source_row in assessment.preview.rows:
        output_row: dict[str, Any] = {}
        for target in columns:
            source = mapping_source(assessment.mappings, target)
            if source:
                output_row[target] = source_row.get(source, "")
        rows.append(output_row)
    return columns, rows


def write_frozen_snapshot(assessment: CandidateAssessment, config: dict[str, Any], sid: str) -> Path:
    """Write a compact CSV.GZ frozen snapshot from a valid candidate."""
    output_root = resolve_path(config["output_freeze_root"])
    output_root.mkdir(parents=True, exist_ok=True)
    frozen_path = output_root / f"{sid}.csv.gz"
    columns, rows = canonical_rows(assessment)
    with gzip.open(frozen_path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return frozen_path


def choose_best_candidate(assessments: list[CandidateAssessment]) -> CandidateAssessment | None:
    """Choose the best plausible freeze candidate, if any."""
    ready = [item for item in assessments if item.readiness_status == "READY_TO_FREEZE"]
    if ready:
        return sorted(ready, key=lambda item: (item.n_prospective_rows, item.n_ge31, item.n_rows), reverse=True)[0]
    plausible = [
        item
        for item in assessments
        if item.mapped_required_count > 0 or item.likely_schema_role in {"formal_path_schema_unknown", "partial_schema_bridge_candidate"}
    ]
    if plausible:
        return sorted(plausible, key=lambda item: (item.mapped_required_count, item.n_prospective_rows, item.n_rows), reverse=True)[0]
    return None


def determine_overall_status(assessments: list[CandidateAssessment], best: CandidateAssessment | None, mode: str, frozen_path: Path | None) -> str:
    """Determine the lane decision status."""
    if best is not None and best.readiness_status == "READY_TO_FREEZE":
        return SNAPSHOT_FROZEN_PASS_STATUS if mode == "write_snapshot" and frozen_path is not None else READY_STATUS
    if any(item.present_forbidden_columns for item in assessments if item.mapped_required_count > 0 or item.likely_schema_role != "inventory_or_validation_output"):
        return BLOCKED_FORBIDDEN_STATUS
    if any(item.readiness_status == "BLOCKED_SCHEMA" for item in assessments if item.mapped_required_count > 0 or item.likely_schema_role != "inventory_or_validation_output"):
        return BLOCKED_SCHEMA_STATUS
    return WAITING_STATUS


def schema_status_for(status: str) -> str:
    """Return compact schema status text."""
    if status in {READY_STATUS, SNAPSHOT_FROZEN_PASS_STATUS}:
        return "PASS"
    if status == BLOCKED_SCHEMA_STATUS:
        return "BLOCKED_SCHEMA"
    if status == BLOCKED_FORBIDDEN_STATUS:
        return "NOT_EVALUATED_FORBIDDEN_COLUMNS"
    return "WAITING_NO_FORMAL_SCHEMA_CANDIDATE"


def forbidden_status_for(assessments: list[CandidateAssessment]) -> str:
    """Return compact forbidden-column status text."""
    return "BLOCKED_FORBIDDEN_COLUMNS" if any(item.present_forbidden_columns for item in assessments) else "PASS"


def make_manifest_row(
    status: str,
    config: dict[str, Any],
    sid: str,
    best: CandidateAssessment | None,
    frozen_path: Path | None,
) -> dict[str, Any]:
    """Create the frozen snapshot manifest row."""
    frozen_sha = ""
    if frozen_path is not None:
        try:
            frozen_sha = sha256_file(frozen_path)
        except OSError:
            frozen_sha = ""
    return {
        "snapshot_id": sid,
        "created_at": utc_timestamp(),
        "source_table_path": rel(best.preview.path) if best else "",
        "frozen_table_path": rel(frozen_path) if frozen_path else "",
        "n_rows": best.n_rows if best else "",
        "n_prospective_rows": best.n_prospective_rows if best else "",
        "n_stations": best.n_stations if best else "",
        "n_ge31": best.n_ge31 if best else "",
        "n_ge33": best.n_ge33 if best else "",
        "wbgt_a_model_id": best.wbgt_a_model_id if best else "",
        "wbgt_a_version": best.wbgt_a_version if best else "",
        "p_ge31_model_id": best.p_ge31_model_id if best else "",
        "source_sha256": best.source_sha256 if best else "",
        "frozen_sha256": frozen_sha,
        "status": status,
        "claim_boundary": config.get("claim_boundary", ""),
    }


def make_validation_rows(
    status: str,
    best: CandidateAssessment | None,
    frozen_path: Path | None,
) -> list[dict[str, Any]]:
    """Create validation rows for the best candidate or written snapshot."""
    if best is None:
        return [
            {
                "validation_target": "",
                "check_id": "formal_candidate_available",
                "check_group": "availability",
                "check_status": "WAITING",
                "detail": "No plausible formal snapshot candidate was found.",
            }
        ]
    rows = [
        {
            "validation_target": rel(best.preview.path),
            "check_id": row["check_id"],
            "check_group": row["check_group"],
            "check_status": row["check_status"],
            "detail": row["detail"],
        }
        for row in best.check_rows
    ]
    rows.append(
        {
            "validation_target": rel(frozen_path) if frozen_path else rel(best.preview.path),
            "check_id": "lane_status",
            "check_group": "decision",
            "check_status": status,
            "detail": best.readiness_reason,
        }
    )
    if frozen_path is None:
        rows.append(
            {
                "validation_target": rel(best.preview.path),
                "check_id": "frozen_table_written",
                "check_group": "dry_run",
                "check_status": "DRY_RUN_NOT_WRITTEN",
                "detail": "freeze_mode=dry_run; no formal snapshot data table was written.",
            }
        )
    else:
        rows.append(
            {
                "validation_target": rel(frozen_path),
                "check_id": "frozen_table_written",
                "check_group": "write_snapshot",
                "check_status": "PASS",
                "detail": "Frozen compact CSV.GZ table was written from source rows without fabrication.",
            }
        )
    return rows


def build_command_template(config_path: Path, status: str, mode: str) -> str:
    """Build the dry-run/write-snapshot command template."""
    return f"""# A-L1H.7 Snapshot Command Template

Decision status: `{status}`
Current freeze mode: `{mode}`

## Dry Run

The default lane mode is dry-run. It writes inventories, schema checks,
manifests, validation rows, and reports, but it does not write a formal snapshot
data table.

```bash
python scripts/v11_l1h7_run_formal_snapshot_freezer.py --config {rel(config_path)}
```

## Write Snapshot

Only after review, set `freeze_mode: write_snapshot` in
`{rel(config_path)}` and rerun the same command. The freezer will write a compact
CSV.GZ under `outputs/v11_systema_l1_high_tail/formal_snapshot/` only if a real
candidate passes required schema, forbidden-column, numeric, metadata, quality,
prospective-row, and ge31 support checks.

```bash
python scripts/v11_l1h7_run_formal_snapshot_freezer.py --config {rel(config_path)}
```

## Standalone Validation

After a snapshot is written, validate the frozen table explicitly:

```bash
python scripts/v11_l1h7_validate_frozen_snapshot.py --config {rel(config_path)} --snapshot outputs/v11_systema_l1_high_tail/formal_snapshot/<snapshot_id>.csv.gz
```

No command in this template trains a model, modifies the archive collector, or
creates station-adjusted WBGT, local 100 m WBGT, official warning probability,
risk/hazard score, System A/B coupling output, fake rows, or fake metrics.
"""


def build_downstream_instructions() -> str:
    """Build A-L1H.6 downstream rerun instructions."""
    command = "python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml"
    return f"""# Downstream A-L1H.6 Rerun Instructions

Run A-L1H.6 only after A-L1H.7 has written and reviewed a real frozen formal
snapshot table. A-L1H.7 does not run A-L1H.6 automatically.

```bash
{command}
```

Expected setup before rerun:

- The frozen snapshot is a compact CSV/CSV.GZ/Parquet table under a configured
  A-L1H.6 candidate path.
- Required A-L1H.6 columns are present exactly or safely bridged by A-L1H.7.
- Forbidden columns are absent.
- Prospective rows are real rows, not placeholders.
- `p_ge31_optional` remains an optional diagnostic companion.
- `p_ge33_optional` remains exploratory unless future support and calibration
  evidence meet the registered gates.
"""


def build_report(
    status: str,
    config: dict[str, Any],
    assessments: list[CandidateAssessment],
    best: CandidateAssessment | None,
    mode: str,
    frozen_path: Path | None,
) -> str:
    """Build the English A-L1H.7 report."""
    today = config.get("generated_date", datetime.now().date().isoformat())
    inventory_rows = make_candidate_inventory(assessments)
    mapping_rows = make_mapping_rows(assessments)
    schema_rows = make_required_schema_rows(assessments)
    forbidden_rows = make_forbidden_rows(assessments)
    readiness_rows = make_freeze_readiness_rows(assessments)
    best_path = rel(best.preview.path) if best else "none"
    frozen_text = rel(frozen_path) if frozen_path else "none"
    l1h6_command = "python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml"
    return f"""# System A A-L1H.7 Formal Snapshot Freezer

Generated: {today}
Decision status: `{status}`
Branch: `{git_branch()}`

## 1. Why A-L1H.7 Follows A-L1H.6

A-L1H.5 froze the System A Level 1 output contract, and A-L1H.6 built the
prospective evaluation harness that is currently waiting for a formal snapshot.
A-L1H.7 sits between them: it searches only compact formal/prospective outputs,
bridges columns only when safe, and prepares a freeze-ready package or a
WAITING/BLOCKED report without fabricating rows or metrics.

## 2. Candidate Search Results

Candidate tables scanned: `{len(assessments)}`

Best candidate path: `{best_path}`

{markdown_table(inventory_rows, ["path", "file_type", "bytes", "row_count", "likely_schema_role", "detection_status"], 20)}

## 3. Column Mapping Results

{markdown_table(mapping_rows, ["candidate_path", "target_column", "required_or_optional", "source_column", "mapping_status", "reason"], 24)}

Safe aliases are accepted only when timezone or contract-source semantics are
clear. Ambiguous aliases are recorded as `AMBIGUOUS_MAPPING` and are not silently
used.

## 4. Schema And Forbidden-Column Checks

Required schema check:

{markdown_table(schema_rows, ["candidate_path", "target_column", "required_or_optional", "source_column", "mapping_status", "check_status"], 24)}

Forbidden-column check:

{markdown_table(forbidden_rows, ["candidate_path", "forbidden_column", "present", "check_status", "reason"], 24)}

## 5. Freeze Readiness Decision

Freeze mode: `{mode}`

Written frozen table: `{frozen_text}`

{markdown_table(readiness_rows, ["candidate_path", "check_id", "check_group", "check_status", "detail"], 24)}

READY_TO_FREEZE requires all required columns present or safely mapped, no
forbidden columns, at least the configured prospective rows and ge31 events,
numeric `official_wbgt_c` and `wbgt_a_c`, model/version metadata, `quality_flag`,
and a retrospective/prospective label.

## 6. Dry-Run Vs Write-Snapshot Behavior

In `dry_run`, this lane does not write a formal snapshot data table. It writes
only inventories, checks, manifests, validation rows, command templates, reports,
and status files. In `write_snapshot`, it writes a compact CSV.GZ under
`outputs/v11_systema_l1_high_tail/formal_snapshot/` only if a real candidate is
freeze-ready.

## 7. Downstream A-L1H.6 Rerun Instructions

After a reviewed frozen snapshot exists, rerun:

`{l1h6_command}`

A-L1H.7 does not run A-L1H.6 automatically and does not modify A-L1H.6 promotion
gates.

## 8. Claim Boundaries

- No model training.
- No archive collector changes.
- No station-adjusted WBGT.
- No local 100 m WBGT.
- No official warning probability.
- No risk_score or hazard_score.
- No System B coupling.
- No System B, SOLWEIG, or Tmrt features.
- No fake metrics or fake rows.
"""


def build_cn_doc(
    status: str,
    config: dict[str, Any],
    assessments: list[CandidateAssessment],
    best: CandidateAssessment | None,
    mode: str,
) -> str:
    """Build the Chinese A-L1H.7 documentation note in valid UTF-8."""
    today = config.get("generated_date", datetime.now().date().isoformat())
    best_path = rel(best.preview.path) if best else "无"
    n_rows = best.n_rows if best else "NA"
    n_prospective = best.n_prospective_rows if best else "NA"
    n_ge31 = best.n_ge31 if best else "NA"
    n_ge33 = best.n_ge33 if best else "NA"
    return f"""# OpenHeat System A A-L1H.7 正式快照冻结器与模式桥

生成日期：{today}
决策状态：`{status}`

## 1. 为什么 A-L1H.7 接在 A-L1H.6 之后

A-L1H.5 已经冻结 System A Level 1 的小时输出契约。A-L1H.6 已经建立前瞻评估框架，但当前状态仍在等待正式冻结快照。A-L1H.7 的作用是把未来快照创建过程做成可复查的冻结器与模式桥：只检查紧凑候选表，只在语义安全时桥接列名，并输出 READY、WAITING 或 BLOCKED 证据包。

## 2. 候选表搜索结果

本轮只搜索配置中的正式/前瞻紧凑根目录，允许 `.csv`、`.csv.gz` 和 `.parquet`。候选表数量：`{len(assessments)}`。最佳候选：`{best_path}`。

## 3. 列映射结果

目标列来自 A-L1H.6 必需输入模式。精确列名直接通过；安全别名只有在时区语义或契约来源清楚时才会使用。`timestamp` 这类列如果不能确认 SGT 语义，会记录为 `AMBIGUOUS_MAPPING`，不会静默改名。

## 4. 模式与禁用列检查

必需列包括 `timestamp_sgt`、`timestamp_utc`、`station_id`、`official_wbgt_c`、`wbgt_a_c`、`wbgt_a_model_id`、`wbgt_a_version`、`is_retrospective_or_prospective` 和 `quality_flag`。禁用列包括 `cell_id`、`local_wbgt_c`、`delta_wbgt_cell`、`station_adjusted_wbgt_c`、`risk_score` 和 `hazard_score`。一旦候选正式快照含有禁用列，该候选会被拒绝。

## 5. 冻结就绪决策

冻结模式：`{mode}`。

最佳候选支持度：`n_rows={n_rows}`，`n_prospective_rows={n_prospective}`，`n_ge31={n_ge31}`，`n_ge33={n_ge33}`。

只有在必需列齐全或安全映射、禁用列缺失、前瞻行数与 ge31 事件达到配置阈值、`official_wbgt_c` 与 `wbgt_a_c` 为数值、模型和版本元数据存在、`quality_flag` 存在、且回顾/前瞻标签存在时，才会输出 `A_L1H7_READY_TO_FREEZE`。

## 6. dry_run 与 write_snapshot 行为

默认 `dry_run` 不写正式快照数据表，只写清单、检查表、清单模式、验证表、命令模板、报告和状态文件。只有当配置显式设置 `freeze_mode: write_snapshot` 且真实候选表通过检查时，才会在 `outputs/v11_systema_l1_high_tail/formal_snapshot/` 写出紧凑 CSV.GZ 快照。

## 7. 下游 A-L1H.6 重跑说明

A-L1H.7 不会自动运行 A-L1H.6。正式快照写出并复查后，再运行：

`python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml`

## 8. 声明边界

- 不训练新模型。
- 不修改 archive collector。
- 不创建 station-adjusted WBGT。
- 不创建本地 100 m WBGT。
- 不创建官方预警概率。
- 不创建 risk_score 或 hazard_score。
- 不创建 System A/B 耦合输出。
- 不使用 System B、SOLWEIG 或 Tmrt 特征。
- 不创建伪指标或伪快照行。
"""


def build_status(
    result: FreezerResult,
    config: dict[str, Any],
    best: CandidateAssessment | None,
) -> str:
    """Build the A-L1H.7 status Markdown."""
    today = config.get("generated_date", datetime.now().date().isoformat())
    files = "\n".join(f"- `{rel(path)}`" for path in result.output_paths)
    best_reason = best.readiness_reason if best else "No plausible formal snapshot candidate found."
    return f"""# A-L1H.7 Status

Status: {result.status}
Generated: {today}
Branch: {git_branch()}

## Scope

System A formal snapshot freezer / schema bridge only. No model training, no
A-L1H.5 contract changes, no A-L1H.6 gate changes, no archive collector changes,
no station-adjusted WBGT, no local 100 m WBGT, no official warning probability,
no risk_score, no hazard_score, no System B coupling, and no fake rows.

## Commands Run

- `python scripts/v11_l1h7_run_formal_snapshot_freezer.py --config configs/v11/systema_l1h7_formal_snapshot_freezer.yaml`

## Key Results

- Candidate tables scanned: {result.candidate_tables_scanned}
- Best candidate path: {result.best_candidate_path or 'none'}
- Freeze mode: {result.freeze_mode}
- n_rows / n_prospective_rows / n_ge31 / n_ge33: {result.n_rows or 'NA'} / {result.n_prospective_rows or 'NA'} / {result.n_ge31 or 'NA'} / {result.n_ge33 or 'NA'}
- Schema status: {result.schema_status}
- Forbidden-column status: {result.forbidden_column_status}
- Decision reason: {best_reason}
- Downstream A-L1H.6 rerun command: `{result.downstream_l1h6_rerun_command}`

## Files Created / Modified

{files}

## Caveats

- `dry_run` does not write a formal snapshot data table.
- WAITING is acceptable when no real formal input exists.
- BLOCKED is acceptable when a plausible candidate has invalid schema or forbidden columns.
- P_ge31 remains optional and is not an official warning probability.
- P_ge33 remains exploratory unless future support and calibration evidence are explicit.

## Safe To Commit

Controlled config, scripts, docs, and compact CSV/Markdown outputs from this
lane after review.

## Not Safe To Commit

Raw archives, rasters, SOLWEIG/System B outputs, tif/tiff files, svfs.zip, patch
zip packages, raw API dumps, or large forecast/live CSVs.
"""


def output_paths_from_config(config: dict[str, Any]) -> dict[str, Path]:
    """Return resolved configured output paths."""
    return {key: resolve_path(value) for key, value in config["outputs"].items() if key != "output_dir"}


def run_freezer(config_path: Path) -> FreezerResult:
    """Run the A-L1H.7 formal snapshot freezer."""
    config = load_config(config_path)
    required, optional, forbidden = load_schema_contract(config)
    candidate_tables = discover_candidate_tables(config)
    previews = [read_table_preview(path, config) for path in candidate_tables]
    assessments = [assess_candidate(preview, required, optional, forbidden, config) for preview in previews]
    best = choose_best_candidate(assessments)
    mode = freeze_mode(config)
    sid = snapshot_id(config)
    frozen_path: Path | None = None
    if best is not None and best.readiness_status == "READY_TO_FREEZE" and mode == "write_snapshot":
        frozen_path = write_frozen_snapshot(best, config, sid)
    status = determine_overall_status(assessments, best, mode, frozen_path)

    manifest_row = make_manifest_row(status, config, sid, best, frozen_path)
    validation_rows = make_validation_rows(status, best, frozen_path)
    outputs = output_paths_from_config(config)
    output_paths: list[Path] = []
    output_paths.append(
        write_csv(
            outputs["input_inventory"],
            make_input_inventory(config, candidate_tables),
            ["input_id", "input_role", "path", "exists", "file_type", "bytes", "searched", "notes"],
        )
    )
    output_paths.append(
        write_csv(
            outputs["candidate_table_inventory"],
            make_candidate_inventory(assessments),
            ["path", "file_type", "bytes", "row_count", "columns", "likely_schema_role", "detection_status"],
        )
    )
    output_paths.append(
        write_csv(
            outputs["column_mapping_candidates"],
            make_mapping_rows(assessments),
            ["candidate_path", "target_column", "required_or_optional", "source_column", "mapping_status", "reason"],
        )
    )
    output_paths.append(
        write_csv(
            outputs["required_schema_check"],
            make_required_schema_rows(assessments),
            ["candidate_path", "target_column", "required_or_optional", "source_column", "mapping_status", "check_status", "reason"],
        )
    )
    output_paths.append(
        write_csv(
            outputs["forbidden_column_check"],
            make_forbidden_rows(assessments),
            ["candidate_path", "forbidden_column", "present", "check_status", "reason"],
        )
    )
    output_paths.append(
        write_csv(
            outputs["freeze_readiness_check"],
            make_freeze_readiness_rows(assessments),
            ["candidate_path", "check_id", "check_group", "check_status", "detail"],
        )
    )
    output_paths.append(
        write_csv(
            outputs["snapshot_manifest_schema"],
            make_manifest_schema_rows(),
            ["field_name", "type", "required", "description"],
        )
    )
    output_paths.append(write_text(outputs["snapshot_command_template"], build_command_template(config_path, status, mode)))
    output_paths.append(write_text(outputs["downstream_l1h6_rerun_instructions"], build_downstream_instructions()))
    output_paths.append(
        write_csv(
            outputs["frozen_snapshot_manifest"],
            [manifest_row],
            [
                "snapshot_id",
                "created_at",
                "source_table_path",
                "frozen_table_path",
                "n_rows",
                "n_prospective_rows",
                "n_stations",
                "n_ge31",
                "n_ge33",
                "wbgt_a_model_id",
                "wbgt_a_version",
                "p_ge31_model_id",
                "source_sha256",
                "frozen_sha256",
                "status",
                "claim_boundary",
            ],
        )
    )
    output_paths.append(
        write_csv(
            outputs["frozen_snapshot_validation"],
            validation_rows,
            ["validation_target", "check_id", "check_group", "check_status", "detail"],
        )
    )

    result = FreezerResult(
        status=status,
        candidate_tables_scanned=len(assessments),
        best_candidate_path=rel(best.preview.path) if best and best.readiness_status == "READY_TO_FREEZE" else "",
        freeze_mode=mode,
        n_rows=str(best.n_rows) if best and best.readiness_status == "READY_TO_FREEZE" else "",
        n_prospective_rows=str(best.n_prospective_rows) if best and best.readiness_status == "READY_TO_FREEZE" else "",
        n_ge31=str(best.n_ge31) if best and best.readiness_status == "READY_TO_FREEZE" else "",
        n_ge33=str(best.n_ge33) if best and best.readiness_status == "READY_TO_FREEZE" else "",
        schema_status=schema_status_for(status),
        forbidden_column_status=forbidden_status_for(assessments),
        downstream_l1h6_rerun_command="python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml",
        output_paths=output_paths,
    )
    report_path = write_text(outputs["report"], build_report(status, config, assessments, best, mode, frozen_path))
    cn_doc_path = write_text(outputs["cn_doc"], build_cn_doc(status, config, assessments, best, mode))
    result.output_paths.extend([report_path, cn_doc_path])
    result.output_paths.append(outputs["status"])
    write_text(outputs["status"], build_status(result, config, best))
    if frozen_path is not None:
        result.output_paths.append(frozen_path)
    return result


def main() -> int:
    """CLI entrypoint for direct freezer runs."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the A-L1H.7 formal snapshot freezer/schema bridge. Inputs, outputs, "
            "candidate roots, freeze mode, support thresholds, and claim boundaries are "
            "declared in the YAML config. The default dry_run mode writes only compact "
            "manifests/checks/reports and never fabricates snapshot rows."
        )
    )
    parser.add_argument("--config", default="configs/v11/systema_l1h7_formal_snapshot_freezer.yaml", help="Path to the explicit A-L1H.7 YAML config.")
    args = parser.parse_args()
    result = run_freezer(resolve_path(args.config))
    print(f"[status] {result.status}")
    print(f"[candidate_tables_scanned] {result.candidate_tables_scanned}")
    print(f"[best_candidate_path] {result.best_candidate_path or 'none'}")
    print(f"[freeze_mode] {result.freeze_mode}")
    print(f"[n_rows] {result.n_rows or 'NA'}")
    print(f"[n_prospective_rows] {result.n_prospective_rows or 'NA'}")
    print(f"[n_ge31] {result.n_ge31 or 'NA'}")
    print(f"[n_ge33] {result.n_ge33 or 'NA'}")
    print(f"[schema_status] {result.schema_status}")
    print(f"[forbidden_column_status] {result.forbidden_column_status}")
    print(f"[downstream_l1h6_rerun_command] {result.downstream_l1h6_rerun_command}")
    print("[files_created]")
    for path in result.output_paths:
        print(f"- {rel(path)}")
    return 0 if result.status in {READY_STATUS, WAITING_STATUS, BLOCKED_SCHEMA_STATUS, BLOCKED_FORBIDDEN_STATUS, SNAPSHOT_FROZEN_PASS_STATUS} else 1


if __name__ == "__main__":
    raise SystemExit(main())
