"""Run the formal B8.6d two-stage surrogate validation pipeline.

Inputs:
    - b86d_two_stage_dataset.csv
    - b86d_feature_set_registry.csv
    - B8.6c single-stage and two-stage reference metrics.
Outputs:
    - b86d_stage1_classifier_metrics.csv
    - b86d_stage2_regressor_metrics.csv
    - b86d_combined_pipeline_metrics.csv
    - b86d_threshold_sweep_metrics.csv
    - b86d_metrics_by_split.csv
    - b86d_metrics_by_target.csv
    - b86d_metrics_by_hour.csv
    - b86d_metrics_by_typology.csv
    - b86d_metrics_by_spatial_bin.csv
    - b86d_oof_predictions.csv
Saved metrics:
    Stage-1 neutral classification, stage-2 non-neutral regression/ranking,
    combined pipeline regression/ranking, threshold trade-offs, split and
    subgroup metrics, and companion-target sensitivity metrics.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86d_common import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    SUPPORTING_WEAK_SPLITS,
    classification_metrics,
    h10_metrics,
    load_config,
    output_path,
    read_csv,
    regression_metrics,
    role_error_and_rank,
    write_csv,
)
from v12_b86d_stage1_classifier import stage1_for_config
from v12_b86d_stage2_regressor import stage2_for_config


@dataclass(frozen=True)
class PipelineResult:
    """Two-stage pipeline run result."""

    status: str
    best_feature_set: str
    best_threshold: float
    best_classifier: str
    best_regressor: str
    combined_rows: int


COMBO_COLS = ["feature_set", "neutral_threshold_c", "classifier", "regressor"]
FOLD_COLS = ["split_family", "split_name", "fold_id", "seed"]


def combine_predictions(stage1: pd.DataFrame, stage2: pd.DataFrame, primary: str) -> pd.DataFrame:
    """Combine stage-1 class predictions with stage-2 delta predictions."""
    stage2_cols = [
        "row_index",
        "feature_set",
        "neutral_threshold_c",
        "split_family",
        "split_name",
        "fold_id",
        "seed",
        "regressor",
        "true_non_neutral_for_stage2",
        "pred_stage2_delta",
    ]
    merged = stage1.merge(stage2[stage2_cols], on=stage2_cols[:7], how="inner")
    merged["pred_combined_delta"] = np.where(
        merged["pred_stage1_class"].astype(str) == "meaningful_cooling",
        pd.to_numeric(merged["pred_stage2_delta"], errors="coerce"),
        0.0,
    )
    merged["true_delta"] = pd.to_numeric(merged[primary], errors="coerce")
    merged["combined_abs_error"] = (merged["pred_combined_delta"] - merged["true_delta"]).abs()
    merged["combined_false_promotion"] = (merged["true_class"] == "neutral") & (
        merged["pred_stage1_class"] == "meaningful_cooling"
    )
    merged["combined_false_neutral"] = (merged["true_class"] == "meaningful_cooling") & (
        merged["pred_stage1_class"] == "neutral"
    )
    merged["claim_boundary"] = CLAIM_BOUNDARY
    return merged


def combined_metric_rows(predictions: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Aggregate combined OOF predictions into fold-level metrics."""
    primary = config["targets"]["primary_target"]
    threshold = float(config["primary_neutral_threshold_c"])
    rows: list[dict[str, Any]] = []
    group_cols = COMBO_COLS + FOLD_COLS
    for values, group in predictions.groupby(group_cols, dropna=False):
        key = dict(zip(group_cols, values))
        y_true = pd.to_numeric(group[primary], errors="coerce").to_numpy(dtype=float)
        y_pred = pd.to_numeric(group["pred_combined_delta"], errors="coerce").to_numpy(dtype=float)
        row: dict[str, Any] = {
            **key,
            "n_test": len(group),
            "n_test_cells": int(group["cell_id"].nunique()),
            "claim_boundary": CLAIM_BOUNDARY,
            "status": "OK",
        }
        row.update(regression_metrics(group, y_true, y_pred, float(key["neutral_threshold_c"])))
        row.update(classification_metrics(group["true_class"].to_numpy(), group["pred_stage1_class"].to_numpy()))
        anchor_mae, anchor_rank = role_error_and_rank(
            group,
            y_true,
            y_pred,
            config["diagnostic_cells"]["robust_priority_anchors"],
        )
        unstable_mae, unstable_rank = role_error_and_rank(
            group,
            y_true,
            y_pred,
            config["diagnostic_cells"]["unstable_review_cells"],
        )
        row["robust_anchor_MAE"] = anchor_mae
        row["robust_anchor_mean_rank_error"] = anchor_rank
        row["unstable_review_MAE"] = unstable_mae
        row["unstable_review_mean_rank_error"] = unstable_rank
        row.update(h10_metrics(group, y_true, y_pred, config, threshold))
        rows.append(row)
    return pd.DataFrame(rows)


