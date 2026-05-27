#!/usr/bin/env python
"""Build the System A A-L1H.6 prospective evaluation harness.

Inputs:
    - configs/v11/systema_l1h6_prospective_eval_harness.yaml
    - Frozen A-L1H.5 status, hourly output contract, output schema,
      threshold-policy register, and station-caveat register.
    - Compact CSV/CSV.GZ/Parquet candidate snapshot tables under configured
      candidate paths and existing v11 output search roots.

Outputs:
    - a_l1h6_input_inventory.csv
    - a_l1h6_expected_input_schema.csv
    - a_l1h6_snapshot_detection_report.csv
    - a_l1h6_evaluation_plan.csv
    - a_l1h6_metric_schema.csv
    - a_l1h6_prospective_metrics.csv
    - a_l1h6_station_caveat_refresh.csv
    - a_l1h6_promotion_gate.csv
    - a_l1h6_report.md
    - A_L1H6_STATUS.md
    - docs/v11/OpenHeat_SystemA_L1H6_prospective_eval_harness_CN.md

Saved metrics:
    When a valid prospective snapshot is present, the harness writes ge31/ge33
    support, deterministic fixed_31 baseline metrics, optional P_ge31 policy
    metrics, Brier/ECE, high-tail MAE, expected-exceedance MAE, interval
    empirical coverage, and station-caveat refresh rows. When no valid snapshot
    exists, it writes WAITING_FOR_FORMAL_SNAPSHOT status and does not create
    synthetic metric values.

Scope guard:
    This harness does not train models, modify archive collectors, touch System
    B or SOLWEIG outputs, create station-adjusted WBGT, create local 100 m WBGT,
    create risk_score/hazard_score, create System A/B coupling output, or
    promote P_ge31 to an official warning probability.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import math
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - used only in lean runtimes.
    yaml = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]

WAITING_STATUS = "A_L1H6_WAITING_FOR_FORMAL_SNAPSHOT"
PASS_STATUS = "A_L1H6_PROSPECTIVE_EVAL_PASS"
WEAK_STATUS = "A_L1H6_PROSPECTIVE_EVAL_WEAK"
BLOCKED_SCHEMA_STATUS = "A_L1H6_BLOCKED_SCHEMA"
FAILED_STATUS = "FAILED"

P_GE31_WAITING = "P_GE31_REMAINS_OPTIONAL_WAITING"
P_GE31_PASS = "P_GE31_PROSPECTIVE_PASS"
P_GE31_WEAK = "P_GE31_PROSPECTIVE_WEAK"
P_GE31_NOT_PROMOTED = "P_GE31_NOT_PROMOTED"
P_GE33_EXPLORATORY = "P_GE33_REMAINS_EXPLORATORY"


@dataclass(frozen=True)
class TablePreview:
    """Schema and compact row preview for a candidate table."""

    path: Path
    rows: list[dict[str, Any]]
    columns: list[str]
    read_status: str
    error: str = ""


@dataclass(frozen=True)
class HarnessResult:
    """Headline result returned by the A-L1H.6 harness."""

    status: str
    snapshot_found: bool
    candidate_path: str
    n_rows: str
    n_ge31: str
    n_ge33: str
    p_ge31_promotion_gate_status: str
    ge33_status: str
    station_caveat_headline: str
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
                    if index < len(raw_lines) and raw_lines[index][0] > line_indent:
                        extra, index = parse_block(index, raw_lines[index][0])
                        if isinstance(extra, dict):
                            item_dict.update(extra)
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
    """Load the explicit A-L1H.6 YAML config."""
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
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


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


def markdown_cell(value: Any) -> str:
    """Escape a compact Markdown table cell."""
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ")


def markdown_table(rows: list[dict[str, Any]], columns: list[str], limit: int | None = None) -> str:
    """Render a compact Markdown table."""
    display_rows = rows if limit is None else rows[:limit]
    if not display_rows:
        return "_No rows available._"
    headers = columns
    body = [[markdown_cell(row.get(col, "")) for col in columns] for row in display_rows]
    widths = [len(header) for header in headers]
    for row in body:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def render(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(values)) + " |"

    separator = "| " + " | ".join("-" * width for width in widths) + " |"
    return "\n".join([render(headers), separator, *(render(row) for row in body)])


def to_float(value: Any) -> float | None:
    """Convert a value to float when possible."""
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    text = str(value).strip()
    if text in {"", "NA", "NaN", "nan", "None", "null"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return number


def safe_div(numerator: float, denominator: float) -> float | None:
    """Return numerator / denominator, or None when undefined."""
    if denominator == 0:
        return None
    return numerator / denominator


def fmt(value: Any, digits: int = 6) -> str:
    """Format numeric output compactly while leaving missing values blank."""
    number = to_float(value)
    if number is None:
        return ""
    return f"{number:.{digits}f}"


def is_compact_table(path: Path) -> bool:
    """Return whether a path has a compact table suffix supported here."""
    suffixes = [suffix.lower() for suffix in path.suffixes]
    return path.suffix.lower() in {".csv", ".parquet"} or suffixes[-2:] == [".csv", ".gz"]


def path_text(path: Path) -> str:
    """Return normalized lowercase project-relative path text."""
    return rel(path).replace("\\", "/").lower()


def should_skip_path(path: Path, config: dict[str, Any]) -> bool:
    """Skip raw, live, System B, SOLWEIG, and large-file paths by pattern."""
    text = path_text(path)
    patterns = [str(pattern).replace("\\", "/").lower() for pattern in config["analysis"].get("skip_path_patterns", [])]
    return any(pattern in text for pattern in patterns)


def is_under(path: Path, parent: Path) -> bool:
    """Return whether path is under parent after resolution."""
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def source_group_for_path(path: Path, config: dict[str, Any]) -> str:
    """Classify a discovered compact table by configured search source."""
    candidate_roots = [resolve_path(raw) for raw in config["inputs"].get("candidate_prospective_paths", [])]
    if any(is_under(path, root) for root in candidate_roots):
        return "configured_candidate_path"
    text = path_text(path)
    formal_tokens = ("v11_archive_formal_beta", "prospective_snapshot", "formal_snapshot", "v11_beta_formal")
    if any(token in text for token in formal_tokens):
        return "formal_like_existing_output"
    return "existing_output_search"


def is_formal_candidate(path: Path, config: dict[str, Any]) -> bool:
    """Return whether a compact file should be treated as a formal snapshot candidate."""
    return source_group_for_path(path, config) in {"configured_candidate_path", "formal_like_existing_output"}


def discover_compact_tables(config: dict[str, Any]) -> list[Path]:
    """Discover compact CSV/CSV.GZ/Parquet tables without reading raw archives."""
    roots = [resolve_path(raw) for raw in config["inputs"].get("candidate_prospective_paths", [])]
    roots.extend(resolve_path(raw) for raw in config["inputs"].get("existing_output_search_roots", []))
    harness_output_dir = resolve_path(config["outputs"]["output_dir"])
    max_bytes = int(config["analysis"].get("compact_file_max_bytes", 5_000_000))
    seen: set[Path] = set()
    tables: list[Path] = []
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            if is_under(path, harness_output_dir):
                continue
            if not is_compact_table(path):
                continue
            if should_skip_path(path, config):
                continue
            if path.stat().st_size > max_bytes:
                continue
            text = path_text(path)
            if "prospective" not in text and "formal" not in text and "snapshot" not in text and source_group_for_path(path, config) == "existing_output_search":
                continue
            tables.append(path)
    return sorted(tables, key=lambda item: rel(item))


def read_table_preview(path: Path) -> TablePreview:
    """Read a compact table for schema and metric evaluation."""
    try:
        if path.suffix.lower() == ".parquet":
            try:
                import pandas as pd  # type: ignore[import-not-found]
            except ModuleNotFoundError:
                return TablePreview(path=path, rows=[], columns=[], read_status="UNREAD_PARQUET_PANDAS_MISSING")
            frame = pd.read_parquet(path)
            rows = frame.to_dict(orient="records")
            return TablePreview(path=path, rows=rows, columns=[str(column) for column in frame.columns], read_status="READ_OK")
        opener = gzip.open if [suffix.lower() for suffix in path.suffixes][-2:] == [".csv", ".gz"] else open
        with opener(path, "rt", encoding="utf-8-sig", errors="replace", newline="") as handle:  # type: ignore[arg-type]
            reader = csv.DictReader(handle)
            rows = [dict(row) for row in reader]
            columns = [str(column) for column in (reader.fieldnames or [])]
            return TablePreview(path=path, rows=rows, columns=columns, read_status="READ_OK")
    except Exception as exc:  # pragma: no cover - defensive for future snapshots.
        return TablePreview(path=path, rows=[], columns=[], read_status="READ_FAILED", error=str(exc))


def is_prospective_value(value: Any) -> bool:
    """Identify prospective rows without requiring a single exact label."""
    text = str(value).strip().lower()
    return "prospective" in text or text in {"future", "forecast", "formal_prospective"}


def non_null_count(rows: list[dict[str, Any]], column: str) -> int:
    """Count non-null, non-empty values in a column."""
    return sum(1 for row in rows if str(row.get(column, "")).strip() not in {"", "NA", "NaN", "nan", "None", "null"})


def binary_counts(observed: list[bool], predicted: list[bool]) -> dict[str, int]:
    """Return TP/FP/FN/TN counts for a binary classifier."""
    tp = sum(1 for obs, pred in zip(observed, predicted) if obs and pred)
    fp = sum(1 for obs, pred in zip(observed, predicted) if not obs and pred)
    fn = sum(1 for obs, pred in zip(observed, predicted) if obs and not pred)
    tn = sum(1 for obs, pred in zip(observed, predicted) if not obs and not pred)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def classification_metrics(counts: dict[str, int]) -> dict[str, float | None]:
    """Return recall, precision, miss rate, false-alarm ratio, and CSI."""
    tp = float(counts["tp"])
    fp = float(counts["fp"])
    fn = float(counts["fn"])
    return {
        "recall": safe_div(tp, tp + fn),
        "precision": safe_div(tp, tp + fp),
        "miss_rate": safe_div(fn, tp + fn),
        "false_alarm_ratio": safe_div(fp, tp + fp),
        "csi": safe_div(tp, tp + fp + fn),
    }


def brier_score(probabilities: list[float], observed: list[bool]) -> float | None:
    """Compute Brier score for binary probabilities."""
    if not probabilities:
        return None
    return sum((prob - float(obs)) ** 2 for prob, obs in zip(probabilities, observed)) / len(probabilities)


def expected_calibration_error(probabilities: list[float], observed: list[bool], bins: int) -> float | None:
    """Compute fixed-width expected calibration error."""
    if not probabilities:
        return None
    total = len(probabilities)
    ece = 0.0
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        in_bin = [
            (prob, obs)
            for prob, obs in zip(probabilities, observed)
            if (lower <= prob < upper) or (index == bins - 1 and lower <= prob <= upper)
        ]
        if not in_bin:
            continue
        avg_prob = sum(prob for prob, _ in in_bin) / len(in_bin)
        event_rate = sum(float(obs) for _, obs in in_bin) / len(in_bin)
        ece += (len(in_bin) / total) * abs(avg_prob - event_rate)
    return ece


def mean_absolute(values: Iterable[float]) -> float | None:
    """Compute mean absolute value for an iterable."""
    items = [abs(value) for value in values]
    if not items:
        return None
    return sum(items) / len(items)


def metric_row(
    metric_name: str,
    metric_group: str,
    value: Any,
    numerator: Any = "",
    denominator: Any = "",
    operating_point: str = "",
    applies_to: str = "prospective_rows",
    status: str = "EVALUATED",
    notes: str = "",
) -> dict[str, Any]:
    """Build one metric output row."""
    return {
        "metric_name": metric_name,
        "metric_group": metric_group,
        "value": fmt(value) if isinstance(value, float) or value is None else value,
        "numerator": numerator,
        "denominator": denominator,
        "operating_point": operating_point,
        "applies_to": applies_to,
        "status": status,
        "notes": notes,
    }


def make_input_inventory(config: dict[str, Any], compact_tables: list[Path]) -> list[dict[str, Any]]:
    """Create the compact input inventory rows."""
    rows: list[dict[str, Any]] = []
    for input_id, raw_path in config["inputs"].items():
        if isinstance(raw_path, str):
            path = resolve_path(raw_path)
            rows.append(
                {
                    "input_id": input_id,
                    "input_role": "configured_input",
                    "path": rel(path),
                    "exists": path.exists(),
                    "file_type": path.suffix.lower() if path.suffix else "directory",
                    "bytes": path.stat().st_size if path.exists() and path.is_file() else "",
                    "source_group": "frozen_contract_or_prior_evidence",
                    "searched": "yes" if path.exists() else "no",
                    "candidate_table": "no",
                    "notes": "Configured A-L1H.5 dependency or optional prior compact evidence.",
                }
            )
        elif isinstance(raw_path, list):
            for index, item in enumerate(raw_path, start=1):
                path = resolve_path(str(item))
                rows.append(
                    {
                        "input_id": f"{input_id}_{index}",
                        "input_role": "configured_search_root",
                        "path": rel(path),
                        "exists": path.exists(),
                        "file_type": "directory",
                        "bytes": "",
                        "source_group": "candidate_path" if input_id == "candidate_prospective_paths" else "existing_output_search_root",
                        "searched": "yes" if path.exists() and path.is_dir() else "no",
                        "candidate_table": "directory",
                        "notes": "Compact CSV/CSV.GZ/Parquet files only; raw archives and large live forecasts skipped.",
                    }
                )
    for path in compact_tables:
        rows.append(
            {
                "input_id": path.stem,
                "input_role": "discovered_compact_table",
                "path": rel(path),
                "exists": True,
                "file_type": "".join(path.suffixes).lower(),
                "bytes": path.stat().st_size,
                "source_group": source_group_for_path(path, config),
                "searched": "yes",
                "candidate_table": "yes" if is_formal_candidate(path, config) else "inventory_only",
                "notes": "Schema inspected only if compact and not skipped by guard patterns.",
            }
        )
    return rows


def make_expected_input_schema(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Create the explicit required/optional future input schema table."""
    descriptions = {
        "timestamp_sgt": "SGT timestamp for the hourly row.",
        "timestamp_utc": "UTC timestamp matching timestamp_sgt.",
        "station_id": "Official station identifier for prospective evaluation grouping.",
        "official_wbgt_c": "Observed official WBGT in Celsius used as the prospective evaluation target.",
        "wbgt_a_c": "Frozen System A deterministic WBGT_A primary output.",
        "wbgt_a_model_id": "Frozen deterministic model identifier.",
        "wbgt_a_version": "Frozen contract/model artifact version.",
        "is_retrospective_or_prospective": "Row provenance label that separates retrospective and prospective rows.",
        "quality_flag": "Compact quality/provenance flag for formal snapshot rows.",
        "p_ge31_optional": "Optional diagnostic probability for official WBGT >=31 C.",
        "p_ge31_model_id_optional": "Optional model id for p_ge31_optional.",
        "p_ge31_threshold_policy_optional": "Optional policy id for interpreting p_ge31_optional.",
        "p_ge33_optional": "Exploratory optional probability for official WBGT >=33 C.",
        "expected_exceedance_ge31_optional": "Optional expected exceedance magnitude above 31 C.",
        "prediction_interval_low_optional": "Optional lower diagnostic interval bound for wbgt_a_c.",
        "prediction_interval_high_optional": "Optional upper diagnostic interval bound for wbgt_a_c.",
        "lead_time_hours_optional": "Optional lead time when the prospective row has forecast lead-time context.",
    }
    types = {
        "timestamp_sgt": "datetime_iso8601",
        "timestamp_utc": "datetime_iso8601",
        "station_id": "string",
        "official_wbgt_c": "float_celsius",
        "wbgt_a_c": "float_celsius",
        "wbgt_a_model_id": "string",
        "wbgt_a_version": "string",
        "is_retrospective_or_prospective": "categorical",
        "quality_flag": "string",
        "p_ge31_optional": "float_0_1",
        "p_ge31_model_id_optional": "string",
        "p_ge31_threshold_policy_optional": "string",
        "p_ge33_optional": "float_0_1",
        "expected_exceedance_ge31_optional": "float_celsius",
        "prediction_interval_low_optional": "float_celsius",
        "prediction_interval_high_optional": "float_celsius",
        "lead_time_hours_optional": "integer_or_float",
    }
    forbidden = {
        "timestamp_sgt": "timezone-free time key",
        "timestamp_utc": "ambiguous cross-system timestamp",
        "station_id": "station correction layer",
        "official_wbgt_c": "training target for new models in this lane",
        "wbgt_a_c": "local 100 m WBGT or official warning",
        "wbgt_a_model_id": "hidden model substitution",
        "wbgt_a_version": "unversioned prospective comparison",
        "is_retrospective_or_prospective": "mixing retrospective and prospective rows",
        "quality_flag": "silent quality failures",
        "p_ge31_optional": "official warning probability",
        "p_ge31_model_id_optional": "unversioned probability",
        "p_ge31_threshold_policy_optional": "official public warning threshold",
        "p_ge33_optional": "promoted severe warning probability",
        "expected_exceedance_ge31_optional": "corrected WBGT value",
        "prediction_interval_low_optional": "guaranteed operational interval",
        "prediction_interval_high_optional": "guaranteed operational interval",
        "lead_time_hours_optional": "claim of forecast skill without validation",
    }
    validation = {
        "timestamp_sgt": "column present; non-null in prospective rows; parseable as timestamp in downstream review",
        "timestamp_utc": "column present; non-null in prospective rows; matches timestamp_sgt hour",
        "station_id": "column present; non-null; grouped station diagnostics can be refreshed",
        "official_wbgt_c": "column present; numeric; defines ge31/ge33 observed events",
        "wbgt_a_c": "column present; numeric; fixed_31 baseline can be evaluated",
        "wbgt_a_model_id": "column present; non-null frozen model metadata",
        "wbgt_a_version": "column present; non-null frozen version metadata",
        "is_retrospective_or_prospective": "column present; at least one prospective row for evaluation",
        "quality_flag": "column present; non-null compact provenance flag",
        "p_ge31_optional": "if present, numeric within [0, 1]; metadata columns should be populated",
        "p_ge31_model_id_optional": "if p_ge31_optional present, non-null model id expected",
        "p_ge31_threshold_policy_optional": "if p_ge31_optional present, non-null policy id expected",
        "p_ge33_optional": "if present, numeric within [0, 1]; remains exploratory",
        "expected_exceedance_ge31_optional": "if present, numeric expected exceedance against max(official_wbgt_c - 31, 0)",
        "prediction_interval_low_optional": "if present with high bound, numeric and <= high bound",
        "prediction_interval_high_optional": "if present with low bound, numeric and >= low bound",
        "lead_time_hours_optional": "if forecast lead time exists, numeric lead time for stratified review",
    }
    rows: list[dict[str, Any]] = []
    for column in config["schema"]["required_columns"]:
        rows.append(
            {
                "column_name": column,
                "required_or_optional": "required",
                "type": types[column],
                "allowed_null": "no",
                "description": descriptions[column],
                "forbidden_interpretation": forbidden[column],
                "validation_check": validation[column],
            }
        )
    for column in config["schema"]["optional_columns"]:
        rows.append(
            {
                "column_name": column,
                "required_or_optional": "optional",
                "type": types[column],
                "allowed_null": "yes",
                "description": descriptions[column],
                "forbidden_interpretation": forbidden[column],
                "validation_check": validation[column],
            }
        )
    return rows


