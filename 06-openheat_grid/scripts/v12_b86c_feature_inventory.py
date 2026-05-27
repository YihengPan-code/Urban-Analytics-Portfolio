"""Inventory B8.6c compact feature candidates and write feature registries.

Inputs:
    configs/v12/systemb_b86c_feature_hardening.yaml
    outputs/v12_systemb_n150_sample_design/n150_sampling_feature_matrix.csv
    outputs/v12_systemb_n150_sample_design/n150_candidate_universe.csv
    B8.6b compact context CSV/Markdown paths declared in the config
    B8.5-F4 compact anchor, neutral, and unstable cell CSVs

Outputs:
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_input_inventory.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_feature_candidate_inventory.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_safe_feature_catalog.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_rejected_feature_catalog.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_feature_group_registry.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_feature_set_registry.csv

Saved metrics:
    Compact input existence, row and column counts, every compact feature
    candidate's safe/rejected/metadata/leakage-risk/future-required class,
    explicit rejection reason, model dataset column name, feature group
    membership, and feature-set membership.

This script reads compact CSV/Markdown/YAML inputs only. It does not run QGIS
or SOLWEIG, does not read raster files, does not open or copy svfs.zip, does
not create AOI-wide prediction, and does not create WBGT, hazard_score,
risk_score, B9, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b86c_feature_hardening.yaml"
FORBIDDEN_SUFFIXES = {".tif", ".tiff"}


@dataclass(frozen=True)
class InventoryResult:
    """Compact return record for the B8.6c inventory step."""

    status: str
    input_rows: int
    feature_candidates_scanned: int
    safe_feature_count: int
    rejected_feature_count: int
    feature_group_rows: int
    feature_set_rows: int


def repo_path(value: str | Path) -> Path:
    """Resolve a config path relative to the OpenHeat project directory."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def rel_path(path: Path) -> str:
    """Return a stable project-relative path string when possible."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_config(path: Path) -> dict[str, Any]:
    """Read the explicit B8.6c YAML config."""
    return yaml.safe_load(repo_path(path).read_text(encoding="utf-8"))


def assert_not_forbidden(path: Path) -> None:
    """Fail fast if a configured path points at a raster or svfs.zip."""
    suffixes = {suffix.lower() for suffix in path.suffixes}
    if suffixes & FORBIDDEN_SUFFIXES or path.name.lower() == "svfs.zip":
        raise ValueError(f"Forbidden file path configured for B8.6c: {path}")


def compact_table_status(path: Path) -> tuple[int, int, list[str], str]:
    """Return compact table shape and header status without touching forbidden files."""
    assert_not_forbidden(path)
    if not path.exists():
        return 0, 0, [], "MISSING"
    suffixes = {suffix.lower() for suffix in path.suffixes}
    if ".csv" not in suffixes:
        return 0, 0, [], "TEXT_OR_CONFIG" if path.suffix.lower() in {".md", ".yaml", ".yml", ".json"} else "UNSUPPORTED_COMPACT_SUFFIX"
    try:
        frame = pd.read_csv(path, nrows=0)
        columns = frame.columns.astype(str).tolist()
        row_count = int(sum(1 for _ in path.open("r", encoding="utf-8", errors="replace")) - 1)
        return max(row_count, 0), int(len(columns)), columns, "READABLE_CSV_HEADER"
    except Exception as exc:  # pragma: no cover - inventory should record local corruption.
        return 0, 0, [], f"HEADER_ERROR:{type(exc).__name__}"


def flatten_input_paths(config: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Flatten configured compact inputs into group/name/path rows."""
    rows: list[tuple[str, str, str]] = []
    for group_name, group_value in config["inputs"].items():
        if isinstance(group_value, dict):
            for name, value in group_value.items():
                rows.append((str(group_name), str(name), str(value)))
    return rows


