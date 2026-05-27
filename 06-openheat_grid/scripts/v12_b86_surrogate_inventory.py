"""Inventory compact B8.6 System B surrogate protocol inputs.

Inputs:
    configs/v12/systemb_b86_surrogate_protocol.yaml, plus compact CSV,
    Parquet, Markdown, YAML, and JSON files under the configured scan roots.

Outputs:
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_input_inventory.csv
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_label_source_inventory.csv
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_feature_source_inventory.csv

Saved metrics:
    File size, suffix, compact-file readability, header columns, N150/surrogate
    filename flags, required label-column availability, feature-column
    availability, and exact BLOCKED_LABEL_INPUT / BLOCKED_FEATURE_INPUT
    reasons when compact inputs are missing.

This script does not run QGIS or SOLWEIG, does not read raster files, does not
copy svfs.zip, does not create an N150 execution runner or manifest, and does
not create local WBGT, hazard_score, risk_score, AOI-wide prediction, or
System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b86_surrogate_protocol.yaml"
COMPACT_SUFFIXES = {".csv", ".gz", ".parquet", ".md", ".yaml", ".yml", ".json"}
RASTER_SUFFIXES = {".tif", ".tiff"}


@dataclass(frozen=True)
class InventoryResult:
    """Compact return record for the B8.6 inventory step."""

    status: str
    n_input_files: int
    n_label_candidates: int
    n_feature_candidates: int
    selected_label_source: str
    selected_feature_source: str
    label_blocker: str
    feature_blocker: str


def repo_path(value: str | Path) -> Path:
    """Resolve a config path relative to the OpenHeat project directory."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def rel_path(path: Path) -> str:
    """Return a stable repository-relative path string when possible."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_config(path: Path) -> dict[str, Any]:
    """Read the explicit B8.6 YAML config."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def is_compact_file(path: Path) -> bool:
    """Return whether the file is allowed for B8.6 compact input discovery."""
    suffixes = {suffix.lower() for suffix in path.suffixes}
    if suffixes & RASTER_SUFFIXES:
        return False
    if path.name.lower() == "svfs.zip":
        return False
    return bool(suffixes & COMPACT_SUFFIXES)


def safe_columns(path: Path) -> tuple[list[str], str]:
    """Read only compact table headers and return columns plus status."""
    suffixes = [suffix.lower() for suffix in path.suffixes]
    try:
        if ".csv" in suffixes:
            return pd.read_csv(path, nrows=0).columns.astype(str).tolist(), "READABLE_HEADER"
        if path.suffix.lower() == ".parquet":
            return pd.read_parquet(path, columns=[]).columns.astype(str).tolist(), "READABLE_HEADER"
        if path.suffix.lower() in {".md", ".yaml", ".yml", ".json"}:
            return [], "TEXT_OR_CONFIG"
    except Exception as exc:  # pragma: no cover - diagnostic output is the point.
        return [], f"HEADER_ERROR:{type(exc).__name__}"
    return [], "SKIPPED_SUFFIX"


def scan_input_files(config: dict[str, Any]) -> pd.DataFrame:
    """Scan configured roots for compact input files without opening rasters."""
    rows: list[dict[str, Any]] = []
    for root_value in config["inputs"]["scan_roots"]:
        root = repo_path(root_value)
        if not root.exists():
            rows.append(
                {
                    "scan_root": str(root_value),
                    "path": str(root_value),
                    "exists": False,
                    "suffix": "",
                    "size_bytes": 0,
                    "read_status": "MISSING_SCAN_ROOT",
                    "columns": "",
                    "column_count": 0,
                    "has_cell_id": False,
                    "has_hour": False,
                    "has_scenario": False,
                    "has_primary_target": False,
                    "has_tmrt_p90": False,
                    "has_m_rad": False,
                    "has_feature_keywords": False,
                    "filename_mentions_n150": False,
                    "filename_mentions_surrogate": False,
                }
            )
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or not is_compact_file(path):
                continue
            columns, read_status = safe_columns(path)
            lower_columns = {column.lower() for column in columns}
            lower_name = rel_path(path).lower()
            feature_tokens = [
                "svf",
                "shade",
                "building",
                "vegetation",
                "tree",
                "grass",
                "water",
                "road",
                "hardscape",
                "overhead",
                "impervious",
                "built",
                "gvi",
            ]
            rows.append(
                {
                    "scan_root": str(root_value),
                    "path": rel_path(path),
                    "exists": True,
                    "suffix": "".join(path.suffixes).lower(),
                    "size_bytes": path.stat().st_size,
                    "read_status": read_status,
                    "columns": "|".join(columns),
                    "column_count": len(columns),
                    "has_cell_id": "cell_id" in lower_columns,
                    "has_hour": bool({"hour_sgt", "hour"} & lower_columns),
                    "has_scenario": "scenario" in lower_columns,
                    "has_primary_target": "delta_tmrt_p90_c" in lower_columns,
                    "has_tmrt_p90": "tmrt_p90_c" in lower_columns or "tmrt_p90_c_base" in lower_columns,
                    "has_m_rad": "m_rad_pct01" in lower_columns,
                    "has_feature_keywords": any(any(token in column for token in feature_tokens) for column in lower_columns),
                    "filename_mentions_n150": "n150" in lower_name,
                    "filename_mentions_surrogate": "surrogate" in lower_name,
                }
            )
    return pd.DataFrame(rows)


