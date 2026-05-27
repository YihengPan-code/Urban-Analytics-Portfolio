"""Build the B8.6c hardened compact surrogate dataset.

Inputs:
    configs/v12/systemb_b86c_feature_hardening.yaml
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_pairwise_delta_by_cell_hour.csv
    outputs/v12_systemb_n150_sample_design/n150_sampling_feature_matrix.csv
    outputs/v12_systemb_n150_sample_design/n150_candidate_universe.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_safe_feature_catalog.csv
    B8.5-F4 compact anchor, neutral, and unstable cell CSVs

Outputs:
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_hardened_surrogate_dataset.csv

Saved metrics:
    Strict F5 label row/cell/forcing-day/hour checks, target availability,
    joined compact feature coverage, F4 diagnostic flags, and safe interaction
    feature creation status.

This script reads compact CSV inputs only. It does not run QGIS or SOLWEIG,
does not read raster files, does not open or copy svfs.zip, does not create
AOI-wide prediction, does not convert Tmrt to WBGT, and does not create WBGT,
hazard_score, risk_score, B9, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86c_feature_inventory import DEFAULT_CONFIG, read_config, rel_path, repo_path


@dataclass(frozen=True)
class DatasetResult:
    """Compact return record for the B8.6c dataset step."""

    status: str
    dataset_rows: int
    dataset_columns: int
    unique_cells: int
    forcing_days: int
    hours: int
    target_count: int
    safe_feature_columns_joined: int
    interaction_columns_created: int


def read_csv(path: Path) -> pd.DataFrame:
    """Read a compact CSV while preserving cell IDs."""
    return pd.read_csv(path, dtype={"cell_id": "string"})


def validate_labels(labels: pd.DataFrame, config: dict[str, Any]) -> None:
    """Validate strict F5 compact label invariants for B8.6c."""
    targets = [config["targets"]["primary"], *config["targets"]["companion"]]
    required = {"cell_id", "forcing_day_id", "hour_sgt", *targets}
    missing = sorted(required - set(labels.columns))
    if missing:
        raise ValueError(f"F5 pairwise labels are missing required columns: {missing}")
    expected = config["expected"]
    observed_hours = set(pd.to_numeric(labels["hour_sgt"], errors="coerce").dropna().astype(int).unique())
    expected_hours = set(int(hour) for hour in expected["hours_sgt"])
    checks = {
        "rows": (len(labels), int(expected["f5_pairwise_rows"])),
        "cells": (labels["cell_id"].nunique(), int(expected["n150_cells"])),
        "forcing_days": (labels["forcing_day_id"].nunique(), int(expected["forcing_day_count"])),
        "hours": (len(observed_hours), len(expected_hours)),
    }
    for name, (observed, required_count) in checks.items():
        if int(observed) != int(required_count):
            raise ValueError(f"F5 labels expected {required_count} {name}; found {observed}.")
    if observed_hours != expected_hours:
        raise ValueError(f"F5 label hours must be {sorted(expected_hours)}; found {sorted(observed_hours)}.")


def normalize_labels(labels: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Normalize F5 labels to a B8.6c row-level target table."""
    validate_labels(labels, config)
    targets = [config["targets"]["primary"], *config["targets"]["companion"]]
    out = labels.copy()
    out["cell_id"] = out["cell_id"].astype(str)
    out["forcing_day_id"] = out["forcing_day_id"].astype(str)
    out["hour_sgt"] = pd.to_numeric(out["hour_sgt"], errors="coerce").astype(int)
    out["scenario_context"] = config["expected"]["scenario_context"]
    out["row_id"] = (
        out["cell_id"]
        + "|"
        + out["forcing_day_id"]
        + "|h"
        + out["hour_sgt"].astype(str)
        + "|"
        + out["scenario_context"]
    )
    out["b86c_label_source"] = "b85_f5_pairwise_delta_by_cell_hour"
    out["target_definition"] = "delta_tmrt_p90_c = overhead_as_canopy - base; SOLWEIG Tmrt label only."
    keep = [
        "row_id",
        "cell_id",
        "forcing_day_id",
        "hour_sgt",
        "scenario_context",
        *targets,
        "label_source",
        "legacy_single_forcing_comparison_source",
        "b86c_label_source",
        "target_definition",
        "notes",
    ]
    return out[[column for column in keep if column in out.columns]].copy()


