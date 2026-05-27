"""Build the B8.6d compact two-stage surrogate dataset.

Inputs:
    - F5 pairwise labels from config key inputs.f5_pairwise_label_path.
    - B8.6c hardened surrogate dataset from inputs.b86c_dataset_path.
    - B8.6c feature registry and safe/rejected feature catalogs.
Outputs:
    - b86d_input_inventory.csv
    - b86d_dataset_schema.csv
    - b86d_two_stage_dataset.csv
    - b86d_feature_set_registry.csv
Saved metrics:
    Row/cell/forcing-day/hour counts, target availability, predictor role and
    leakage-guard status for each dataset column.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86d_common import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    ensure_output_dir,
    feature_columns_for_set,
    forbidden_predictor,
    load_config,
    output_path,
    parse_pipe_list,
    read_csv,
    repo_path,
    validation_folds,
    fold_inventory,
    write_csv,
)


@dataclass(frozen=True)
class DatasetResult:
    """B8.6d dataset creation result."""

    status: str
    rows: int
    cells: int
    forcing_days: int
    hours: int
    feature_sets: int


def guardrails_are_set(config: dict[str, Any]) -> None:
    """Validate explicit no-raster/no-AOI/no-B9 guardrails."""
    guardrails = config.get("guardrails", {})
    required = ["no_raster_io", "no_qgis_solweig", "no_aoi_prediction", "no_b9"]
    missing = [key for key in required if guardrails.get(key) is not True]
    if missing:
        raise ValueError(f"B8.6d guardrails are not explicit true values: {missing}")


def input_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Build an input inventory without touching forbidden raw/raster files."""
    rows: list[dict[str, Any]] = []
    for key, path in config["inputs"].items():
        resolved = repo_path(path)
        row: dict[str, Any] = {
            "input_key": key,
            "path": str(path),
            "exists": resolved.exists(),
            "size_bytes": resolved.stat().st_size if resolved.exists() else None,
            "row_count": None,
            "column_count": None,
            "unique_cells": None,
            "forcing_day_count": None,
            "hour_count": None,
            "allowed_for_b86d": True,
            "claim_boundary": CLAIM_BOUNDARY,
        }
        if resolved.exists() and resolved.suffix.lower() == ".csv":
            frame = pd.read_csv(resolved)
            row["row_count"] = len(frame)
            row["column_count"] = len(frame.columns)
            if "cell_id" in frame.columns:
                row["unique_cells"] = int(frame["cell_id"].nunique())
            if "forcing_day_id" in frame.columns:
                row["forcing_day_count"] = int(frame["forcing_day_id"].nunique())
            if "hour_sgt" in frame.columns:
                row["hour_count"] = int(frame["hour_sgt"].nunique())
        rows.append(row)
    return pd.DataFrame(rows)


def validate_dataset(dataset: pd.DataFrame, labels: pd.DataFrame, config: dict[str, Any]) -> None:
    """Validate the compact row/cell/target contract."""
    expected = config["expected"]
    primary = config["targets"]["primary_target"]
    required = ["cell_id", "forcing_day_id", "hour_sgt", primary]
    missing = [column for column in required if column not in dataset.columns]
    if missing:
        raise ValueError(f"B8.6d blocked input: missing required dataset columns {missing}")
    for target in [primary, *config["targets"]["companion_targets"]]:
        if target not in dataset.columns:
            raise ValueError(f"B8.6d blocked input: missing target {target}")
        if int(dataset[target].notna().sum()) != len(dataset):
            raise ValueError(f"B8.6d blocked input: target {target} has missing values")
    if len(dataset) != int(expected["rows"]):
        raise ValueError(f"B8.6d blocked input: expected {expected['rows']} rows, found {len(dataset)}")
    if int(dataset["cell_id"].nunique()) != int(expected["cells"]):
        raise ValueError("B8.6d blocked input: unexpected unique cell count")
    if int(dataset["forcing_day_id"].nunique()) != int(expected["forcing_days"]):
        raise ValueError("B8.6d blocked input: unexpected forcing day count")
    hours = sorted(pd.to_numeric(dataset["hour_sgt"], errors="coerce").dropna().astype(int).unique().tolist())
    if hours != list(map(int, expected["hours"])):
        raise ValueError(f"B8.6d blocked input: unexpected hours {hours}")
    if len(labels) != int(expected["rows"]):
        raise ValueError(f"B8.6d blocked input: F5 label rows mismatch {len(labels)}")


