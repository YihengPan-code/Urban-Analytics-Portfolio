"""Audit B8.6e spatial, typology, anchor, neutral, and feature-shift failures.

Inputs:
    b86e_failure_joined_dataset.csv and the B8.6e config.
Outputs:
    spatial holdout summary, spatial-bin inventory, typology x spatial cross
    failure table, worst-cell context, anchor-underprediction context,
    neutral false-promotion context, and feature distribution shift CSVs.
Saved metrics:
    Group-level MAE, Spearman, top10 overlap, neutral accuracy, false promotion
    and false neutral rates, event support, compact feature standardized
    differences, missingness, and out-of-domain flags. No target-derived
    feature is used for feature shift diagnostics.
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
    failure_label,
    full_safe_compact_columns,
    load_config,
    output_path,
    read_csv,
    summarize_prediction_group,
    top_fraction_overlap,
    write_csv,
)


@dataclass(frozen=True)
class SpatialAuditResult:
    """Spatial audit result."""

    status: str
    spatial_bins: int
    cross_rows: int
    shifted_features: int


def spatial_holdout(frame: pd.DataFrame) -> pd.DataFrame:
    """Return selected spatial-holdout rows."""
    return frame.loc[frame["split_family"].astype(str).eq("spatial_holdout")].copy()


def summarize_by_spatial_bin(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Summarize spatial holdout failures by deterministic spatial bin."""
    rows: list[dict[str, Any]] = []
    for spatial_bin, group in frame.groupby("spatial_bin", dropna=False):
        row = {"spatial_bin": spatial_bin}
        row.update(summarize_prediction_group(group, config))
        row["suspected_failure_type"] = failure_label(row, config)
        row["claim_boundary"] = CLAIM_BOUNDARY
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["Spearman", "top10pct_overlap", "mean_abs_error"], ascending=[True, True, False])


