"""Run B8.6f abstention / uncertainty gate diagnostics on compact OOF rows.

Inputs:
    B8.6d OOF predictions, B8.6e failure diagnostics, current N150 compact
    features, and the B8.6f config.
Outputs:
    b86f_abstention_rule_catalog.csv and
    b86f_abstention_gate_metrics.csv.
Saved metrics:
    Moderate and strict diagnostic abstention rules, retained and abstained
    fractions, retained-subset MAE/Spearman/top10pct, neutral false-promotion,
    anchor underprediction, anchor and known-neutral retained/abstained counts,
    and future dry-run preflight suitability. This script uses only existing
    compact predictions and diagnostics. It creates no AOI-wide prediction,
    B9 output, WBGT, hazard, risk, raster, QGIS/SOLWEIG, or System A/B
    coupling output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86f_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    as_float,
    bool_value,
    current_cell_features,
    input_path,
    load_config,
    n150_distance_context,
    output_path,
    prediction_metrics,
    read_csv,
    write_csv,
)


@dataclass(frozen=True)
class AbstentionGateResult:
    """Abstention gate diagnostic result."""

    status: str
    rules: int
    metric_rows: int


def weak_spatial_bins(config: dict[str, Any]) -> set[str]:
    """Return weak spatial bins from B8.6e summary."""
    spatial = read_csv(input_path(config, "b86e_spatial_failure_path"))
    weak = spatial.loc[
        (pd.to_numeric(spatial["Spearman"], errors="coerce") < float(config["spatial_failure_spearman_threshold"]))
        | (pd.to_numeric(spatial["top10pct_overlap"], errors="coerce") < float(config["spatial_failure_top10_threshold"])),
        "spatial_bin",
    ]
    return set(weak.astype(str))


def rule_catalog(config: dict[str, Any]) -> pd.DataFrame:
    """Build the abstention rule catalog."""
    threshold = config["abstention_thresholds"]
    rows = [
        {
            "gate_level": "moderate",
            "rule_id": "high_feature_distance",
            "condition": f"nearest N150 non-coordinate feature-space distance percentile >= {threshold['high_feature_distance_percentile']}",
            "action": "abstain",
            "diagnostic_boundary": "feature-space OOD diagnostic only",
        },
        {
            "gate_level": "moderate",
            "rule_id": "weak_spatial_bin_no_supporting_neighbour",
            "condition": "weak B8.6e spatial bin and nearest-N150 distance percentile above high-distance threshold",
            "action": "abstain",
            "diagnostic_boundary": "spatial-holdout safety diagnostic only",
        },
        {
            "gate_level": "moderate",
            "rule_id": "low_typology_support",
            "condition": f"typology support < {threshold['low_typology_support_min_cells']} current N150 cells",
            "action": "abstain",
            "diagnostic_boundary": "sample-support diagnostic only",
        },
        {
            "gate_level": "moderate",
            "rule_id": "known_gap_family_severe",
            "condition": "severe anchor, severe neutral false-promotion, or known unstable cell family applies",
            "action": "abstain",
            "diagnostic_boundary": "known failure family diagnostic only",
        },
        {
            "gate_level": "moderate",
            "rule_id": "predicted_cooling_high_false_promotion_context",
            "condition": "predicted meaningful cooling and cell-level neutral false-promotion context is high",
            "action": "abstain_or_flag",
            "diagnostic_boundary": "neutral-boundary safety diagnostic only",
        },
        {
            "gate_level": "strict",
            "rule_id": "strict_feature_distance",
            "condition": "nearest N150 non-coordinate feature-space distance percentile >= 0.75",
            "action": "abstain",
            "diagnostic_boundary": "stricter diagnostic variant",
        },
        {
            "gate_level": "strict",
            "rule_id": "strict_weak_spatial_or_known_gap",
            "condition": "weak spatial bin with sparse support or any B8.6e known gap family",
            "action": "abstain",
            "diagnostic_boundary": "stricter diagnostic variant",
        },
    ]
    out = pd.DataFrame(rows)
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def cell_failure_context(config: dict[str, Any]) -> pd.DataFrame:
    """Create cell-level failure context for abstention diagnostics."""
    distances = n150_distance_context(config)
    inventory = read_csv(input_path(config, "b86e_spatial_bin_inventory_path"))
    anchor = read_csv(input_path(config, "b86e_anchor_context_path"))
    neutral = read_csv(input_path(config, "b86e_neutral_context_path"))
    current = current_cell_features(config)
    typology_counts = current.get("typology_label", pd.Series(dtype=str)).astype(str).value_counts()
    inventory_cell = inventory.sort_values("mean_abs_error", ascending=False).drop_duplicates("cell_id")
    context = distances.merge(
        inventory_cell[
            [
                "cell_id",
                "spatial_bin",
                "typology",
                "mean_abs_error",
                "false_promotion_rate",
                "false_neutral_rate",
                "suspected_failure_type",
            ]
        ].rename(
            columns={
                "spatial_bin": "b86e_spatial_bin",
                "typology": "b86e_typology",
                "mean_abs_error": "b86e_cell_mean_abs_error",
                "false_promotion_rate": "b86e_cell_false_promotion_rate",
                "false_neutral_rate": "b86e_cell_false_neutral_rate",
            }
        ),
        on="cell_id",
        how="left",
    )
    if "typology_label" not in context.columns:
        context["typology_label"] = context.get("b86e_typology", "unknown")
    context["typology_for_gate"] = context["b86e_typology"].fillna(context["typology_label"]).astype(str)
    context["spatial_bin_for_gate"] = context["b86e_spatial_bin"].fillna(context.get("spatial_bin", "unknown")).astype(str)
    anchor_group = anchor.groupby("cell_id", as_index=False).agg(
        anchor_max_abs_error=("mean_abs_error", "max"),
        anchor_max_underprediction_rate=("underprediction_rate_for_cooling", "max"),
    )
    neutral_group = neutral.groupby("cell_id", as_index=False).agg(
        neutral_max_false_promotion_rate=("false_promotion_rate", "max"),
        neutral_max_abs_error=("mean_abs_error", "max"),
    )
    context = context.merge(anchor_group, on="cell_id", how="left").merge(neutral_group, on="cell_id", how="left")
    context["typology_support_count"] = context["typology_for_gate"].map(typology_counts).fillna(0).astype(int)
    context["anchor_flag"] = context["cell_id"].astype(str).isin(set(config["anchor_cells"]))
    context["known_neutral_flag"] = context["cell_id"].astype(str).isin(set(config["known_neutral_cells"]))
    context["known_unstable_flag"] = context["cell_id"].astype(str).isin(set(config["known_unstable_cells"]))
    context["anchor_gap_severe"] = (
        context["anchor_flag"]
        & (
            (pd.to_numeric(context["anchor_max_abs_error"], errors="coerce") >= float(config["anchor_underprediction_mae_threshold"]))
            | (pd.to_numeric(context["anchor_max_underprediction_rate"], errors="coerce") >= 0.5)
        )
    )
    context["neutral_gap_severe"] = (
        context["known_neutral_flag"]
        | (pd.to_numeric(context["neutral_max_false_promotion_rate"], errors="coerce") >= 0.5)
    )
    context["any_b86e_gap_family"] = context["suspected_failure_type"].fillna("").astype(str).ne("not-flagged")
    return context


def attach_gate_flags(config: dict[str, Any]) -> pd.DataFrame:
    """Attach moderate and strict abstention flags to B8.6d OOF rows."""
    oof = read_csv(input_path(config, "b86d_oof_predictions_path"))
    context = cell_failure_context(config)
    weak_bins = weak_spatial_bins(config)
    threshold = float(config["neutral_threshold_c"])
    high_distance = float(config["abstention_thresholds"]["high_feature_distance_percentile"])
    oof = oof.merge(
        context[
            [
                "cell_id",
                "nearest_n150_distance",
                "nearest_n150_distance_percentile",
                "typology_support_count",
                "spatial_bin_for_gate",
                "typology_for_gate",
                "anchor_flag",
                "known_neutral_flag",
                "known_unstable_flag",
                "anchor_gap_severe",
                "neutral_gap_severe",
                "any_b86e_gap_family",
                "neutral_max_false_promotion_rate",
            ]
        ],
        on="cell_id",
        how="left",
    )
    pred = pd.to_numeric(oof["pred_combined_delta"], errors="coerce")
    oof["predicted_meaningful_cooling_flag"] = pred < -threshold
    oof["true_neutral_flag"] = pd.to_numeric(oof["true_delta"], errors="coerce").abs() <= threshold
    oof["weak_spatial_bin_flag"] = oof["spatial_bin_for_gate"].astype(str).isin(weak_bins)
    distance_pct = pd.to_numeric(oof["nearest_n150_distance_percentile"], errors="coerce").fillna(1.0)
    oof["moderate_high_distance"] = distance_pct >= high_distance
    oof["moderate_weak_spatial_no_support"] = oof["weak_spatial_bin_flag"] & (distance_pct >= high_distance)
    oof["moderate_low_typology_support"] = pd.to_numeric(oof["typology_support_count"], errors="coerce").fillna(0) < int(
        config["abstention_thresholds"]["low_typology_support_min_cells"]
    )
    oof["moderate_known_gap_family"] = (
        oof["anchor_gap_severe"].map(bool_value)
        | oof["neutral_gap_severe"].map(bool_value)
        | oof["known_unstable_flag"].map(bool_value)
    )
    oof["moderate_high_false_promotion_context"] = oof["predicted_meaningful_cooling_flag"] & (
        pd.to_numeric(oof["neutral_max_false_promotion_rate"], errors="coerce").fillna(0.0) >= 0.5
    )
    moderate_cols = [
        "moderate_high_distance",
        "moderate_weak_spatial_no_support",
        "moderate_low_typology_support",
        "moderate_known_gap_family",
        "moderate_high_false_promotion_context",
    ]
    oof["moderate_abstain"] = oof[moderate_cols].any(axis=1)
    oof["strict_high_distance"] = distance_pct >= 0.75
    oof["strict_weak_spatial_no_support"] = oof["weak_spatial_bin_flag"] & (distance_pct >= 0.75)
    oof["strict_low_typology_support"] = pd.to_numeric(oof["typology_support_count"], errors="coerce").fillna(0) < 5
    oof["strict_known_gap_family"] = (
        oof["any_b86e_gap_family"].map(bool_value)
        | oof["anchor_gap_severe"].map(bool_value)
        | oof["neutral_gap_severe"].map(bool_value)
        | oof["known_unstable_flag"].map(bool_value)
    )
    oof["strict_high_false_promotion_context"] = oof["predicted_meaningful_cooling_flag"] & (
        pd.to_numeric(oof["neutral_max_false_promotion_rate"], errors="coerce").fillna(0.0) >= 0.2
    )
    strict_cols = [
        "strict_high_distance",
        "strict_weak_spatial_no_support",
        "strict_low_typology_support",
        "strict_known_gap_family",
        "strict_high_false_promotion_context",
    ]
    oof["strict_abstain"] = oof[strict_cols].any(axis=1)
    return oof


def neutral_false_promotion_rate(frame: pd.DataFrame, threshold: float) -> float:
    """Compute false-promotion rate among true-neutral retained rows."""
    if frame.empty:
        return float("nan")
    true = pd.to_numeric(frame["true_delta"], errors="coerce")
    pred = pd.to_numeric(frame["pred_combined_delta"], errors="coerce")
    true_neutral = true.abs() <= threshold
    if int(true_neutral.sum()) == 0:
        return float("nan")
    return float(((true_neutral) & (pred < -threshold)).sum() / int(true_neutral.sum()))


def anchor_underprediction_rate(frame: pd.DataFrame, threshold: float) -> float:
    """Compute anchor cooling underprediction rate on retained rows."""
    anchor = frame.loc[frame.get("anchor_flag", pd.Series(False, index=frame.index)).map(bool_value)].copy()
    if anchor.empty:
        return float("nan")
    true = pd.to_numeric(anchor["true_delta"], errors="coerce")
    pred = pd.to_numeric(anchor["pred_combined_delta"], errors="coerce")
    cooling = true < -threshold
    if int(cooling.sum()) == 0:
        return float("nan")
    return float(((cooling) & ((pred - true) > threshold)).sum() / int(cooling.sum()))


def metric_rows(config: dict[str, Any], gated: pd.DataFrame) -> pd.DataFrame:
    """Create abstention gate metrics for baseline, moderate, and strict gates."""
    rows: list[dict[str, Any]] = []
    threshold = float(config["neutral_threshold_c"])
    scopes = ["overall", "spatial_holdout", "cell_group_holdout", "typology_holdout", "forcing_day_holdout", "hour_holdout"]
    gates = {
        "baseline_no_gate": pd.Series(False, index=gated.index),
        "moderate_gate": gated["moderate_abstain"].map(bool_value),
        "strict_gate": gated["strict_abstain"].map(bool_value),
    }
    anchor_cells = set(config["anchor_cells"])
    neutral_cells = set(config["known_neutral_cells"])
    for scope in scopes:
        base_scope = gated if scope == "overall" else gated.loc[gated["split_family"].astype(str).eq(scope)].copy()
        if base_scope.empty:
            continue
        total_rows = len(base_scope)
        total_cells = set(base_scope["cell_id"].astype(str))
        for gate_name, abstain_flags in gates.items():
            flags = abstain_flags.loc[base_scope.index]
            retained = base_scope.loc[~flags].copy()
            abstained = base_scope.loc[flags].copy()
            metrics = prediction_metrics(retained, threshold)
            retained_cells = set(retained["cell_id"].astype(str))
            abstained_cells = set(abstained["cell_id"].astype(str))
            fp_rate = neutral_false_promotion_rate(retained, threshold)
            anchor_rate = anchor_underprediction_rate(retained, threshold)
            improves = (
                gate_name != "baseline_no_gate"
                and scope == "spatial_holdout"
                and metrics["n_rows"] > 0
                and metrics["Spearman"] == metrics["Spearman"]
                and metrics["Spearman"] >= 0.45
                and metrics["top10pct_overlap"] == metrics["top10pct_overlap"]
                and metrics["top10pct_overlap"] >= 0.50
                and fp_rate == fp_rate
                and fp_rate <= 0.15
                and len(retained) / total_rows >= 0.40
            )
            rows.append(
                {
                    "gate_level": gate_name,
                    "split_family": scope,
                    "n_rows_total": int(total_rows),
                    "n_rows_retained": int(len(retained)),
                    "n_rows_abstained": int(len(abstained)),
                    "retained_coverage_fraction": float(len(retained) / total_rows) if total_rows else float("nan"),
                    "abstained_fraction": float(len(abstained) / total_rows) if total_rows else float("nan"),
                    "n_cells_total": int(len(total_cells)),
                    "n_cells_retained": int(len(retained_cells)),
                    "MAE_retained": metrics["MAE"],
                    "Spearman_retained": metrics["Spearman"],
                    "top10pct_overlap_retained": metrics["top10pct_overlap"],
                    "neutral_false_promotion_rate_retained": fp_rate,
                    "anchor_underprediction_rate_retained": anchor_rate,
                    "anchor_underprediction_mae_retained": metrics["anchor_underprediction_mae"],
                    "anchors_retained": int(len(retained_cells & anchor_cells)),
                    "anchors_abstained": int(len(abstained_cells & anchor_cells)),
                    "known_neutral_cells_retained": int(len(retained_cells & neutral_cells)),
                    "known_neutral_cells_abstained": int(len(abstained_cells & neutral_cells)),
                    "improves_safety_enough_for_future_dry_run_preflight": bool(improves),
                    "diagnostic_boundary": "diagnostic_only_no_aoi_prediction",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> AbstentionGateResult:
    """Run abstention gate diagnostics and write CSV outputs."""
    config = load_config(config_path)
    catalog = rule_catalog(config)
    gated = attach_gate_flags(config)
    metrics = metric_rows(config, gated)
    write_csv(catalog, output_path(config, "abstention_rule_catalog"))
    write_csv(metrics, output_path(config, "abstention_gate_metrics"))
    status = "B86F_ABSTENTION_GATE_DIAGNOSTIC_READY"
    return AbstentionGateResult(status=status, rules=len(catalog), metric_rows=len(metrics))


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run B8.6f abstention and uncertainty gate diagnostics.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
