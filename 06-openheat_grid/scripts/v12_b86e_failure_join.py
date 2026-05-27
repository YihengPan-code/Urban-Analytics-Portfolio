"""Join B8.6d OOF failures with compact labels and safe cell features.

Inputs:
    B8.6d OOF predictions, F5 pairwise labels, B8.6c hardened compact dataset,
    B8.6c safe feature catalog, and N150 compact feature metadata from the
    B8.6e config.
Outputs:
    b86e_failure_joined_dataset.csv
Saved metrics:
    Row-level true/predicted SOLWEIG-derived Tmrt-delta errors, split metadata,
    spatial bin, typology, anchor/neutral/unstable flags, and safe compact
    feature columns. No AOI-wide prediction, WBGT, hazard, risk, raster, QGIS,
    SOLWEIG, B9, or System A/B coupling output is created.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86e_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    add_spatial_bin,
    cell_feature_frame,
    full_safe_compact_columns,
    input_path,
    load_config,
    output_path,
    read_csv,
    selected_oof_predictions,
    write_csv,
)


@dataclass(frozen=True)
class JoinResult:
    """Failure join result."""

    status: str
    rows: int
    cells: int
    safe_features: int


def marker_frame(config: dict[str, Any]) -> pd.DataFrame:
    """Build one-row-per-cell marker and feature table."""
    cells = cell_feature_frame(config)
    cells = add_spatial_bin(cells)
    safe_cols = full_safe_compact_columns(config, cells, include_coordinate=False)
    keep = [
        "cell_id",
        "typology_label",
        "centroid_x",
        "centroid_y",
        "centroid_x_normalized",
        "centroid_y_normalized",
        "spatial_bin",
        *safe_cols,
    ]
    keep = list(dict.fromkeys([column for column in keep if column in cells.columns]))
    out = cells[keep].copy()
    out["anchor_flag"] = out["cell_id"].astype(str).isin(set(config["anchor_cells"]))
    out["known_neutral_flag"] = out["cell_id"].astype(str).isin(set(config["known_neutral_cells"]))
    out["unstable_flag"] = out["cell_id"].astype(str).isin(set(config["known_unstable_cells"]))
    return out


def build_failure_join(config: dict[str, Any]) -> tuple[pd.DataFrame, int]:
    """Build the joined B8.6e row-level failure table."""
    threshold = float(config["neutral_threshold_c"])
    primary = str(config["primary_target"])
    oof = selected_oof_predictions(config)
    if oof.empty:
        raise ValueError("Selected B8.6d OOF prediction table is empty.")
    labels = read_csv(input_path(config, "f5_pairwise_label_path"))
    label_keep = [column for column in ["cell_id", "forcing_day_id", "hour_sgt", primary] if column in labels.columns]
    labels = labels[label_keep].rename(columns={primary: "f5_true_delta_tmrt_p90_c"})
    keys = ["cell_id", "forcing_day_id", "hour_sgt"]
    merged = oof.merge(labels, on=keys, how="left", validate="many_to_one")
    markers = marker_frame(config)
    safe_features = [
        column
        for column in full_safe_compact_columns(config, markers, include_coordinate=False)
        if column in markers.columns
    ]
    merged = merged.merge(markers, on="cell_id", how="left", validate="many_to_one", suffixes=("", "_cell"))

    true_source = "true_delta" if "true_delta" in merged.columns else primary
    if true_source not in merged.columns:
        true_source = "f5_true_delta_tmrt_p90_c"
    merged["true_delta_tmrt_p90_c"] = pd.to_numeric(merged[true_source], errors="coerce")
    merged["predicted_delta_tmrt_p90_c"] = pd.to_numeric(merged["pred_combined_delta"], errors="coerce")
    merged["signed_error"] = merged["predicted_delta_tmrt_p90_c"] - merged["true_delta_tmrt_p90_c"]
    merged["abs_error"] = merged["signed_error"].abs()
    merged["predicted_class"] = merged["pred_stage1_class"].astype(str)
    merged["true_neutral_flag"] = merged["true_delta_tmrt_p90_c"].abs() <= threshold
    merged["predicted_meaningful_cooling_flag"] = merged["predicted_class"].eq("meaningful_cooling")
    merged["false_promotion_flag"] = merged["true_neutral_flag"] & merged["predicted_meaningful_cooling_flag"]
    merged["false_neutral_flag"] = (merged["true_delta_tmrt_p90_c"] < -threshold) & merged["predicted_class"].eq("neutral")
    if "typology_label" in merged.columns:
        merged["typology"] = merged["typology_label"]
    elif "typology_label_cell" in merged.columns:
        merged["typology"] = merged["typology_label_cell"]
    else:
        merged["typology"] = "unknown"
    out_cols = [
        "cell_id",
        "forcing_day_id",
        "hour_sgt",
        "true_delta_tmrt_p90_c",
        "predicted_delta_tmrt_p90_c",
        "abs_error",
        "signed_error",
        "predicted_class",
        "true_neutral_flag",
        "predicted_meaningful_cooling_flag",
        "false_promotion_flag",
        "false_neutral_flag",
        "split_family",
        "split_name",
        "fold_id",
        "spatial_bin",
        "typology",
        "anchor_flag",
        "known_neutral_flag",
        "unstable_flag",
        "centroid_x",
        "centroid_y",
        "centroid_x_normalized",
        "centroid_y_normalized",
        *safe_features,
    ]
    if "seed" in merged.columns:
        out_cols.insert(out_cols.index("spatial_bin"), "seed")
    out_cols = list(dict.fromkeys([column for column in out_cols if column in merged.columns]))
    out = merged[out_cols].copy()
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out, len(safe_features)


def run(config_path: Path = DEFAULT_CONFIG) -> JoinResult:
    """Write the B8.6e joined failure dataset."""
    config = load_config(config_path)
    joined, feature_count = build_failure_join(config)
    write_csv(joined, output_path(config, "failure_joined_dataset"))
    return JoinResult(
        status="B86E_FAILURE_JOIN_READY",
        rows=len(joined),
        cells=int(joined["cell_id"].nunique()),
        safe_features=feature_count,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Join selected B8.6d OOF predictions to compact labels, spatial/typology metadata, "
            "diagnostic cell markers, and B8.6c safe compact features."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