def table_shape(path: Path) -> tuple[int, int, str]:
    """Read a compact table enough to report shape."""
    try:
        if not path.exists():
            return 0, 0, "MISSING"
        if ".csv" in [suffix.lower() for suffix in path.suffixes]:
            frame = pd.read_csv(path)
        elif path.suffix.lower() == ".parquet":
            frame = pd.read_parquet(path)
        else:
            return 0, 0, "TEXT_OR_CONFIG"
        return int(len(frame)), int(frame.shape[1]), "READABLE_TABLE"
    except Exception as exc:  # pragma: no cover - diagnostic output is the point.
        return 0, 0, f"TABLE_ERROR:{type(exc).__name__}"


def label_inventory(config: dict[str, Any], input_inventory: pd.DataFrame) -> pd.DataFrame:
    """Build candidate label-source inventory from explicit and discovered files."""
    required = {"cell_id", "hour_sgt", "delta_tmrt_p90_c"}
    rows: list[dict[str, Any]] = []
    explicit = config["inputs"]["label_candidates"]
    for label_name, value in explicit.items():
        path = repo_path(value)
        columns, read_status = safe_columns(path) if path.exists() else ([], "MISSING")
        lower_columns = {column.lower() for column in columns}
        row_count, column_count, table_status = table_shape(path) if path.exists() and ".csv" in [suffix.lower() for suffix in path.suffixes] else (0, len(columns), read_status)
        has_hour = "hour_sgt" in lower_columns or "hour" in lower_columns
        normalized_columns = set(lower_columns)
        if "hour" in normalized_columns:
            normalized_columns.add("hour_sgt")
        rows.append(
            {
                "candidate_name": label_name,
                "path": rel_path(path),
                "exists": path.exists(),
                "read_status": read_status,
                "table_status": table_status,
                "row_count": row_count,
                "column_count": column_count,
                "has_cell_id": "cell_id" in lower_columns,
                "has_hour_sgt_or_hour": has_hour,
                "has_scenario": "scenario" in lower_columns,
                "has_tmrt_p90_c": "tmrt_p90_c" in lower_columns or "tmrt_p90_c_base" in lower_columns,
                "has_delta_tmrt_p90_c": "delta_tmrt_p90_c" in lower_columns,
                "has_delta_tmrt_mean_c": "delta_tmrt_mean_c" in lower_columns,
                "has_delta_tmrt_p95_c": "delta_tmrt_p95_c" in lower_columns,
                "has_m_rad_pct01": "m_rad_pct01" in lower_columns,
                "required_columns_present": required.issubset(normalized_columns),
                "target_definition_guess": "overhead_as_canopy_minus_base" if "base_vs_overhead" in path.name else "reference_domain_or_scenario_label",
                "usable_for_b86_primary": path.exists() and required.issubset(normalized_columns) and "base_vs_overhead" in path.name,
                "notes": "Primary B8.6 label source requires overhead_as_canopy - base pairwise delta.",
            }
        )
    discovered = input_inventory.loc[
        input_inventory["exists"]
        & input_inventory["filename_mentions_n150"]
        & input_inventory["has_cell_id"]
        & input_inventory["has_primary_target"]
    ].copy()
    for item in discovered.itertuples(index=False):
        if str(item.path) in {row["path"] for row in rows}:
            continue
        rows.append(
            {
                "candidate_name": "discovered_n150_label",
                "path": item.path,
                "exists": True,
                "read_status": item.read_status,
                "table_status": "HEADER_ONLY_DISCOVERY",
                "row_count": 0,
                "column_count": item.column_count,
                "has_cell_id": item.has_cell_id,
                "has_hour_sgt_or_hour": item.has_hour,
                "has_scenario": item.has_scenario,
                "has_tmrt_p90_c": item.has_tmrt_p90,
                "has_delta_tmrt_p90_c": item.has_primary_target,
                "has_delta_tmrt_mean_c": "delta_tmrt_mean_c" in str(item.columns).lower(),
                "has_delta_tmrt_p95_c": "delta_tmrt_p95_c" in str(item.columns).lower(),
                "has_m_rad_pct01": item.has_m_rad,
                "required_columns_present": item.has_cell_id and item.has_hour and item.has_primary_target,
                "target_definition_guess": "discovered_compact_label",
                "usable_for_b86_primary": False,
                "notes": "Discovered by schema; not selected unless explicit pairwise source is missing and reviewed.",
            }
        )
    return pd.DataFrame(rows)