def detection_row_for_table(config: dict[str, Any], preview: TablePreview) -> dict[str, Any]:
    """Inspect a compact table for prospective snapshot eligibility."""
    required = list(config["schema"]["required_columns"])
    optional = list(config["schema"]["optional_columns"])
    forbidden = list(config["schema"]["forbidden_columns"])
    columns = set(preview.columns)
    missing_required = [column for column in required if column not in columns]
    optional_present = [column for column in optional if column in columns]
    forbidden_present = [column for column in forbidden if column in columns]
    prospective_rows = [
        row
        for row in preview.rows
        if "is_retrospective_or_prospective" in row and is_prospective_value(row.get("is_retrospective_or_prospective"))
    ]
    official_values = [to_float(row.get("official_wbgt_c")) for row in prospective_rows]
    official_values = [value for value in official_values if value is not None]
    n_ge31 = sum(1 for value in official_values if value >= 31.0)
    n_ge33 = sum(1 for value in official_values if value >= 33.0)
    lead_time_present = "lead_time_hours_optional" in columns and non_null_count(prospective_rows, "lead_time_hours_optional") > 0
    model_metadata = (
        "wbgt_a_model_id" in columns
        and "wbgt_a_version" in columns
        and non_null_count(prospective_rows, "wbgt_a_model_id") > 0
        and non_null_count(prospective_rows, "wbgt_a_version") > 0
    )
    p_ge31_metadata = (
        "p_ge31_optional" not in columns
        or (
            "p_ge31_model_id_optional" in columns
            and "p_ge31_threshold_policy_optional" in columns
            and non_null_count(prospective_rows, "p_ge31_model_id_optional") > 0
            and non_null_count(prospective_rows, "p_ge31_threshold_policy_optional") > 0
        )
    )
    if preview.read_status != "READ_OK":
        status = preview.read_status
        reason = preview.error or "Table could not be read for schema inspection."
    elif missing_required or forbidden_present:
        status = "SCHEMA_INVALID"
        reason = f"missing_required={';'.join(missing_required) or 'none'}; forbidden_present={';'.join(forbidden_present) or 'none'}"
    elif not prospective_rows:
        status = "NO_PROSPECTIVE_ROWS"
        reason = "Required schema is present but no row is labeled prospective."
    else:
        status = "VALID_FOR_EVALUATION"
        reason = "Required schema present, forbidden columns absent, and prospective rows found."
    return {
        "path": rel(preview.path),
        "source_group": source_group_for_path(preview.path, config),
        "candidate_table": "yes" if is_formal_candidate(preview.path, config) else "inventory_only",
        "read_status": preview.read_status,
        "detection_status": status,
        "reason": reason,
        "n_total_rows": len(preview.rows) if preview.read_status == "READ_OK" else "",
        "n_prospective_rows": len(prospective_rows) if preview.read_status == "READ_OK" else "",
        "n_ge31": n_ge31 if preview.read_status == "READ_OK" else "",
        "n_ge33": n_ge33 if preview.read_status == "READ_OK" else "",
        "required_columns_present": "no" if missing_required else "yes",
        "missing_required_columns": ";".join(missing_required),
        "forbidden_columns_present": ";".join(forbidden_present),
        "optional_columns_present": ";".join(optional_present),
        "lead_time_hours_optional_present": "yes" if lead_time_present else "no",
        "frozen_model_version_metadata": "yes" if model_metadata else "no",
        "p_ge31_metadata_status": "ok_or_not_present" if p_ge31_metadata else "missing_optional_probability_metadata",
    }


