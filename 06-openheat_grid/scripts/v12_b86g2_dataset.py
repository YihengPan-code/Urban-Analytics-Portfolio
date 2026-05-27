"""Build the B8.6g2 modeling dataset.

Inputs:
    B8.6g N150 feature dataset, F5 N150 multi-forcing labels, B8.6g feature
    schema, and N150 sampling feature matrix from the B8.6g2 config.
Outputs:
    b86g2_modeling_dataset.csv and b86g2_dataset_schema.csv.
Saved metrics:
    Row count, unique cell count, target availability, feature roles, leakage
    guard status, and predictor eligibility for the compact retest dataset.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86g2_common import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    b86g_feature_schema,
    build_feature_registry,
    ensure_output_dir,
    forbidden_predictor,
    guardrails_are_set,
    load_config,
    output_path,
    parse_pipe_list,
    read_csv,
    write_csv,
)


@dataclass(frozen=True)
class DatasetResult:
    """B8.6g2 dataset result."""

    status: str
    rows: int
    cells: int
    feature_columns: int


def context_columns(config: dict[str, Any], sample: pd.DataFrame) -> list[str]:
    """Select compact context columns needed for splits and baseline features."""
    wanted = [
        "cell_id",
        "typology_label",
        "primary_role",
        "secondary_roles",
        "source_feature_completeness",
        "sampling_feature_completeness",
        "centroid_x",
        "centroid_y",
        "in_n24_completed",
        *config["baseline_feature_columns"],
    ]
    return list(dict.fromkeys([column for column in wanted if column in sample.columns]))


def validate_inputs(labels: pd.DataFrame, features: pd.DataFrame, dataset: pd.DataFrame, config: dict[str, Any]) -> None:
    """Validate B8.6g2 row/cell/target contracts."""
    primary = config["primary_target"]
    required_label_cols = ["cell_id", "forcing_day_id", "hour_sgt", primary, *config["companion_targets"]]
    missing = [column for column in required_label_cols if column not in labels.columns]
    if missing:
        raise ValueError(f"B86G2_BLOCKED_INPUT missing F5 label columns: {missing}")
    if len(labels) != int(config["expected_label_rows"]):
        raise ValueError(f"B86G2_BLOCKED_INPUT expected {config['expected_label_rows']} label rows, found {len(labels)}")
    if int(features["cell_id"].nunique()) != int(config["expected_n150_cell_count"]):
        raise ValueError("B86G2_BLOCKED_INPUT unexpected B8.6g N150 feature cell count")
    if features["cell_id"].duplicated().any():
        raise ValueError("B86G2_BLOCKED_INPUT duplicate cell_id in B8.6g N150 feature dataset")
    if len(dataset) != int(config["expected_label_rows"]):
        raise ValueError(f"B86G2_BLOCKED_INPUT expected {config['expected_label_rows']} modeling rows, found {len(dataset)}")
    if int(dataset["cell_id"].nunique()) != int(config["expected_n150_cell_count"]):
        raise ValueError("B86G2_BLOCKED_INPUT unexpected modeling unique cell count")
    for target in [primary, *config["companion_targets"]]:
        if int(dataset[target].notna().sum()) != len(dataset):
            raise ValueError(f"B86G2_BLOCKED_INPUT target {target} has missing values")
    hours = sorted(pd.to_numeric(dataset["hour_sgt"], errors="coerce").dropna().astype(int).unique().tolist())
    if hours != list(map(int, config["expected_hours"])):
        raise ValueError(f"B86G2_BLOCKED_INPUT unexpected hours {hours}")
    forcing_days = int(dataset["forcing_day_id"].nunique())
    if forcing_days != int(config["expected_forcing_days"]):
        raise ValueError(f"B86G2_BLOCKED_INPUT unexpected forcing day count {forcing_days}")


def build_dataset(config: dict[str, Any]) -> pd.DataFrame:
    """Join B8.6g N150 features to F5 labels by cell_id."""
    labels = read_csv(config["f5_pairwise_label_path"])
    features = read_csv(config["b86g_n150_feature_dataset_path"])
    sample = read_csv(config["n150_sampling_feature_matrix_path"])
    sample_context = sample[context_columns(config, sample)].drop_duplicates("cell_id")
    dataset = labels.merge(sample_context, on="cell_id", how="left", validate="many_to_one")
    dataset = dataset.merge(features, on="cell_id", how="left", validate="many_to_one")
    if "row_id" not in dataset.columns:
        dataset.insert(
            0,
            "row_id",
            dataset["cell_id"].astype(str)
            + "|"
            + dataset["forcing_day_id"].astype(str)
            + "|h"
            + dataset["hour_sgt"].astype(str)
            + "|b86g2_feature_retest",
        )
    dataset["b86g2_scenario_context"] = "overhead_as_canopy_minus_base"
    dataset["b86g2_label_source"] = "F5 N150 multi-forcing SOLWEIG-derived compact Tmrt delta labels"
    anchors = set(config["diagnostic_cells"]["anchor_cells"])
    neutrals = set(config["diagnostic_cells"]["known_neutral_cells"])
    unstable = set(config["diagnostic_cells"]["unstable_cells"])
    dataset["anchor_cell_flag"] = dataset["cell_id"].astype(str).isin(anchors)
    dataset["known_neutral_cell_flag"] = dataset["cell_id"].astype(str).isin(neutrals)
    dataset["unstable_cell_flag"] = dataset["cell_id"].astype(str).isin(unstable)
    dataset["neutral_abs_le_threshold"] = pd.to_numeric(dataset[config["primary_target"]], errors="coerce").abs() <= float(
        config["neutral_threshold_c"]
    )
    dataset["meaningful_cooling_lt_threshold"] = pd.to_numeric(dataset[config["primary_target"]], errors="coerce") < -float(
        config["neutral_threshold_c"]
    )
    dataset["claim_boundary"] = CLAIM_BOUNDARY
    validate_inputs(labels, features, dataset, config)
    return dataset


def dataset_schema(dataset: pd.DataFrame, registry: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create dataset schema and predictor role audit."""
    targets = {config["primary_target"], *config["companion_targets"]}
    target_derived = {"base_tmrt_p90_c", "overhead_tmrt_p90_c", "within_slice_rank", "rank_direction"}
    split_meta = {"cell_id", "forcing_day_id", "hour_sgt", "typology_label", "centroid_x", "centroid_y"}
    diagnostic_meta = {
        "anchor_cell_flag",
        "known_neutral_cell_flag",
        "unstable_cell_flag",
        "neutral_abs_le_threshold",
        "meaningful_cooling_lt_threshold",
    }
    feature_cols: set[str] = set()
    for value in registry["feature_columns"].fillna(""):
        feature_cols.update(parse_pipe_list(value))
    rows: list[dict[str, Any]] = []
    for column in dataset.columns:
        if column in targets:
            role = "target"
            predictor_allowed = False
        elif column in target_derived:
            role = "target_derived_excluded"
            predictor_allowed = False
        elif column in feature_cols and not forbidden_predictor(column):
            role = "predictor"
            predictor_allowed = True
        elif column in split_meta:
            role = "split_metadata"
            predictor_allowed = column == "hour_sgt" and column in feature_cols
        elif column in diagnostic_meta:
            role = "diagnostic_metadata"
            predictor_allowed = False
        else:
            role = "metadata_or_unused_context"
            predictor_allowed = False
        forbidden = forbidden_predictor(column)
        rows.append(
            {
                "column_name": column,
                "dtype": str(dataset[column].dtype),
                "non_null_count": int(dataset[column].notna().sum()),
                "missing_fraction": float(dataset[column].isna().mean()),
                "unique_count": int(dataset[column].nunique(dropna=True)),
                "role": role,
                "predictor_allowed": bool(predictor_allowed and not forbidden),
                "leakage_guard": "PASS" if not (predictor_allowed and forbidden) else "EXCLUDED_FORBIDDEN",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> DatasetResult:
    """Build and write the B8.6g2 modeling dataset and schema."""
    config = load_config(config_path)
    guardrails_are_set(config)
    ensure_output_dir(config)
    dataset = build_dataset(config)
    registry = build_feature_registry(dataset, b86g_feature_schema(config), config)
    schema = dataset_schema(dataset, registry, config)
    write_csv(dataset, output_path(config, "modeling_dataset"))
    write_csv(schema, output_path(config, "dataset_schema"))
    feature_columns = set()
    for value in registry["feature_columns"].fillna(""):
        feature_columns.update(parse_pipe_list(value))
    return DatasetResult("B86G2_DATASET_READY", len(dataset), int(dataset["cell_id"].nunique()), len(feature_columns))


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Build B8.6g2 modeling dataset by joining B8.6g N150 features to F5 labels by cell_id."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