def input_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Inventory every declared compact input path."""
    rows: list[dict[str, Any]] = []
    for group_name, name, value in flatten_input_paths(config):
        path = repo_path(value)
        row_count, column_count, columns, status = compact_table_status(path)
        rows.append(
            {
                "input_group": group_name,
                "candidate_name": name,
                "path": rel_path(path),
                "exists": path.exists(),
                "suffix": "".join(path.suffixes).lower(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
                "read_status": status,
                "row_count": row_count,
                "column_count": column_count,
                "columns": "|".join(columns),
                "compact_only_status": "PASS",
            }
        )
    return pd.DataFrame(rows)


def dataset_column_name(source_table: str, column: str, config: dict[str, Any]) -> str:
    """Return the dataset column name that B8.6c will use for a source column."""
    if source_table == config["feature_contract"]["candidate_universe_source"] and column != "cell_id":
        return f"{config['feature_contract']['candidate_universe_prefix']}{column}"
    return column


def classify_feature(
    source_table: str,
    column: str,
    dtype: str,
    non_null_count: int,
    config: dict[str, Any],
) -> tuple[str, bool, str, str]:
    """Classify one feature candidate and return class, predictor flag, group hint, and reason."""
    lower = column.lower()
    contract = config["feature_contract"]
    dataset_col = dataset_column_name(source_table, column, config)
    safe_sampling = set(contract["sampling_safe_columns"])
    safe_candidate = set(contract["candidate_universe_safe_columns"])
    safe_categorical = set(contract["categorical_safe_columns"])
    coordinate_cols = set(contract["coordinate_diagnostic_columns"])
    metadata_columns = set(contract["metadata_columns"])
    forbidden_tokens = [str(token).lower() for token in contract["forbidden_predictor_tokens"]]
    path_tokens = [str(token).lower() for token in contract["path_or_status_tokens"]]
    future_tokens = [str(token).lower() for token in contract["future_required_tokens"]]
    safe_tokens = [str(token).lower() for token in contract["safe_semantic_tokens"]]

    if column == "cell_id" or dataset_col in metadata_columns:
        return "metadata", False, "id_or_split_metadata", "Identifier, split, or lane metadata; not a predictor."
    if dataset_col in coordinate_cols or column in {"lon", "lat", "centroid_x", "centroid_y"}:
        return "metadata", False, "coordinate_context_diagnostic", "Coordinates are for spatial diagnostics/bins only."
    if any(token in lower for token in future_tokens):
        return "future-required", False, "future_risk_overlay", "Exposure/vulnerability context is future risk-overlay material, not a System B surrogate predictor."
    if any(token in lower for token in forbidden_tokens):
        return "leakage-risk", False, "forbidden_claim_boundary", "Column name matches forbidden target/claim/leakage token."
    if any(token in lower for token in path_tokens):
        return "metadata", False, "source_or_status_metadata", "Source/path/status/note metadata is excluded from predictors."
    if lower.endswith("_missing") or lower.endswith("_q01"):
        return "metadata", False, "sampling_diagnostic_metadata", "Sampling imputation/bin diagnostic column; not primary evidence predictor."

    curated_safe = (source_table == contract["sampling_feature_source"] and column in safe_sampling) or (
        source_table == contract["candidate_universe_source"] and column in safe_candidate
    )
    semantic_safe = any(token in lower for token in safe_tokens)
    is_categorical = dataset_col in safe_categorical or column in {"typology_label", "land_use_hint"}
    numeric_like = dtype != "object" and non_null_count > 0
    if curated_safe or is_categorical or (semantic_safe and numeric_like):
        group = group_hint(dataset_col)
        return "safe", True, group, "Compact non-target feature candidate; permitted by leakage guard."

    return "rejected", False, "not_in_safe_contract", "Not in the safe compact feature contract for B8.6c."


def group_hint(dataset_col: str) -> str:
    """Return a coarse feature group hint from a dataset column name."""
    lower = dataset_col.lower()
    if "overhead" in lower or "shade" in lower:
        return "overhead_shade"
    if "svf" in lower or "sky" in lower or "building" in lower or "canyon" in lower or "height" in lower or "dsm" in lower:
        return "built_canyon_svf"
    if "tree" in lower or "gvi" in lower or "grass" in lower or "water" in lower or "ndvi" in lower or "green" in lower or "park" in lower:
        return "vegetation_water"
    if "road" in lower or "hardscape" in lower or "impervious" in lower or "built" in lower:
        return "road_hardscape"
    if "typology" in lower or "land_use" in lower:
        return "typology_context"
    return "full_safe_compact"


def source_feature_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Inventory every compact source-table column as a feature candidate."""
    rows: list[dict[str, Any]] = []
    for source_table, value in config["inputs"]["feature_sources"].items():
        path = repo_path(value)
        assert_not_forbidden(path)
        if not path.exists():
            continue
        frame = pd.read_csv(path, dtype={"cell_id": "string"})
        for column in frame.columns.astype(str):
            dataset_col = dataset_column_name(str(source_table), column, config)
            non_null = int(frame[column].notna().sum())
            classification, predictor_allowed, hint, reason = classify_feature(
                str(source_table),
                column,
                str(frame[column].dtype),
                non_null,
                config,
            )
            rows.append(
                {
                    "source_table": source_table,
                    "source_path": rel_path(path),
                    "column_name": column,
                    "dataset_column": dataset_col,
                    "dtype": str(frame[column].dtype),
                    "non_null_count": non_null,
                    "missing_fraction": float(1 - non_null / len(frame)) if len(frame) else np.nan,
                    "unique_count": int(frame[column].nunique(dropna=True)),
                    "classification": classification,
                    "predictor_allowed": predictor_allowed,
                    "feature_group_hint": hint,
                    "rejection_reason": "" if classification == "safe" else reason,
                    "leakage_guard": "PASS" if predictor_allowed else "EXCLUDED",
                    "claim_boundary": "Feature audit only; no observed truth, causal feature importance, WBGT, risk, B9, or AOI-wide prediction.",
                }
            )
    return pd.DataFrame(rows)