def select_best_pipeline(metrics: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    """Select the best primary-threshold two-stage candidate."""
    primary_threshold = float(config["primary_neutral_threshold_c"])
    candidates = metrics.loc[
        (metrics["neutral_threshold_c"].astype(float) == primary_threshold)
        & (metrics["split_family"].isin(SUPPORTING_WEAK_SPLITS))
        & (metrics["status"].astype(str) == "OK")
    ].copy()
    if candidates.empty:
        fallback = metrics.loc[metrics["status"].astype(str) == "OK"].head(1)
        if fallback.empty:
            return {
                "feature_set": "",
                "neutral_threshold_c": primary_threshold,
                "classifier": "",
                "regressor": "",
                "score": float("nan"),
            }
        row = fallback.iloc[0]
        return {column: row[column] for column in COMBO_COLS} | {"score": float("nan")}
    grouped = candidates.groupby(COMBO_COLS, dropna=False).agg(
        neutral_accuracy=("accuracy", "mean"),
        false_promotion_rate=("false_promotion_rate", "mean"),
        spearman=("Spearman_observed_vs_predicted", "mean"),
        top10=("top10pct_overlap", "mean"),
        mae=("MAE", "mean"),
        anchor_mae=("robust_anchor_MAE", "mean"),
    )
    score_frame = grouped.reset_index()
    score_frame["score"] = (
        score_frame["neutral_accuracy"].fillna(0.0) * 0.25
        + score_frame["spearman"].fillna(-1.0) * 0.35
        + score_frame["top10"].fillna(0.0) * 0.25
        - score_frame["false_promotion_rate"].fillna(1.0) * 0.15
        - score_frame["mae"].fillna(1.0) * 0.05
    )
    row = score_frame.sort_values(["score", "neutral_accuracy", "spearman", "top10"], ascending=False).iloc[0]
    return row.to_dict()


def threshold_sweep(metrics: pd.DataFrame) -> pd.DataFrame:
    """Summarize threshold trade-offs across supporting split families."""
    support = metrics.loc[metrics["split_family"].isin(SUPPORTING_WEAK_SPLITS)].copy()
    if support.empty:
        return pd.DataFrame()
    grouped = support.groupby(COMBO_COLS, dropna=False).agg(
        n_folds=("MAE", "size"),
        neutral_accuracy=("accuracy", "mean"),
        balanced_accuracy=("balanced_accuracy", "mean"),
        false_promotion_rate=("false_promotion_rate", "mean"),
        false_neutral_rate=("false_neutral_rate", "mean"),
        Spearman=("Spearman_observed_vs_predicted", "mean"),
        top10pct_overlap=("top10pct_overlap", "mean"),
        robust_anchor_MAE=("robust_anchor_MAE", "mean"),
        spatial_Spearman=(
            "Spearman_observed_vs_predicted",
            lambda values: float(support.loc[values.index, "Spearman_observed_vs_predicted"][
                support.loc[values.index, "split_family"] == "spatial_holdout"
            ].mean()),
        ),
        typology_Spearman=(
            "Spearman_observed_vs_predicted",
            lambda values: float(support.loc[values.index, "Spearman_observed_vs_predicted"][
                support.loc[values.index, "split_family"] == "typology_holdout"
            ].mean()),
        ),
    )
    out = grouped.reset_index()
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out.sort_values(["neutral_threshold_c", "neutral_accuracy", "Spearman"], ascending=[True, False, False])


def reference_baselines(config: dict[str, Any]) -> pd.DataFrame:
    """Load B8.6c single-stage reference metrics for comparison."""
    path = config["inputs"].get("b86c_feature_set_model_metrics_path")
    try:
        metrics = read_csv(path)
    except FileNotFoundError:
        return pd.DataFrame()
    primary = config["targets"]["primary_target"]
    subset = metrics.loc[
        metrics["target"].astype(str).eq(primary)
        & metrics["feature_set"].astype(str).isin(config["feature_sets_to_test"])
        & metrics["model"].astype(str).isin(config["models"]["regressors"])
        & metrics["split_family"].astype(str).isin(config["split_families"])
    ].copy()
    if subset.empty:
        return pd.DataFrame()
    combo = subset.groupby(["split_family", "feature_set", "model"], dropna=False).agg(
        baseline_MAE=("MAE", "mean"),
        baseline_Spearman=("Spearman_observed_vs_predicted", "mean"),
        baseline_top10pct_overlap=("top10pct_overlap", "mean"),
        baseline_anchor_MAE=("robust_anchor_MAE", "mean"),
    ).reset_index()
    combo["rank_score"] = combo["baseline_Spearman"].fillna(-1.0) + combo["baseline_top10pct_overlap"].fillna(0.0)
    best = combo.sort_values("rank_score", ascending=False).groupby("split_family", as_index=False).head(1)
    return best.drop(columns=["rank_score"]).rename(columns={"feature_set": "baseline_feature_set", "model": "baseline_model"})


def selected_metrics_by_split(metrics: pd.DataFrame, best: dict[str, Any], config: dict[str, Any]) -> pd.DataFrame:
    """Aggregate selected combined metrics by split and join B8.6c reference baselines."""
    selected = metrics.copy()
    for column in COMBO_COLS:
        selected = selected.loc[selected[column].astype(str) == str(best[column])]
    grouped = selected.groupby(["split_family", "split_name"], dropna=False).agg(
        n_folds=("MAE", "size"),
        MAE=("MAE", "mean"),
        RMSE=("RMSE", "mean"),
        R2=("R2", "mean"),
        Spearman=("Spearman_observed_vs_predicted", "mean"),
        top10pct_overlap=("top10pct_overlap", "mean"),
        neutral_accuracy=("accuracy", "mean"),
        false_promotion_rate=("false_promotion_rate", "mean"),
        robust_anchor_MAE=("robust_anchor_MAE", "mean"),
        h10_Spearman=("h10_Spearman", "mean"),
        core_hour_excluding_h10_Spearman=("core_hour_excluding_h10_Spearman", "mean"),
    ).reset_index()
    baseline = reference_baselines(config)
    if not baseline.empty:
        grouped = grouped.merge(baseline, on="split_family", how="left")
        grouped["Spearman_gain_vs_b86c_single_stage"] = grouped["Spearman"] - grouped["baseline_Spearman"]
        grouped["top10_gain_vs_b86c_single_stage"] = grouped["top10pct_overlap"] - grouped["baseline_top10pct_overlap"]
        grouped["anchor_MAE_delta_vs_b86c_single_stage"] = grouped["robust_anchor_MAE"] - grouped["baseline_anchor_MAE"]
    grouped["selected_feature_set"] = best["feature_set"]
    grouped["selected_threshold_c"] = best["neutral_threshold_c"]
    grouped["selected_classifier"] = best["classifier"]
    grouped["selected_regressor"] = best["regressor"]
    grouped["claim_boundary"] = CLAIM_BOUNDARY
    return grouped


def subgroup_metrics(predictions: pd.DataFrame, group_col: str, threshold: float) -> pd.DataFrame:
    """Compute selected OOF subgroup metrics."""
    rows: list[dict[str, Any]] = []
    for value, group in predictions.groupby(group_col, dropna=False):
        y_true = pd.to_numeric(group["true_delta"], errors="coerce").to_numpy(dtype=float)
        y_pred = pd.to_numeric(group["pred_combined_delta"], errors="coerce").to_numpy(dtype=float)
        row: dict[str, Any] = {
            group_col: value,
            "n_rows": len(group),
            "n_cells": int(group["cell_id"].nunique()),
            "claim_boundary": CLAIM_BOUNDARY,
        }
        row.update(regression_metrics(group, y_true, y_pred, threshold))
        rows.append(row)
    return pd.DataFrame(rows)


def target_sensitivity_metrics(dataset: pd.DataFrame, registry: pd.DataFrame, config: dict[str, Any], best: dict[str, Any]) -> pd.DataFrame:
    """Evaluate companion targets with the selected feature set/regressor as sensitivity evidence."""
    targets = [config["targets"]["primary_target"], *config["targets"]["companion_targets"]]
    rows: list[pd.DataFrame] = []
    for target in targets:
        metrics, _ = stage2_for_config(
            dataset,
            registry,
            config,
            target=target,
            thresholds=[float(config["primary_neutral_threshold_c"])],
            model_names=[str(best["regressor"])],
            feature_sets=[str(best["feature_set"])],
            train_non_neutral_only=False,
        )
        if metrics.empty:
            continue
        grouped = metrics.groupby(["target", "split_family"], dropna=False).agg(
            n_folds=("MAE", "size"),
            MAE=("MAE", "mean"),
            RMSE=("RMSE", "mean"),
            R2=("R2", "mean"),
            Spearman=("Spearman_observed_vs_predicted", "mean"),
            top10pct_overlap=("top10pct_overlap", "mean"),
            sign_accuracy=("sign_accuracy", "mean"),
        ).reset_index()
        grouped["target_role"] = grouped["target"].map(config["targets"]["target_roles"])
        grouped["target_decision_context"] = "companion sensitivity; does not replace p90 by default"
        rows.append(grouped)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def run(config_path: Path = DEFAULT_CONFIG) -> PipelineResult:
    """Run stage 1, stage 2, and combined two-stage validation."""
    config = load_config(config_path)
    dataset = read_csv(output_path(config, "two_stage_dataset"))
    registry = read_csv(output_path(config, "feature_set_registry"))
    primary = config["targets"]["primary_target"]

    thresholds = [float(value) for value in config["neutral_thresholds_c"]]
    stage1_metrics, stage1_predictions = stage1_for_config(dataset, registry, config, thresholds=thresholds)
    stage2_metrics, stage2_predictions = stage2_for_config(dataset, registry, config, target=primary, thresholds=thresholds)
    write_csv(stage1_metrics, output_path(config, "stage1_classifier_metrics"))
    write_csv(stage2_metrics, output_path(config, "stage2_regressor_metrics"))

    combined_predictions = combine_predictions(stage1_predictions, stage2_predictions, primary)
    combined_metrics = combined_metric_rows(combined_predictions, config)
    write_csv(combined_metrics, output_path(config, "combined_pipeline_metrics"))

    best = select_best_pipeline(combined_metrics, config)
    sweep = threshold_sweep(combined_metrics)
    write_csv(sweep, output_path(config, "threshold_sweep_metrics"))
    by_split = selected_metrics_by_split(combined_metrics, best, config)
    write_csv(by_split, output_path(config, "metrics_by_split"))

    selected_oof = combined_predictions.copy()
    for column in COMBO_COLS:
        selected_oof = selected_oof.loc[selected_oof[column].astype(str) == str(best[column])]
    write_csv(selected_oof, output_path(config, "oof_predictions"))

    threshold = float(best.get("neutral_threshold_c", config["primary_neutral_threshold_c"]))
    by_hour = subgroup_metrics(selected_oof, "hour_sgt", threshold)
    write_csv(by_hour, output_path(config, "metrics_by_hour"))
    by_typology = subgroup_metrics(selected_oof, "typology_label", threshold)
    write_csv(by_typology, output_path(config, "metrics_by_typology"))
    spatial_oof = selected_oof.loc[selected_oof["split_family"].astype(str) == "spatial_holdout"].copy()
    by_spatial = subgroup_metrics(spatial_oof, "split_name", threshold) if not spatial_oof.empty else pd.DataFrame()
    write_csv(by_spatial, output_path(config, "metrics_by_spatial_bin"))

    by_target = target_sensitivity_metrics(dataset, registry, config, best)
    write_csv(by_target, output_path(config, "metrics_by_target"))

    return PipelineResult(
        status="B86D_TWO_STAGE_PIPELINE_READY",
        best_feature_set=str(best["feature_set"]),
        best_threshold=float(best["neutral_threshold_c"]),
        best_classifier=str(best["classifier"]),
        best_regressor=str(best["regressor"]),
        combined_rows=len(combined_metrics),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run the full B8.6d two-stage validation pipeline.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