def choose_snapshot(config: dict[str, Any], previews: list[TablePreview]) -> tuple[TablePreview | None, list[dict[str, Any]], str]:
    """Choose the best formal candidate snapshot, or return why evaluation waits/blocks."""
    detection_rows = [detection_row_for_table(config, preview) for preview in previews]
    formal_rows = [row for row in detection_rows if row["candidate_table"] == "yes"]
    valid_paths = {row["path"] for row in formal_rows if row["detection_status"] == "VALID_FOR_EVALUATION"}
    valid_previews = [preview for preview in previews if rel(preview.path) in valid_paths]
    if valid_previews:
        valid_previews.sort(
            key=lambda preview: sum(
                1
                for row in preview.rows
                if is_prospective_value(row.get("is_retrospective_or_prospective"))
            ),
            reverse=True,
        )
        return valid_previews[0], detection_rows, "VALID_FORMAL_SNAPSHOT_FOUND"
    if any(row["detection_status"] == "SCHEMA_INVALID" for row in formal_rows):
        return None, detection_rows, "FORMAL_CANDIDATE_SCHEMA_INVALID"
    return None, detection_rows, "WAITING_FOR_FORMAL_SNAPSHOT"


def candidate_root_detection_rows(config: dict[str, Any], compact_tables: list[Path]) -> list[dict[str, Any]]:
    """Create explicit detection rows for missing or empty configured roots."""
    rows: list[dict[str, Any]] = []
    for raw in config["inputs"].get("candidate_prospective_paths", []):
        root = resolve_path(str(raw))
        root_tables = [path for path in compact_tables if is_under(path, root)]
        if not root.exists():
            status = "MISSING_CONFIGURED_CANDIDATE_PATH"
            reason = "Configured formal snapshot path does not exist yet."
        elif not root.is_dir():
            status = "CONFIGURED_CANDIDATE_PATH_NOT_DIRECTORY"
            reason = "Configured formal snapshot path is not a directory."
        elif not root_tables:
            status = "NO_COMPACT_TABLES_IN_CONFIGURED_CANDIDATE_PATH"
            reason = "Directory exists but contains no compact CSV/CSV.GZ/Parquet candidate table under size and guard filters."
        else:
            continue
        rows.append(
            {
                "path": rel(root),
                "source_group": "configured_candidate_path",
                "candidate_table": "directory",
                "read_status": "NOT_READ_DIRECTORY",
                "detection_status": status,
                "reason": reason,
                "n_total_rows": "",
                "n_prospective_rows": "",
                "n_ge31": "",
                "n_ge33": "",
                "required_columns_present": "",
                "missing_required_columns": "",
                "forbidden_columns_present": "",
                "optional_columns_present": "",
                "lead_time_hours_optional_present": "",
                "frozen_model_version_metadata": "",
                "p_ge31_metadata_status": "",
            }
        )
    return rows