def available_feature_columns(inventory: pd.DataFrame) -> set[str]:
    """Return dataset columns that are either safe predictors or allowed diagnostics."""
    if inventory.empty:
        return set()
    return set(inventory["dataset_column"].astype(str))


def feature_group_registry(config: dict[str, Any], inventory: pd.DataFrame) -> pd.DataFrame:
    """Create the B8.6c feature group registry from the explicit config."""
    available = available_feature_columns(inventory)
    safe_features = set(
        inventory.loc[inventory["classification"] == "safe", "dataset_column"].astype(str)
    )
    rows: list[dict[str, Any]] = []
    group_defs = dict(config["feature_groups"])
    full_safe = sorted(
        safe_features
        | {"hour_sgt"}
        | set(config["interactions"].keys())
        | set(config["feature_contract"]["categorical_safe_columns"])
    )
    group_defs["full_safe_compact"] = full_safe
    for group_name, columns in group_defs.items():
        for column in columns:
            is_available = column in available or column in config["interactions"] or column == "hour_sgt"
            is_coordinate = column in set(config["feature_contract"]["coordinate_diagnostic_columns"])
            rows.append(
                {
                    "feature_group": group_name,
                    "feature_column": column,
                    "available_in_dataset_contract": bool(is_available),
                    "feature_role": "diagnostic_coordinate" if is_coordinate else "predictor_candidate",
                    "primary_evidence_allowed": bool(not is_coordinate and group_name != "coordinate_context_diagnostic"),
                    "notes": "Coordinates are diagnostic only." if is_coordinate else "Compact non-target feature group member.",
                }
            )
    return pd.DataFrame(rows)


def feature_set_registry(config: dict[str, Any], group_registry: pd.DataFrame) -> pd.DataFrame:
    """Create the B8.6c feature set registry."""
    rows: list[dict[str, Any]] = []
    for set_name, definition in config["feature_sets"].items():
        groups = [str(group) for group in definition["groups"]]
        subset = group_registry.loc[
            group_registry["feature_group"].isin(groups)
            & group_registry["available_in_dataset_contract"].astype(bool)
        ].copy()
        columns = sorted(subset["feature_column"].dropna().astype(str).unique().tolist())
        coordinate_cols = set(config["feature_contract"]["coordinate_diagnostic_columns"])
        contains_coordinates = bool(set(columns) & coordinate_cols)
        rows.append(
            {
                "feature_set": set_name,
                "feature_groups": "|".join(groups),
                "feature_columns": "|".join(columns),
                "feature_count": len(columns),
                "primary_evidence_allowed": bool(definition.get("primary_evidence_allowed", True) and not contains_coordinates),
                "contains_coordinate_context": contains_coordinates,
                "feature_set_role": "diagnostic_only" if contains_coordinates else "main_candidate",
                "status": "AVAILABLE" if columns else "EMPTY",
                "claim_boundary": "Diagnostic feature set; coordinates are not causal." if contains_coordinates else "Non-target compact feature set.",
            }
        )
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> InventoryResult:
    """Run the compact input and feature-candidate inventory."""
    config = read_config(config_path)
    out_dir = repo_path(config["outputs"]["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    inputs = input_inventory(config)
    candidates = source_feature_inventory(config)
    safe = candidates.loc[candidates["classification"] == "safe"].copy()
    rejected = candidates.loc[candidates["classification"] != "safe"].copy()
    groups = feature_group_registry(config, candidates)
    sets = feature_set_registry(config, groups)

    inputs.to_csv(repo_path(config["outputs"]["input_inventory"]), index=False)
    candidates.to_csv(repo_path(config["outputs"]["feature_candidate_inventory"]), index=False)
    safe.to_csv(repo_path(config["outputs"]["safe_feature_catalog"]), index=False)
    rejected.to_csv(repo_path(config["outputs"]["rejected_feature_catalog"]), index=False)
    groups.to_csv(repo_path(config["outputs"]["feature_group_registry"]), index=False)
    sets.to_csv(repo_path(config["outputs"]["feature_set_registry"]), index=False)

    status = "B86C_INPUTS_READY" if not safe.empty and not sets.empty else "B86C_BLOCKED_INPUT"
    return InventoryResult(
        status=status,
        input_rows=int(len(inputs)),
        feature_candidates_scanned=int(len(candidates)),
        safe_feature_count=int(len(safe)),
        rejected_feature_count=int(len(rejected)),
        feature_group_rows=int(len(groups)),
        feature_set_rows=int(len(sets)),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Inventory B8.6c compact feature candidates, classify leakage-safe and "
            "rejected columns, and write feature group/set registries."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6c YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