def safe_feature_columns(config: dict[str, Any]) -> pd.DataFrame:
    """Load the safe feature catalog written by the inventory step."""
    path = repo_path(config["outputs"]["safe_feature_catalog"])
    if not path.exists():
        raise FileNotFoundError(f"Missing safe feature catalog: {path}")
    return pd.read_csv(path)


def source_columns_for_catalog(catalog: pd.DataFrame, source_table: str) -> list[tuple[str, str]]:
    """Return source and dataset column pairs for one compact feature source."""
    subset = catalog.loc[
        (catalog["source_table"].astype(str) == source_table)
        & catalog["predictor_allowed"].astype(bool)
    ].copy()
    return list(zip(subset["column_name"].astype(str), subset["dataset_column"].astype(str)))


def build_feature_frame(config: dict[str, Any], label_cells: set[str]) -> tuple[pd.DataFrame, int]:
    """Build one row per cell of safe compact features from both sources."""
    catalog = safe_feature_columns(config)
    contract = config["feature_contract"]

    sample_path = repo_path(config["inputs"]["feature_sources"][contract["sampling_feature_source"]])
    candidate_path = repo_path(config["inputs"]["feature_sources"][contract["candidate_universe_source"]])
    sample = read_csv(sample_path)
    candidate = read_csv(candidate_path)
    for frame, name in [(sample, "n150_sampling_feature_matrix"), (candidate, "n150_candidate_universe")]:
        if "cell_id" not in frame.columns:
            raise ValueError(f"{name} has no cell_id column.")
        coverage = len(label_cells & set(frame["cell_id"].dropna().astype(str)))
        if coverage != int(config["expected"]["n150_cells"]):
            raise ValueError(f"{name} covers {coverage} F5 label cells, expected 150.")

    sample_pairs = source_columns_for_catalog(catalog, contract["sampling_feature_source"])
    candidate_pairs = source_columns_for_catalog(catalog, contract["candidate_universe_source"])

    metadata = [
        column
        for column in contract["metadata_columns"]
        if column in sample.columns and column not in {"row_id", "cell_id"}
    ]
    sample_keep = ["cell_id", *metadata, *[source for source, _ in sample_pairs if source in sample.columns]]
    sample_out = sample[sample_keep].drop_duplicates("cell_id").copy()

    candidate_keep = ["cell_id", *[source for source, _ in candidate_pairs if source in candidate.columns]]
    candidate_out = candidate[candidate_keep].drop_duplicates("cell_id").copy()
    rename_map = {source: dataset_col for source, dataset_col in candidate_pairs if source in candidate_out.columns}
    candidate_out = candidate_out.rename(columns=rename_map)

    features = sample_out.merge(candidate_out, on="cell_id", how="left", validate="one_to_one")
    joined_count = len(set(features.columns) - {"cell_id"})
    return features, joined_count


def create_interactions(dataset: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, int]:
    """Create configured safe interaction terms when both source columns exist."""
    out = dataset.copy()
    created = 0
    for name, pair in config["interactions"].items():
        left, right = pair
        if left not in out.columns or right not in out.columns:
            continue
        left_values = pd.to_numeric(out[left], errors="coerce")
        right_values = pd.to_numeric(out[right], errors="coerce")
        if left_values.notna().sum() == 0 or right_values.notna().sum() == 0:
            continue
        out[name] = left_values * right_values
        created += 1
    return out, created