def spatial_inventory(frame: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    """Create per-cell context inventory within spatial bins."""
    rows: list[dict[str, Any]] = []
    failure_map = dict(zip(summary["spatial_bin"].astype(str), summary["suspected_failure_type"].astype(str)))
    grouped = frame.groupby(["spatial_bin", "cell_id"], dropna=False)
    for (spatial_bin, cell_id), group in grouped:
        rows.append(
            {
                "spatial_bin": spatial_bin,
                "cell_id": cell_id,
                "typology": group["typology"].mode().iloc[0] if "typology" in group and not group["typology"].mode().empty else "",
                "n_rows": int(len(group)),
                "mean_true_delta_tmrt_p90_c": float(group["true_delta_tmrt_p90_c"].mean()),
                "mean_predicted_delta_tmrt_p90_c": float(group["predicted_delta_tmrt_p90_c"].mean()),
                "mean_abs_error": float(group["abs_error"].mean()),
                "mean_signed_error": float(group["signed_error"].mean()),
                "false_promotion_rate": float(group["false_promotion_flag"].mean()),
                "false_neutral_rate": float(group["false_neutral_flag"].mean()),
                "anchor_flag": bool(group["anchor_flag"].any()),
                "known_neutral_flag": bool(group["known_neutral_flag"].any()),
                "unstable_flag": bool(group["unstable_flag"].any()),
                "suspected_failure_type": failure_map.get(str(spatial_bin), "not-flagged"),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows).sort_values(["mean_abs_error", "false_promotion_rate"], ascending=False)


def typology_spatial_cross(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Summarize typology x spatial-bin failure modes."""
    threshold = float(config["neutral_threshold_c"])
    rows: list[dict[str, Any]] = []
    for (typology, spatial_bin), group in frame.groupby(["typology", "spatial_bin"], dropna=False):
        base = summarize_prediction_group(group, config)
        support = pd.to_numeric(group["true_delta_tmrt_p90_c"], errors="coerce")
        predicted = pd.to_numeric(group["predicted_delta_tmrt_p90_c"], errors="coerce")
        row = {
            "typology": typology,
            "spatial_bin": spatial_bin,
            "n_rows": int(len(group)),
            "n_cells": int(group["cell_id"].nunique()),
            "meaningful_cooling_support": int((support < -threshold).sum()),
            "neutral_support": int((support.abs() <= threshold).sum()),
            "median_true_delta_tmrt_p90_c": float(support.median()),
            "median_predicted_delta_tmrt_p90_c": float(predicted.median()),
            "false_promotion_rate": base["false_promotion_rate"],
            "top10pct_overlap": top_fraction_overlap(group, "true_delta_tmrt_p90_c", "predicted_delta_tmrt_p90_c", 0.10),
            "mean_abs_error": base["mean_abs_error"],
            "Spearman": base["Spearman"],
        }
        labels = []
        if int(row["n_cells"]) < int(config.get("sample_support_low_cell_threshold", 10)):
            labels.append("sample-support-low")
        if row["false_promotion_rate"] == row["false_promotion_rate"] and row["false_promotion_rate"] >= float(
            config["neutral_false_promotion_warn_threshold"]
        ):
            labels.append("neutral-false-promotion")
        if row["Spearman"] == row["Spearman"] and row["Spearman"] < float(config["spatial_failure_spearman_threshold"]):
            labels.append("feature-distribution-shift")
        if row["top10pct_overlap"] == row["top10pct_overlap"] and row["top10pct_overlap"] < float(
            config["spatial_failure_top10_threshold"]
        ):
            labels.append("target-role-mismatch")
        row["failure_label"] = "|".join(labels) if labels else "not-flagged"
        row["claim_boundary"] = CLAIM_BOUNDARY
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["failure_label", "Spearman", "top10pct_overlap"], ascending=[True, True, True])


def worst_cell_context(frame: pd.DataFrame) -> pd.DataFrame:
    """Create worst-cell context from spatial holdout rows."""
    rows: list[dict[str, Any]] = []
    for cell_id, group in frame.groupby("cell_id", dropna=False):
        rows.append(
            {
                "cell_id": cell_id,
                "spatial_bin": group["spatial_bin"].mode().iloc[0],
                "typology": group["typology"].mode().iloc[0],
                "n_rows": int(len(group)),
                "mean_true_delta_tmrt_p90_c": float(group["true_delta_tmrt_p90_c"].mean()),
                "mean_predicted_delta_tmrt_p90_c": float(group["predicted_delta_tmrt_p90_c"].mean()),
                "mean_abs_error": float(group["abs_error"].mean()),
                "mean_signed_error": float(group["signed_error"].mean()),
                "max_abs_error": float(group["abs_error"].max()),
                "false_promotion_rate": float(group["false_promotion_flag"].mean()),
                "false_neutral_rate": float(group["false_neutral_flag"].mean()),
                "anchor_flag": bool(group["anchor_flag"].any()),
                "known_neutral_flag": bool(group["known_neutral_flag"].any()),
                "unstable_flag": bool(group["unstable_flag"].any()),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows).sort_values("mean_abs_error", ascending=False).head(50)


def anchor_context(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize anchor underprediction in each split family."""
    anchor = frame.loc[frame["anchor_flag"].astype(bool)].copy()
    rows: list[dict[str, Any]] = []
    for (cell_id, split_family), group in anchor.groupby(["cell_id", "split_family"], dropna=False):
        cooling_underprediction = (group["true_delta_tmrt_p90_c"] < -0.05) & (group["signed_error"] > 0.05)
        rows.append(
            {
                "cell_id": cell_id,
                "split_family": split_family,
                "spatial_bin": group["spatial_bin"].mode().iloc[0],
                "typology": group["typology"].mode().iloc[0],
                "n_rows": int(len(group)),
                "mean_true_delta_tmrt_p90_c": float(group["true_delta_tmrt_p90_c"].mean()),
                "mean_predicted_delta_tmrt_p90_c": float(group["predicted_delta_tmrt_p90_c"].mean()),
                "mean_abs_error": float(group["abs_error"].mean()),
                "mean_signed_error": float(group["signed_error"].mean()),
                "underprediction_rate_for_cooling": float(cooling_underprediction.mean()),
                "false_neutral_rate": float(group["false_neutral_flag"].mean()),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows).sort_values(["split_family", "mean_abs_error"], ascending=[True, False])


def neutral_false_promotion_context(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize true-neutral rows promoted as meaningful cooling."""
    neutral = frame.loc[frame["true_neutral_flag"].astype(bool)].copy()
    rows: list[dict[str, Any]] = []
    for (cell_id, split_family), group in neutral.groupby(["cell_id", "split_family"], dropna=False):
        rows.append(
            {
                "cell_id": cell_id,
                "split_family": split_family,
                "spatial_bin": group["spatial_bin"].mode().iloc[0],
                "typology": group["typology"].mode().iloc[0],
                "n_rows": int(len(group)),
                "known_neutral_flag": bool(group["known_neutral_flag"].any()),
                "false_promotion_rate": float(group["false_promotion_flag"].mean()),
                "mean_true_delta_tmrt_p90_c": float(group["true_delta_tmrt_p90_c"].mean()),
                "mean_predicted_delta_tmrt_p90_c": float(group["predicted_delta_tmrt_p90_c"].mean()),
                "mean_abs_error": float(group["abs_error"].mean()),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values(["false_promotion_rate", "mean_abs_error"], ascending=False).head(100)


def distribution_shift(joined: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Compute safe numeric compact feature distribution shifts by spatial bin and typology."""
    cell_rows = joined.drop_duplicates("cell_id").copy()
    feature_cols = full_safe_compact_columns(config, cell_rows, include_coordinate=False)
    numeric = [
        column
        for column in feature_cols
        if column in cell_rows.columns and pd.to_numeric(cell_rows[column], errors="coerce").notna().sum() > 0
    ]
    rows: list[dict[str, Any]] = []
    for axis in ["spatial_bin", "typology"]:
        if axis not in cell_rows.columns:
            continue
        for value, group in cell_rows.groupby(axis, dropna=False):
            rest = cell_rows.loc[~cell_rows.index.isin(group.index)].copy()
            for feature in numeric:
                values = pd.to_numeric(group[feature], errors="coerce")
                rest_values = pd.to_numeric(rest[feature], errors="coerce")
                if values.notna().sum() == 0 or rest_values.notna().sum() == 0:
                    continue
                pooled = float(np.sqrt((values.var(ddof=0) + rest_values.var(ddof=0)) / 2.0))
                standardized = float((values.mean() - rest_values.mean()) / pooled) if pooled else 0.0
                out_of_domain = bool(values.min() < rest_values.min() or values.max() > rest_values.max())
                rows.append(
                    {
                        "distribution_axis": axis,
                        "group_value": value,
                        "reference_group": f"rest_of_{axis}",
                        "feature": feature,
                        "n_cells": int(group["cell_id"].nunique()),
                        "mean": float(values.mean()),
                        "std": float(values.std(ddof=0)),
                        "min": float(values.min()),
                        "max": float(values.max()),
                        "rest_mean": float(rest_values.mean()),
                        "rest_std": float(rest_values.std(ddof=0)),
                        "standardized_difference_vs_rest": standardized,
                        "missing_fraction": float(values.isna().mean()),
                        "out_of_domain_flag": out_of_domain,
                        "claim_boundary": CLAIM_BOUNDARY,
                    }
                )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["abs_standardized_difference"] = out["standardized_difference_vs_rest"].abs()
    return out.sort_values(["out_of_domain_flag", "abs_standardized_difference"], ascending=[False, False])


def run(config_path: Path = DEFAULT_CONFIG) -> SpatialAuditResult:
    """Run and write all spatial-domain audit outputs."""
    config = load_config(config_path)
    joined = read_csv(output_path(config, "failure_joined_dataset"))
    spatial = spatial_holdout(joined)
    summary = summarize_by_spatial_bin(spatial, config)
    inventory = spatial_inventory(spatial, summary)
    cross = typology_spatial_cross(spatial, config)
    worst = worst_cell_context(spatial)
    anchor = anchor_context(joined)
    neutral = neutral_false_promotion_context(joined)
    shift = distribution_shift(joined, config)
    write_csv(summary, output_path(config, "spatial_holdout_failure_summary"))
    write_csv(inventory, output_path(config, "spatial_bin_failure_inventory"))
    write_csv(cross, output_path(config, "typology_spatial_cross_failure"))
    write_csv(worst, output_path(config, "worst_cell_error_context"))
    write_csv(anchor, output_path(config, "anchor_underprediction_context"))
    write_csv(neutral, output_path(config, "neutral_false_promotion_context"))
    write_csv(shift, output_path(config, "feature_distribution_shift"))
    return SpatialAuditResult(
        status="B86E_SPATIAL_DOMAIN_AUDIT_READY",
        spatial_bins=int(summary["spatial_bin"].nunique()) if not summary.empty else 0,
        cross_rows=len(cross),
        shifted_features=int((shift.get("abs_standardized_difference", pd.Series(dtype=float)) >= 1.0).sum()),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run B8.6e spatial-domain and feature-distribution failure audit.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