def feature_inventory(config: dict[str, Any], input_inventory: pd.DataFrame) -> pd.DataFrame:
    """Build candidate feature-source inventory from explicit and discovered files."""
    feature_columns = set(config["feature_contract"]["baseline_feature_columns"])
    coordinate_pairs = config["feature_contract"]["coordinate_pairs"]
    rows: list[dict[str, Any]] = []
    explicit = config["inputs"]["feature_candidates"]
    for feature_name, value in explicit.items():
        path = repo_path(value)
        columns, read_status = safe_columns(path) if path.exists() else ([], "MISSING")
        lower_to_original = {column.lower(): column for column in columns}
        lower_columns = set(lower_to_original)
        row_count, column_count, table_status = table_shape(path) if path.exists() and ".csv" in [suffix.lower() for suffix in path.suffixes] else (0, len(columns), read_status)
        available_features = [column for column in feature_columns if column.lower() in lower_columns]
        usable_pairs = [
            f"{x}/{y}"
            for x, y in coordinate_pairs
            if x.lower() in lower_columns and y.lower() in lower_columns
        ]
        rows.append(
            {
                "candidate_name": feature_name,
                "path": rel_path(path),
                "exists": path.exists(),
                "read_status": read_status,
                "table_status": table_status,
                "row_count": row_count,
                "column_count": column_count,
                "has_cell_id": "cell_id" in lower_columns,
                "available_feature_count": len(available_features),
                "available_features": "|".join(sorted(available_features)),
                "usable_coordinate_pairs": "|".join(usable_pairs),
                "has_typology_label": "typology_label" in lower_columns,
                "contains_target_like_columns": any(token in column for column in lower_columns for token in ["tmrt", "m_rad", "wbgt", "hazard", "risk"]),
                "usable_for_b86_features": path.exists() and "cell_id" in lower_columns and len(available_features) >= 5,
                "notes": "Feature source is compact; target-like columns are excluded from predictors if present.",
            }
        )
    discovered = input_inventory.loc[
        input_inventory["exists"]
        & input_inventory["has_cell_id"]
        & input_inventory["has_feature_keywords"]
    ].copy()
    for item in discovered.itertuples(index=False):
        if str(item.path) in {row["path"] for row in rows}:
            continue
        rows.append(
            {
                "candidate_name": "discovered_feature_table",
                "path": item.path,
                "exists": True,
                "read_status": item.read_status,
                "table_status": "HEADER_ONLY_DISCOVERY",
                "row_count": 0,
                "column_count": item.column_count,
                "has_cell_id": item.has_cell_id,
                "available_feature_count": 0,
                "available_features": "",
                "usable_coordinate_pairs": "",
                "has_typology_label": "typology_label" in str(item.columns).lower(),
                "contains_target_like_columns": any(token in str(item.columns).lower() for token in ["tmrt", "m_rad", "wbgt", "hazard", "risk"]),
                "usable_for_b86_features": False,
                "notes": "Discovered by feature keywords; explicit feature sources take precedence.",
            }
        )
    return pd.DataFrame(rows)


def selected_source(inventory: pd.DataFrame, usable_col: str) -> str:
    """Return the first usable source path, or an empty string."""
    usable = inventory.loc[inventory[usable_col]].copy() if usable_col in inventory else pd.DataFrame()
    if usable.empty:
        return ""
    return str(usable.iloc[0]["path"])


def run(config_path: Path = DEFAULT_CONFIG) -> InventoryResult:
    """Run compact input discovery and write B8.6 inventory outputs."""
    config = read_config(config_path)
    out_dir = repo_path(config["outputs"]["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    input_frame = scan_input_files(config)
    label_frame = label_inventory(config, input_frame)
    feature_frame = feature_inventory(config, input_frame)

    input_frame.to_csv(repo_path(config["outputs"]["input_inventory"]), index=False)
    label_frame.to_csv(repo_path(config["outputs"]["label_source_inventory"]), index=False)
    feature_frame.to_csv(repo_path(config["outputs"]["feature_source_inventory"]), index=False)

    label_source = selected_source(label_frame, "usable_for_b86_primary")
    feature_source = selected_source(feature_frame, "usable_for_b86_features")
    label_blocker = "" if label_source else "BLOCKED_LABEL_INPUT: no compact N150 pairwise overhead-minus-base label source with cell_id/hour_sgt/delta_tmrt_p90_c."
    feature_blocker = "" if feature_source else "BLOCKED_FEATURE_INPUT: no compact non-raster feature table with cell_id and sufficient physical features."
    if label_blocker:
        status = "BLOCKED_LABEL_INPUT"
    elif feature_blocker:
        status = "BLOCKED_FEATURE_INPUT"
    else:
        status = "INPUTS_READY"
    return InventoryResult(
        status=status,
        n_input_files=len(input_frame),
        n_label_candidates=len(label_frame),
        n_feature_candidates=len(feature_frame),
        selected_label_source=label_source,
        selected_feature_source=feature_source,
        label_blocker=label_blocker,
        feature_blocker=feature_blocker,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Inventory compact B8.6 surrogate protocol inputs.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6 YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