def load_thresholds(config: dict[str, Any]) -> dict[str, float]:
    """Load frozen A-L1H.5 threshold policies."""
    rows = read_csv_rows(resolve_path(config["inputs"]["threshold_policy_register_path"]))
    thresholds: dict[str, float] = {}
    for row in rows:
        policy_id = str(row.get("policy_id", "")).strip()
        threshold = to_float(row.get("threshold"))
        if policy_id and threshold is not None:
            thresholds[policy_id] = threshold
    thresholds.setdefault("fixed_31", float(config["analysis"]["fixed_31_threshold"]))
    return thresholds


def prospective_subset(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return rows labeled prospective."""
    return [row for row in rows if is_prospective_value(row.get("is_retrospective_or_prospective"))]


def observed_pairs(rows: list[dict[str, Any]]) -> list[tuple[dict[str, Any], float, float]]:
    """Return rows with numeric official WBGT and wbgt_a_c."""
    pairs: list[tuple[dict[str, Any], float, float]] = []
    for row in rows:
        official = to_float(row.get("official_wbgt_c"))
        predicted = to_float(row.get("wbgt_a_c"))
        if official is None or predicted is None:
            continue
        pairs.append((row, official, predicted))
    return pairs


def add_classification_metric_rows(
    rows: list[dict[str, Any]],
    prefix: str,
    metric_group: str,
    counts: dict[str, int],
    operating_point: str,
    notes: str,
) -> None:
    """Append standard binary-classification metrics to output rows."""
    metrics = classification_metrics(counts)
    rows.extend(
        [
            metric_row(f"{prefix}_tp", metric_group, counts["tp"], operating_point=operating_point, notes=notes),
            metric_row(f"{prefix}_fp", metric_group, counts["fp"], operating_point=operating_point, notes=notes),
            metric_row(f"{prefix}_fn", metric_group, counts["fn"], operating_point=operating_point, notes=notes),
            metric_row(f"{prefix}_tn", metric_group, counts["tn"], operating_point=operating_point, notes=notes),
            metric_row(f"{prefix}_recall_ge31", metric_group, metrics["recall"], counts["tp"], counts["tp"] + counts["fn"], operating_point, notes=notes),
            metric_row(f"{prefix}_precision_ge31", metric_group, metrics["precision"], counts["tp"], counts["tp"] + counts["fp"], operating_point, notes=notes),
            metric_row(f"{prefix}_miss_rate_ge31", metric_group, metrics["miss_rate"], counts["fn"], counts["tp"] + counts["fn"], operating_point, notes=notes),
            metric_row(f"{prefix}_false_alarm_ratio_ge31", metric_group, metrics["false_alarm_ratio"], counts["fp"], counts["tp"] + counts["fp"], operating_point, notes=notes),
            metric_row(f"{prefix}_CSI_ge31", metric_group, metrics["csi"], counts["tp"], counts["tp"] + counts["fp"] + counts["fn"], operating_point, notes=notes),
        ]
    )


def evaluate_snapshot(config: dict[str, Any], preview: TablePreview) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Evaluate prospective metrics for a valid formal snapshot preview."""
    thresholds = load_thresholds(config)
    rows = prospective_subset(preview.rows)
    pairs = observed_pairs(rows)
    official = [item[1] for item in pairs]
    wbgt_a = [item[2] for item in pairs]
    observed_ge31 = [value >= 31.0 for value in official]
    observed_ge33 = [value >= 33.0 for value in official]
    fixed_pred = [value >= thresholds["fixed_31"] for value in wbgt_a]
    fixed_counts = binary_counts(observed_ge31, fixed_pred)
    fixed_metrics = classification_metrics(fixed_counts)
    metric_rows: list[dict[str, Any]] = [
        metric_row("n_rows", "support", len(rows), denominator=len(rows), notes="Prospective rows labeled in formal snapshot."),
        metric_row("n_numeric_rows", "support", len(pairs), denominator=len(rows), notes="Prospective rows with numeric official_wbgt_c and wbgt_a_c."),
        metric_row("n_stations", "support", len({str(row.get("station_id", "")) for row, _, _ in pairs if str(row.get("station_id", "")).strip()}), notes="Unique stations in numeric prospective rows."),
        metric_row("n_ge31", "support", sum(observed_ge31), denominator=len(pairs), notes="Official WBGT >=31 C events."),
        metric_row("n_ge33", "support", sum(observed_ge33), denominator=len(pairs), notes="Official WBGT >=33 C events."),
    ]
    add_classification_metric_rows(
        metric_rows,
        "fixed31",
        "deterministic_fixed_31_baseline",
        fixed_counts,
        "fixed_31",
        "Deterministic baseline from wbgt_a_c >=31 C.",
    )
    high_tail_mae = mean_absolute(pred - obs for obs, pred in zip(official, wbgt_a) if obs >= 31.0)
    metric_rows.append(metric_row("high_tail_MAE_obs_ge31", "deterministic_fixed_31_baseline", high_tail_mae, denominator=sum(observed_ge31), notes="MAE of wbgt_a_c on observed ge31 rows."))

    p_values: list[float] = []
    p_observed: list[bool] = []
    has_p_ge31 = "p_ge31_optional" in preview.columns
    if has_p_ge31:
        for row, obs, _ in pairs:
            probability = to_float(row.get("p_ge31_optional"))
            if probability is None or probability < 0.0 or probability > 1.0:
                continue
            p_values.append(probability)
            p_observed.append(obs >= 31.0)
        metric_rows.append(metric_row("Brier_p_ge31_optional", "optional_p_ge31_calibration", brier_score(p_values, p_observed), denominator=len(p_values), notes="Only evaluated for rows with valid p_ge31_optional in [0, 1]."))
        metric_rows.append(metric_row("ECE_p_ge31_optional", "optional_p_ge31_calibration", expected_calibration_error(p_values, p_observed, int(config["analysis"].get("probability_ece_bins", 10))), denominator=len(p_values), notes="Fixed-width ECE; internal diagnostic only."))
        for policy_id, threshold in thresholds.items():
            if policy_id == "fixed_31":
                continue
            policy_pred = [probability >= threshold for probability in p_values]
            counts = binary_counts(p_observed, policy_pred)
            add_classification_metric_rows(
                metric_rows,
                f"p_ge31_{policy_id}",
                "optional_p_ge31_operating_policy",
                counts,
                policy_id,
                "Frozen A-L1H.5 policy applied prospectively; not an official warning threshold.",
            )
    else:
        metric_rows.append(metric_row("Brier_p_ge31_optional", "optional_p_ge31_calibration", "", status="NOT_AVAILABLE", notes="p_ge31_optional column absent."))
        metric_rows.append(metric_row("ECE_p_ge31_optional", "optional_p_ge31_calibration", "", status="NOT_AVAILABLE", notes="p_ge31_optional column absent."))

    if "expected_exceedance_ge31_optional" in preview.columns:
        errors: list[float] = []
        for row, obs, _ in pairs:
            predicted_exceedance = to_float(row.get("expected_exceedance_ge31_optional"))
            if predicted_exceedance is None:
                continue
            observed_exceedance = max(obs - 31.0, 0.0)
            errors.append(predicted_exceedance - observed_exceedance)
        metric_rows.append(metric_row("expected_exceedance_MAE", "optional_expected_exceedance", mean_absolute(errors), denominator=len(errors), notes="MAE against max(official_wbgt_c - 31, 0)."))
    else:
        metric_rows.append(metric_row("expected_exceedance_MAE", "optional_expected_exceedance", "", status="NOT_AVAILABLE", notes="expected_exceedance_ge31_optional column absent."))

    if "prediction_interval_low_optional" in preview.columns and "prediction_interval_high_optional" in preview.columns:
        covered = 0
        usable = 0
        invalid_bounds = 0
        for row, obs, _ in pairs:
            low = to_float(row.get("prediction_interval_low_optional"))
            high = to_float(row.get("prediction_interval_high_optional"))
            if low is None or high is None:
                continue
            if low > high:
                invalid_bounds += 1
                continue
            usable += 1
            covered += int(low <= obs <= high)
        metric_rows.append(metric_row("interval_empirical_coverage", "optional_interval_diagnostic", safe_div(covered, usable), covered, usable, notes=f"Invalid interval bounds skipped: {invalid_bounds}."))
    else:
        metric_rows.append(metric_row("interval_empirical_coverage", "optional_interval_diagnostic", "", status="NOT_AVAILABLE", notes="Interval columns absent."))

    station_rows = evaluate_station_caveats(config, pairs, thresholds)
    summary = {
        "n_rows": len(rows),
        "n_numeric_rows": len(pairs),
        "n_ge31": sum(observed_ge31),
        "n_ge33": sum(observed_ge33),
        "fixed_counts": fixed_counts,
        "fixed_metrics": fixed_metrics,
        "has_p_ge31": has_p_ge31,
        "p_values_count": len(p_values),
        "p_brier": brier_score(p_values, p_observed) if has_p_ge31 else None,
        "p_ece": expected_calibration_error(p_values, p_observed, int(config["analysis"].get("probability_ece_bins", 10))) if has_p_ge31 else None,
        "best_f1_metrics": None,
        "station_failed": any(row.get("caveat_status") == "FAILED_FOCUS_CAVEAT" for row in station_rows),
        "station_caveat_headline": build_station_headline(station_rows),
    }
    best_threshold = thresholds.get(str(config["analysis"].get("p_ge31_reference_policy_id", "best_F1")))
    if has_p_ge31 and best_threshold is not None and p_values:
        counts = binary_counts(p_observed, [probability >= best_threshold for probability in p_values])
        summary["best_f1_metrics"] = classification_metrics(counts)
        summary["best_f1_counts"] = counts
    return metric_rows, station_rows, summary


def evaluate_station_caveats(
    config: dict[str, Any],
    pairs: list[tuple[dict[str, Any], float, float]],
    thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    """Refresh station caveats for S142/S139 and all stations."""
    best_policy = str(config["analysis"].get("p_ge31_reference_policy_id", "best_F1"))
    best_threshold = thresholds.get(best_policy)
    station_ids = sorted({str(row.get("station_id", "")).strip() for row, _, _ in pairs if str(row.get("station_id", "")).strip()})
    station_ids = ["ALL", *station_ids]
    focus = set(str(station) for station in config["analysis"].get("focus_stations", []))
    rows: list[dict[str, Any]] = []
    for station_id in station_ids:
        subset = pairs if station_id == "ALL" else [item for item in pairs if str(item[0].get("station_id", "")).strip() == station_id]
        observed = [obs >= 31.0 for _, obs, _ in subset]
        fixed_pred = [pred >= thresholds["fixed_31"] for _, _, pred in subset]
        fixed_counts = binary_counts(observed, fixed_pred)
        fixed_metrics = classification_metrics(fixed_counts)
        p_counts: dict[str, int] | None = None
        p_metrics: dict[str, float | None] | None = None
        if best_threshold is not None:
            p_pairs = [(row, obs) for row, obs, _ in subset if to_float(row.get("p_ge31_optional")) is not None]
            if p_pairs:
                p_observed = [obs >= 31.0 for _, obs in p_pairs]
                p_pred = [(to_float(row.get("p_ge31_optional")) or 0.0) >= best_threshold for row, _ in p_pairs]
                p_counts = binary_counts(p_observed, p_pred)
                p_metrics = classification_metrics(p_counts)
        n_ge31 = sum(observed)
        caveat_status = "ROUTINE_MONITORING"
        if station_id in focus:
            caveat_status = "FOCUS_MONITORING"
            if n_ge31 >= 5 and p_metrics is not None and (p_metrics["miss_rate"] or 0.0) > 0.50:
                caveat_status = "FAILED_FOCUS_CAVEAT"
        if n_ge31 == 0:
            caveat_status = "LOW_EVENT_SUPPORT"
        headline = (
            f"{station_id}: n={len(subset)}; n_ge31={n_ge31}; "
            f"fixed31_recall={fmt(fixed_metrics['recall'], 3) or 'NA'}; "
            f"p_ge31_{best_policy}_recall={fmt(p_metrics['recall'], 3) if p_metrics else 'NA'}"
        )
        rows.append(
            {
                "station_id": station_id,
                "n_rows": len(subset),
                "n_ge31": n_ge31,
                "n_ge33": sum(1 for _, obs, _ in subset if obs >= 33.0),
                "fixed31_recall_ge31": fmt(fixed_metrics["recall"]),
                "fixed31_miss_rate_ge31": fmt(fixed_metrics["miss_rate"]),
                "fixed31_false_alarm_ratio_ge31": fmt(fixed_metrics["false_alarm_ratio"]),
                f"p_ge31_{best_policy}_recall_ge31": fmt(p_metrics["recall"]) if p_metrics else "",
                f"p_ge31_{best_policy}_miss_rate_ge31": fmt(p_metrics["miss_rate"]) if p_metrics else "",
                f"p_ge31_{best_policy}_false_alarm_ratio_ge31": fmt(p_metrics["false_alarm_ratio"]) if p_metrics else "",
                "caveat_status": caveat_status,
                "headline": headline,
                "not_station_correction": "yes",
            }
        )
    return rows


def build_station_headline(station_rows: list[dict[str, Any]]) -> str:
    """Build a concise station-caveat headline."""
    if not station_rows:
        return "Station caveat refresh waiting for formal snapshot."
    focus_rows = [row for row in station_rows if row.get("station_id") in {"S142", "S139"}]
    if not focus_rows:
        focus_rows = [row for row in station_rows if row.get("station_id") == "ALL"]
    failed = [row for row in station_rows if row.get("caveat_status") == "FAILED_FOCUS_CAVEAT"]
    prefix = "focus caveat failed" if failed else "station caveats refreshed"
    return f"{prefix}: " + " | ".join(str(row.get("headline", "")) for row in focus_rows)


def determine_promotion_gate(config: dict[str, Any], snapshot: TablePreview | None, detection_reason: str, summary: dict[str, Any] | None) -> tuple[list[dict[str, Any]], str, str, str]:
    """Apply A-L1H.6 promotion-gate logic without promoting official warning use."""
    min_rows = int(config["analysis"]["minimum_prospective_rows"])
    min_ge31 = int(config["analysis"]["minimum_ge31_events"])
    min_ge33 = int(config["analysis"]["minimum_ge33_events_for_promotion"])
    if snapshot is None:
        if detection_reason == "FORMAL_CANDIDATE_SCHEMA_INVALID":
            p_status = P_GE31_NOT_PROMOTED
            support_status = "BLOCKED_SCHEMA"
            next_action = "Fix candidate snapshot schema to match the frozen A-L1H.5 contract before evaluation."
        else:
            p_status = P_GE31_WAITING
            support_status = "WAITING_FOR_FORMAL_SNAPSHOT"
            next_action = "Freeze a formal prospective snapshot with required schema and prospective rows."
        ge33_status = P_GE33_EXPLORATORY
        rows = [
            {
                "gate_id": "p_ge31_optional",
                "status": p_status,
                "support_status": support_status,
                "evidence_summary": "No valid formal prospective snapshot evaluated.",
                "pass_condition": "Requires prospective support, improved recall/miss behavior vs fixed_31, controlled false alarms, stable Brier/ECE, and station caveats not failed.",
                "forbidden_interpretation": "official warning probability",
                "next_action": next_action,
            },
            {
                "gate_id": "p_ge33_optional",
                "status": ge33_status,
                "support_status": support_status,
                "evidence_summary": "No valid formal prospective snapshot evaluated.",
                "pass_condition": f"Requires >= {min_ge33} ge33 events plus explicit calibration evidence.",
                "forbidden_interpretation": "promoted severe warning probability",
                "next_action": "Keep p_ge33 exploratory.",
            },
        ]
        return rows, p_status, ge33_status, "Station caveat refresh waiting for formal snapshot."

    assert summary is not None
    support_ok = summary["n_rows"] >= min_rows and summary["n_ge31"] >= min_ge31
    ge33_status = P_GE33_EXPLORATORY
    if summary["n_ge33"] >= min_ge33:
        ge33_status = "P_GE33_SUPPORT_PRESENT_EXPLICIT_CALIBRATION_REVIEW_REQUIRED"
    best = summary.get("best_f1_metrics")
    fixed = summary["fixed_metrics"]
    if not support_ok:
        p_status = P_GE31_NOT_PROMOTED
        support_status = "INSUFFICIENT_SUPPORT"
    elif not summary.get("has_p_ge31") or best is None:
        p_status = P_GE31_NOT_PROMOTED
        support_status = "P_GE31_NOT_AVAILABLE"
    else:
        recall_gain = (best.get("recall") or 0.0) - (fixed.get("recall") or 0.0)
        precision_drop = (fixed.get("precision") or 0.0) - (best.get("precision") or 0.0)
        false_alarm = best.get("false_alarm_ratio")
        brier = summary.get("p_brier")
        ece = summary.get("p_ece")
        metrics_ok = (
            recall_gain >= float(config["analysis"]["p_ge31_min_recall_improvement"])
            and precision_drop <= float(config["analysis"]["p_ge31_max_precision_drop"])
            and false_alarm is not None
            and false_alarm <= float(config["analysis"]["p_ge31_max_false_alarm_ratio"])
            and brier is not None
            and brier <= float(config["analysis"]["p_ge31_max_brier"])
            and ece is not None
            and ece <= float(config["analysis"]["p_ge31_max_ece"])
        )
        if metrics_ok and not summary["station_failed"]:
            p_status = P_GE31_PASS
            support_status = "PASS"
        elif metrics_ok:
            p_status = P_GE31_WEAK
            support_status = "STATION_CAVEATS_REMAIN"
        else:
            p_status = P_GE31_NOT_PROMOTED
            support_status = "METRICS_FAILED"
    rows = [
        {
            "gate_id": "p_ge31_optional",
            "status": p_status,
            "support_status": support_status,
            "evidence_summary": (
                f"n_rows={summary['n_rows']}; n_ge31={summary['n_ge31']}; "
                f"fixed31_recall={fmt(fixed.get('recall'), 3) or 'NA'}; "
                f"best_F1_recall={fmt(best.get('recall'), 3) if best else 'NA'}; "
                f"Brier={fmt(summary.get('p_brier'), 3) or 'NA'}; ECE={fmt(summary.get('p_ece'), 3) or 'NA'}"
            ),
            "pass_condition": "Materially improved ge31 recall/miss behavior vs fixed_31 with acceptable precision/false alarms, stable Brier/ECE, and station caveats not failed.",
            "forbidden_interpretation": "official warning probability",
            "next_action": "Review prospective evidence; keep public-warning claims forbidden regardless of this internal gate.",
        },
        {
            "gate_id": "p_ge33_optional",
            "status": ge33_status,
            "support_status": "SUPPORT_PRESENT" if summary["n_ge33"] >= min_ge33 else "LOW_SUPPORT",
            "evidence_summary": f"n_ge33={summary['n_ge33']}; minimum_for_promotion={min_ge33}; explicit calibration evidence is not auto-created by this harness.",
            "pass_condition": f"Requires >= {min_ge33} ge33 events plus explicit calibration evidence.",
            "forbidden_interpretation": "promoted severe warning probability",
            "next_action": "Keep p_ge33 exploratory unless a separate reviewed calibration package supports it.",
        },
    ]
    return rows, p_status, ge33_status, str(summary["station_caveat_headline"])


def determine_lane_status(snapshot: TablePreview | None, detection_reason: str, p_status: str) -> str:
    """Map snapshot and promotion results to an A-L1H.6 lane status."""
    if detection_reason == "FORMAL_CANDIDATE_SCHEMA_INVALID":
        return BLOCKED_SCHEMA_STATUS
    if snapshot is None:
        return WAITING_STATUS
    if p_status == P_GE31_PASS:
        return PASS_STATUS
    return WEAK_STATUS


def make_evaluation_plan() -> list[dict[str, Any]]:
    """Create the prospective evaluation plan table."""
    return [
        {
            "step_id": "1",
            "phase": "contract_dependency",
            "action": "Confirm A-L1H.5 status, output contract, schema, threshold policy, and station caveat register are frozen.",
            "input_dependency": "A-L1H.5 contract package",
            "output": "input_inventory; expected_input_schema",
            "pass_condition": "All frozen contract inputs exist.",
            "claim_boundary": "No modification to A-L1H.5 decisions.",
        },
        {
            "step_id": "2",
            "phase": "snapshot_detection",
            "action": "Search compact CSV/CSV.GZ/Parquet snapshot candidates and verify required columns, prospective rows, event support, lead-time metadata, and frozen model/version metadata.",
            "input_dependency": "candidate_prospective_paths; existing output search roots",
            "output": "snapshot_detection_report",
            "pass_condition": "Valid formal snapshot has required schema, no forbidden columns, and prospective rows.",
            "claim_boundary": "No raw archive or live-growing forecast CSV reads.",
        },
        {
            "step_id": "3",
            "phase": "prospective_metrics",
            "action": "Evaluate prospective rows against official_wbgt_c using deterministic fixed_31 and optional companion diagnostics if present.",
            "input_dependency": "valid formal prospective snapshot",
            "output": "prospective_metrics",
            "pass_condition": "Metrics are written only for real prospective rows.",
            "claim_boundary": "No model training and no fake metrics when no snapshot exists.",
        },
        {
            "step_id": "4",
            "phase": "station_caveat_refresh",
            "action": "Refresh S142/S139 and all-station caveats without creating station-adjusted WBGT.",
            "input_dependency": "valid formal prospective snapshot",
            "output": "station_caveat_refresh",
            "pass_condition": "Station rows report support and caveat status.",
            "claim_boundary": "Station diagnostics are not a correction layer.",
        },
        {
            "step_id": "5",
            "phase": "promotion_gate",
            "action": "Apply frozen internal gate logic for P_ge31 and keep P_ge33 exploratory unless support and explicit calibration evidence exist.",
            "input_dependency": "prospective metrics; station caveat refresh",
            "output": "promotion_gate; report; status",
            "pass_condition": "Gate status is PASS, WEAK, NOT_PROMOTED, or WAITING with reasons.",
            "claim_boundary": "P_ge31 is not promoted to official warning probability.",
        },
    ]


def make_metric_schema() -> list[dict[str, Any]]:
    """Create the metric schema table."""
    return [
        {"metric_name": "n_rows", "required_when_snapshot_valid": "yes", "type": "integer", "formula_or_definition": "Count of prospective rows.", "output_group": "support", "caveat": "Rows must be explicitly labeled prospective."},
        {"metric_name": "n_stations", "required_when_snapshot_valid": "yes", "type": "integer", "formula_or_definition": "Unique station_id count in numeric prospective rows.", "output_group": "support", "caveat": "Station support can be uneven."},
        {"metric_name": "n_ge31", "required_when_snapshot_valid": "yes", "type": "integer", "formula_or_definition": "Count of official_wbgt_c >=31 C.", "output_group": "support", "caveat": "Minimum 30 for P_ge31 promotion review."},
        {"metric_name": "n_ge33", "required_when_snapshot_valid": "yes", "type": "integer", "formula_or_definition": "Count of official_wbgt_c >=33 C.", "output_group": "support", "caveat": "Minimum 30 plus explicit calibration evidence before ge33 review."},
        {"metric_name": "recall_ge31", "required_when_snapshot_valid": "yes", "type": "float", "formula_or_definition": "TP / (TP + FN) for official_wbgt_c >=31 C.", "output_group": "classification", "caveat": "Report for deterministic fixed_31 and optional P_ge31 policies separately."},
        {"metric_name": "precision_ge31", "required_when_snapshot_valid": "yes", "type": "float", "formula_or_definition": "TP / (TP + FP) for official_wbgt_c >=31 C.", "output_group": "classification", "caveat": "Precision must be interpreted with false-alarm governance caveats."},
        {"metric_name": "miss_rate_ge31", "required_when_snapshot_valid": "yes", "type": "float", "formula_or_definition": "FN / (TP + FN).", "output_group": "classification", "caveat": "High-tail misses remain the focus."},
        {"metric_name": "false_alarm_ratio_ge31", "required_when_snapshot_valid": "yes", "type": "float", "formula_or_definition": "FP / (TP + FP).", "output_group": "classification", "caveat": "Not a public alert false-alarm guarantee."},
        {"metric_name": "CSI_ge31", "required_when_snapshot_valid": "yes", "type": "float", "formula_or_definition": "TP / (TP + FP + FN).", "output_group": "classification", "caveat": "Internal diagnostic only."},
        {"metric_name": "Brier_p_ge31_optional", "required_when_snapshot_valid": "if column present", "type": "float", "formula_or_definition": "Mean squared error between p_ge31_optional and observed ge31 event.", "output_group": "calibration", "caveat": "Does not make P_ge31 an official warning probability."},
        {"metric_name": "ECE_p_ge31_optional", "required_when_snapshot_valid": "if column present", "type": "float", "formula_or_definition": "Fixed-width expected calibration error.", "output_group": "calibration", "caveat": "Bin-level calibration should be reviewed before stronger claims."},
        {"metric_name": "high_tail_MAE_obs_ge31", "required_when_snapshot_valid": "yes", "type": "float_celsius", "formula_or_definition": "Mean absolute wbgt_a_c error on official_wbgt_c >=31 C rows.", "output_group": "deterministic", "caveat": "Primary output remains wbgt_a_c, not local 100 m WBGT."},
        {"metric_name": "expected_exceedance_MAE", "required_when_snapshot_valid": "if column present", "type": "float_celsius", "formula_or_definition": "MAE against max(official_wbgt_c - 31, 0).", "output_group": "expected_exceedance", "caveat": "Not a corrected WBGT forecast."},
        {"metric_name": "interval_empirical_coverage", "required_when_snapshot_valid": "if columns present", "type": "float", "formula_or_definition": "Share of rows where interval_low <= official_wbgt_c <= interval_high.", "output_group": "interval", "caveat": "Not an operational interval guarantee."},
    ]


def waiting_station_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Write non-metric station caveat placeholders while waiting."""
    rows: list[dict[str, Any]] = []
    for station_id in ["ALL", *[str(item) for item in config["analysis"].get("focus_stations", [])]]:
        rows.append(
            {
                "station_id": station_id,
                "n_rows": "",
                "n_ge31": "",
                "n_ge33": "",
                "fixed31_recall_ge31": "",
                "fixed31_miss_rate_ge31": "",
                "fixed31_false_alarm_ratio_ge31": "",
                "p_ge31_best_F1_recall_ge31": "",
                "p_ge31_best_F1_miss_rate_ge31": "",
                "p_ge31_best_F1_false_alarm_ratio_ge31": "",
                "caveat_status": "WAITING_FOR_FORMAL_SNAPSHOT",
                "headline": "No station metrics computed because no valid prospective snapshot exists.",
                "not_station_correction": "yes",
            }
        )
    return rows


def build_report(
    status: str,
    config: dict[str, Any],
    detection_reason: str,
    detection_rows: list[dict[str, Any]],
    metric_rows: list[dict[str, Any]],
    promotion_rows: list[dict[str, Any]],
    station_rows: list[dict[str, Any]],
    candidate_path: str,
) -> str:
    """Build the English A-L1H.6 report."""
    today = config.get("generated_date", date.today().isoformat())
    snapshot_found = "yes" if candidate_path else "no"
    metrics_text = markdown_table(metric_rows, ["metric_name", "metric_group", "value", "operating_point", "status"], 28) if metric_rows else "_No prospective metrics were computed because no valid formal snapshot exists._"
    return f"""# System A A-L1H.6 Prospective Evaluation Harness

Generated: {today}
Decision status: `{status}`
Branch: `{git_branch()}`

## 1. Why A-L1H.6 Follows A-L1H.5

A-L1H.5 froze the System A Level 1 model card and hourly output contract. A-L1H.6 prepares the prospective evaluation harness requested by that contract: it waits for a future frozen formal snapshot, separates prospective rows from retrospective rows, and evaluates only after real prospective rows exist.

## 2. Frozen Contract Dependency

The harness depends on the frozen A-L1H.5 status, hourly output contract, output schema, threshold-policy register, and station-caveat register. It does not modify A-L1H.5 decisions. `wbgt_a_c` remains primary; `p_ge31_optional` remains an optional diagnostic companion; `p_ge33_optional` remains exploratory.

## 3. Snapshot Detection Results

Detection reason: `{detection_reason}`

Snapshot found: `{snapshot_found}`

Candidate path: `{candidate_path or 'none'}`

{markdown_table(detection_rows, ["path", "candidate_table", "detection_status", "n_prospective_rows", "n_ge31", "n_ge33", "reason"], 12)}

## 4. Required Future Input Schema

The required future table must include `timestamp_sgt`, `timestamp_utc`, `station_id`, `official_wbgt_c`, `wbgt_a_c`, `wbgt_a_model_id`, `wbgt_a_version`, `is_retrospective_or_prospective`, and `quality_flag`. Optional companions may include `p_ge31_optional`, `p_ge31_model_id_optional`, `p_ge31_threshold_policy_optional`, `p_ge33_optional`, expected exceedance, interval, and lead-time fields.

Forbidden columns remain forbidden: `cell_id`, `local_wbgt_c`, `delta_wbgt_cell`, `station_adjusted_wbgt_c`, `risk_score`, and `hazard_score`.

## 5. Evaluation Metrics

{metrics_text}

## 6. Promotion Gate Logic

{markdown_table(promotion_rows, ["gate_id", "status", "support_status", "evidence_summary", "next_action"], None)}

## 7. Station Caveat Refresh

{markdown_table(station_rows, ["station_id", "n_rows", "n_ge31", "n_ge33", "caveat_status", "headline"], 14)}

Station rows are monitoring diagnostics only; they are not station corrections.

## 8. Claim Boundaries

- No new model training.
- No station-adjusted WBGT.
- No local 100 m WBGT.
- No official warning probability.
- No risk_score or hazard_score.
- No System A/B coupling.
- No System B, SOLWEIG, or Tmrt features.

## 9. Next Recommended Action

Freeze a formal prospective System A snapshot with the required schema, place it under a configured candidate path, and rerun:

`python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml`
"""


def build_cn_doc(
    status: str,
    config: dict[str, Any],
    detection_reason: str,
    candidate_path: str,
    promotion_rows: list[dict[str, Any]],
    station_headline: str,
) -> str:
    """Build the Chinese A-L1H.6 documentation note in valid UTF-8."""
    today = config.get("generated_date", date.today().isoformat())
    p_ge31_status = next((row.get("status", "") for row in promotion_rows if row.get("gate_id") == "p_ge31_optional"), "")
    ge33_status = next((row.get("status", "") for row in promotion_rows if row.get("gate_id") == "p_ge33_optional"), "")
    cn_station_headline = (
        "站点注意事项刷新正在等待正式快照。"
        if station_headline == "Station caveat refresh waiting for formal snapshot."
        else station_headline
    )
    return f"""# OpenHeat System A A-L1H.6 前瞻评估框架

生成日期：{today}
决策状态：`{status}`

## 1. 为什么 A-L1H.6 接在 A-L1H.5 之后

A-L1H.5 已冻结 System A Level 1 的模型卡与小时输出契约。本通道不重新训练模型，也不改变契约决策；它只准备未来正式冻结快照的前瞻评估框架。

## 2. 冻结契约依赖

本框架依赖 A-L1H.5 的状态文件、小时输出契约、输出模式表、阈值策略登记表和站点注意事项登记表。`wbgt_a_c` 仍是主输出；`p_ge31_optional` 仍是可选诊断伴随列；`p_ge33_optional` 仍是探索性列。

## 3. 快照检测结果

检测结果：`{detection_reason}`。

候选快照：`{candidate_path or '无'}`。

如果没有有效正式前瞻快照，本框架输出 `WAITING_FOR_FORMAL_SNAPSHOT`，并且不生成伪造指标。

## 4. 未来输入模式

未来正式快照必须包含：`timestamp_sgt`、`timestamp_utc`、`station_id`、`official_wbgt_c`、`wbgt_a_c`、`wbgt_a_model_id`、`wbgt_a_version`、`is_retrospective_or_prospective` 和 `quality_flag`。

可选列包括：`p_ge31_optional`、`p_ge31_model_id_optional`、`p_ge31_threshold_policy_optional`、`p_ge33_optional`、`expected_exceedance_ge31_optional`、区间上下界和 `lead_time_hours_optional`。

## 5. 评估指标

有正式前瞻行时，框架会报告 `n_rows`、`n_stations`、`n_ge31`、`n_ge33`、ge31 的召回率、精确率、漏报率、误报比例、CSI、`p_ge31_optional` 的 Brier 和 ECE、高尾 MAE、固定 31 C 基线、可选 P_ge31 策略、期望超阈误差、区间覆盖率以及站点注意事项刷新。

## 6. 提升门槛逻辑

`p_ge31_optional` 当前门槛状态：`{p_ge31_status}`。只有在正式前瞻快照中相对 `wbgt_a_c` fixed_31 保持实质性召回/漏报改善、精确率与误报表现可接受、Brier/ECE 稳定且站点注意事项未失败时，才可进入更强的内部伴随列讨论。

`p_ge33_optional` 当前状态：`{ge33_status}`。除非至少有 30 个 ge33 事件并有明确校准证据，否则仍保持探索性。

## 7. 站点注意事项刷新

{cn_station_headline}

这些站点结果只是监测和解释注意事项，不是站点修正模型。

## 8. 声明边界

- 不训练新模型。
- 不创建站点修正 WBGT。
- 不创建本地 100 m WBGT。
- 不创建官方预警概率。
- 不创建 risk_score 或 hazard_score。
- 不创建 System A/B 耦合输出。
- 不使用 System B、SOLWEIG 或 Tmrt 特征。

## 9. 下一步建议

在未来正式快照冻结后，把紧凑 CSV/CSV.GZ/Parquet 快照放入配置中的候选目录，并重新运行：

`python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml`
"""


def build_status(
    status: str,
    config: dict[str, Any],
    result: HarnessResult,
    detection_reason: str,
    output_paths: list[Path],
) -> str:
    """Build the A-L1H.6 status file."""
    today = config.get("generated_date", date.today().isoformat())
    files = "\n".join(f"- `{rel(path)}`" for path in output_paths)
    return f"""# A-L1H.6 Status

Status: {status}
Generated: {today}
Branch: {git_branch()}

## Scope

System A prospective evaluation harness only. No model training, no archive collector changes, no System B/SOLWEIG outputs, no station-adjusted WBGT, no local 100 m WBGT, no risk_score, no hazard_score, and no official warning probability.

## Commands Run

- `python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml`

## Key Results

- Snapshot found: {str(result.snapshot_found).lower()}
- Candidate path: {result.candidate_path or 'none'}
- Detection reason: {detection_reason}
- n_rows / n_ge31 / n_ge33: {result.n_rows or 'NA'} / {result.n_ge31 or 'NA'} / {result.n_ge33 or 'NA'}
- P_ge31 promotion gate: {result.p_ge31_promotion_gate_status}
- ge33 status: {result.ge33_status}
- Station caveat headline: {result.station_caveat_headline}

## Files Created / Modified

{files}

## Caveats

- WAITING status is acceptable and expected when no formal prospective snapshot exists.
- No fake prospective metrics are written while waiting.
- Promotion gates are internal diagnostic gates and do not create public warning probabilities.

## Safe To Commit

Controlled config, scripts, docs, and compact outputs from this lane after review.

## Not Safe To Commit

Raw archives, rasters, SOLWEIG/System B outputs, tif/tiff files, svfs.zip, patch zip packages, raw API dumps, or large forecast/live CSVs.
"""


def run_harness(config_path: Path) -> HarnessResult:
    """Run the A-L1H.6 prospective evaluation harness."""
    config = load_config(config_path)
    compact_tables = discover_compact_tables(config)
    previews = [read_table_preview(path) for path in compact_tables]
    snapshot, detection_rows, detection_reason = choose_snapshot(config, previews)
    detection_rows = candidate_root_detection_rows(config, compact_tables) + detection_rows

    input_inventory = make_input_inventory(config, compact_tables)
    expected_schema = make_expected_input_schema(config)
    evaluation_plan = make_evaluation_plan()
    metric_schema = make_metric_schema()

    metric_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] | None = None
    if snapshot is not None:
        metric_rows, station_rows, summary = evaluate_snapshot(config, snapshot)
    else:
        station_rows = waiting_station_rows(config)

    promotion_rows, p_status, ge33_status, station_headline = determine_promotion_gate(config, snapshot, detection_reason, summary)
    status = determine_lane_status(snapshot, detection_reason, p_status)
    candidate_path = rel(snapshot.path) if snapshot is not None else ""
    n_rows = str(summary["n_rows"]) if summary is not None else ""
    n_ge31 = str(summary["n_ge31"]) if summary is not None else ""
    n_ge33 = str(summary["n_ge33"]) if summary is not None else ""

    outputs = config["outputs"]
    output_paths = [
        write_csv(
            resolve_path(outputs["input_inventory"]),
            input_inventory,
            ["input_id", "input_role", "path", "exists", "file_type", "bytes", "source_group", "searched", "candidate_table", "notes"],
        ),
        write_csv(
            resolve_path(outputs["expected_input_schema"]),
            expected_schema,
            ["column_name", "required_or_optional", "type", "allowed_null", "description", "forbidden_interpretation", "validation_check"],
        ),
        write_csv(
            resolve_path(outputs["snapshot_detection_report"]),
            detection_rows,
            [
                "path",
                "source_group",
                "candidate_table",
                "read_status",
                "detection_status",
                "reason",
                "n_total_rows",
                "n_prospective_rows",
                "n_ge31",
                "n_ge33",
                "required_columns_present",
                "missing_required_columns",
                "forbidden_columns_present",
                "optional_columns_present",
                "lead_time_hours_optional_present",
                "frozen_model_version_metadata",
                "p_ge31_metadata_status",
            ],
        ),
        write_csv(
            resolve_path(outputs["evaluation_plan"]),
            evaluation_plan,
            ["step_id", "phase", "action", "input_dependency", "output", "pass_condition", "claim_boundary"],
        ),
        write_csv(
            resolve_path(outputs["metric_schema"]),
            metric_schema,
            ["metric_name", "required_when_snapshot_valid", "type", "formula_or_definition", "output_group", "caveat"],
        ),
        write_csv(
            resolve_path(outputs["prospective_metrics"]),
            metric_rows,
            ["metric_name", "metric_group", "value", "numerator", "denominator", "operating_point", "applies_to", "status", "notes"],
        ),
        write_csv(
            resolve_path(outputs["station_caveat_refresh"]),
            station_rows,
            [
                "station_id",
                "n_rows",
                "n_ge31",
                "n_ge33",
                "fixed31_recall_ge31",
                "fixed31_miss_rate_ge31",
                "fixed31_false_alarm_ratio_ge31",
                "p_ge31_best_F1_recall_ge31",
                "p_ge31_best_F1_miss_rate_ge31",
                "p_ge31_best_F1_false_alarm_ratio_ge31",
                "caveat_status",
                "headline",
                "not_station_correction",
            ],
        ),
        write_csv(
            resolve_path(outputs["promotion_gate"]),
            promotion_rows,
            ["gate_id", "status", "support_status", "evidence_summary", "pass_condition", "forbidden_interpretation", "next_action"],
        ),
    ]

    result = HarnessResult(
        status=status,
        snapshot_found=snapshot is not None,
        candidate_path=candidate_path,
        n_rows=n_rows,
        n_ge31=n_ge31,
        n_ge33=n_ge33,
        p_ge31_promotion_gate_status=p_status,
        ge33_status=ge33_status,
        station_caveat_headline=station_headline,
        output_paths=output_paths,
    )
    report_path = write_text(
        resolve_path(outputs["report"]),
        build_report(status, config, detection_reason, detection_rows, metric_rows, promotion_rows, station_rows, candidate_path),
    )
    cn_doc_path = write_text(
        resolve_path(outputs["cn_doc"]),
        build_cn_doc(status, config, detection_reason, candidate_path, promotion_rows, station_headline),
    )
    result.output_paths.extend([report_path, cn_doc_path])
    status_path = write_text(resolve_path(outputs["status"]), build_status(status, config, result, detection_reason, result.output_paths))
    result.output_paths.append(status_path)
    return result


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the A-L1H.6 prospective evaluation harness. "
            "Inputs, outputs, candidate paths, required schema, and metric gates are declared in the YAML config."
        )
    )
    parser.add_argument("--config", default="configs/v11/systema_l1h6_prospective_eval_harness.yaml", help="Path to the explicit A-L1H.6 YAML config.")
    args = parser.parse_args()

    result = run_harness(resolve_path(args.config))
    print(f"[status] {result.status}")
    print(f"[snapshot_found] {'yes' if result.snapshot_found else 'no'}")
    print(f"[candidate_path] {result.candidate_path or 'none'}")
    print(f"[n_rows] {result.n_rows or 'NA'}")
    print(f"[n_ge31] {result.n_ge31 or 'NA'}")
    print(f"[n_ge33] {result.n_ge33 or 'NA'}")
    print(f"[p_ge31_promotion_gate_status] {result.p_ge31_promotion_gate_status}")
    print(f"[ge33_status] {result.ge33_status}")
    print(f"[station_caveat_headline] {result.station_caveat_headline}")
    print("[files_created]")
    for path in result.output_paths:
        print(f"- {rel(path)}")
    return 0 if result.status in {WAITING_STATUS, PASS_STATUS, WEAK_STATUS, BLOCKED_SCHEMA_STATUS} else 1


if __name__ == "__main__":
    raise SystemExit(main())