def cell_list(path: Path) -> set[str]:
    """Read a compact F4 cell-list CSV."""
    if not path.exists():
        return set()
    frame = pd.read_csv(path, dtype={"cell_id": "string"})
    return set(frame["cell_id"].dropna().astype(str)) if "cell_id" in frame.columns else set()


def add_diagnostic_flags(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Attach F4 anchor, neutral-boundary, and unstable-review flags."""
    out = dataset.copy()
    f4 = config["inputs"]["f4_context"]
    anchors = set(config["diagnostic_cells"]["robust_priority_anchors"]) | cell_list(repo_path(f4["robust_priority_cells"]))
    neutral = cell_list(repo_path(f4["neutral_boundary_cells"]))
    unstable = cell_list(repo_path(f4["unstable_priority_cells"]))
    out["robust_anchor_flag"] = out["cell_id"].astype(str).isin(anchors)
    out["neutral_boundary_flag"] = out["cell_id"].astype(str).isin(neutral)
    out["unstable_review_flag"] = out["cell_id"].astype(str).isin(unstable)
    return out


def build_dataset(config: dict[str, Any]) -> tuple[pd.DataFrame, int, int]:
    """Build the hardened F5 label-feature dataset."""
    labels = normalize_labels(read_csv(repo_path(config["inputs"]["label_source"]["f5_pairwise_delta"])), config)
    label_cells = set(labels["cell_id"].astype(str).unique())
    features, joined_count = build_feature_frame(config, label_cells)
    dataset = labels.merge(features, on="cell_id", how="left", validate="many_to_one")
    dataset, interaction_count = create_interactions(dataset, config)
    dataset = add_diagnostic_flags(dataset, config)
    dataset["cell_id_predictor_status"] = "group_metadata_only"
    dataset["forcing_day_predictor_status"] = "split_metadata_only"
    dataset["claim_boundary"] = "SOLWEIG-derived Tmrt labels only; not WBGT, risk, observed truth, B9, or AOI-wide prediction."
    dataset = dataset.sort_values(["cell_id", "forcing_day_id", "hour_sgt"]).reset_index(drop=True)
    return dataset, joined_count, interaction_count


def empty_output(config: dict[str, Any], status: str) -> DatasetResult:
    """Write an empty output when required compact inputs are blocked."""
    pd.DataFrame().to_csv(repo_path(config["outputs"]["hardened_surrogate_dataset"]), index=False)
    return DatasetResult(status, 0, 0, 0, 0, 0, 0, 0, 0)


def run(config_path: Path = DEFAULT_CONFIG) -> DatasetResult:
    """Build and write the B8.6c hardened compact surrogate dataset."""
    config = read_config(config_path)
    repo_path(config["outputs"]["out_dir"]).mkdir(parents=True, exist_ok=True)
    try:
        dataset, safe_count, interaction_count = build_dataset(config)
    except (FileNotFoundError, ValueError) as exc:
        print(json.dumps({"dataset_blocker": str(exc)}, ensure_ascii=False))
        return empty_output(config, "B86C_BLOCKED_INPUT")

    dataset.to_csv(repo_path(config["outputs"]["hardened_surrogate_dataset"]), index=False)
    targets = [config["targets"]["primary"], *config["targets"]["companion"]]
    return DatasetResult(
        status="B86C_DATASET_READY",
        dataset_rows=int(len(dataset)),
        dataset_columns=int(dataset.shape[1]),
        unique_cells=int(dataset["cell_id"].nunique()),
        forcing_days=int(dataset["forcing_day_id"].nunique()),
        hours=int(dataset["hour_sgt"].nunique()),
        target_count=int(sum(target in dataset.columns for target in targets)),
        safe_feature_columns_joined=int(safe_count),
        interaction_columns_created=int(interaction_count),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Build the B8.6c hardened surrogate dataset from F5 compact labels "
            "and leakage-safe compact features."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6c YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