def add_lane_columns(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Add B8.6d neutral-label and diagnostic columns."""
    out = dataset.copy()
    primary = config["targets"]["primary_target"]
    for threshold in config["neutral_thresholds_c"]:
        suffix = str(threshold).replace(".", "p")
        out[f"neutral_abs_le_t{suffix}"] = pd.to_numeric(out[primary], errors="coerce").abs() <= float(threshold)
        out[f"meaningful_cooling_lt_t{suffix}"] = pd.to_numeric(out[primary], errors="coerce") < -float(threshold)
    out["b86d_primary_target"] = primary
    out["b86d_primary_neutral_threshold_c"] = float(config["primary_neutral_threshold_c"])
    out["b86d_claim_boundary"] = CLAIM_BOUNDARY
    return out


def build_feature_registry(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Filter the B8.6c registry to B8.6d requested feature sets."""
    registry = read_csv(config["inputs"]["b86c_feature_set_registry_path"])
    rows: list[dict[str, Any]] = []
    for feature_set in config["feature_sets_to_test"]:
        source = registry.loc[registry["feature_set"].astype(str) == feature_set]
        source_columns = parse_pipe_list(source.iloc[0]["feature_columns"]) if not source.empty else []
        available_columns = feature_columns_for_set(registry, dataset, feature_set, config)
        forbidden_columns = [column for column in source_columns if column in dataset.columns and forbidden_predictor(column, config)]
        missing_columns = [column for column in source_columns if column not in dataset.columns]
        rows.append(
            {
                "feature_set": feature_set,
                "source_feature_count": len(source_columns),
                "available_feature_count": len(available_columns),
                "available_feature_columns": "|".join(available_columns),
                "missing_feature_count": len(missing_columns),
                "missing_feature_columns": "|".join(missing_columns),
                "excluded_forbidden_count": len(forbidden_columns),
                "excluded_forbidden_columns": "|".join(forbidden_columns),
                "primary_evidence_allowed": bool(source.iloc[0].get("primary_evidence_allowed", True)) if not source.empty else False,
                "contains_coordinate_context": bool(source.iloc[0].get("contains_coordinate_context", False)) if not source.empty else False,
                "status": "AVAILABLE" if available_columns else "BLOCKED_NO_FEATURES",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def dataset_schema(dataset: pd.DataFrame, registry: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create a machine-readable schema and leakage-guard audit."""
    target_cols = {config["targets"]["primary_target"], *config["targets"]["companion_targets"]}
    feature_cols = set()
    for value in registry["available_feature_columns"].fillna(""):
        feature_cols.update(parse_pipe_list(value))
    split_meta = set(config["feature_contract"]["split_metadata_columns"])
    meta = set(config["feature_contract"]["metadata_columns"])
    rows: list[dict[str, Any]] = []
    for column in dataset.columns:
        if column in target_cols:
            role = "target"
            allowed = False
        elif column in feature_cols:
            role = "predictor"
            allowed = True
        elif column in split_meta:
            role = "split_metadata"
            allowed = column == "hour_sgt" and column in feature_cols
        elif column in meta:
            role = "metadata"
            allowed = False
        else:
            role = "unused_compact_context"
            allowed = False
        forbidden = forbidden_predictor(column, config)
        rows.append(
            {
                "column_name": column,
                "dtype": str(dataset[column].dtype),
                "non_null_count": int(dataset[column].notna().sum()),
                "missing_fraction": float(dataset[column].isna().mean()),
                "unique_count": int(dataset[column].nunique(dropna=True)),
                "role": role,
                "predictor_allowed": bool(allowed and not forbidden),
                "leakage_guard": "PASS" if not (allowed and forbidden) else "EXCLUDED_FORBIDDEN",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> DatasetResult:
    """Create B8.6d dataset outputs."""
    config = load_config(config_path)
    ensure_output_dir(config)
    guardrails_are_set(config)
    labels = read_csv(config["inputs"]["f5_pairwise_label_path"])
    dataset = read_csv(config["inputs"]["b86c_dataset_path"])
    validate_dataset(dataset, labels, config)
    dataset = add_lane_columns(dataset, config)
    registry = build_feature_registry(dataset, config)
    schema = dataset_schema(dataset, registry, config)
    folds = validation_folds(dataset, config)

    write_csv(input_inventory(config), output_path(config, "input_inventory"))
    write_csv(schema, output_path(config, "dataset_schema"))
    write_csv(dataset, output_path(config, "two_stage_dataset"))
    write_csv(registry, output_path(config, "feature_set_registry"))
    write_csv(fold_inventory(dataset, folds), output_path(config, "validation_splits"))

    return DatasetResult(
        status="B86D_DATASET_READY",
        rows=len(dataset),
        cells=int(dataset["cell_id"].nunique()),
        forcing_days=int(dataset["forcing_day_id"].nunique()),
        hours=int(dataset["hour_sgt"].nunique()),
        feature_sets=int((registry["status"] == "AVAILABLE").sum()),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Build the B8.6d compact two-stage surrogate dataset, schema, input inventory, "
            "and feature-set registry. Inputs/outputs/saved metrics are documented in the module docstring."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    result = run(args.config)
    print(result)


if __name__ == "__main__":
    main()
