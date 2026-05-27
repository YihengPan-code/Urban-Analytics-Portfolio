"""Create B8.6d selected-workflow diagnostics.

Inputs:
    - b86d_oof_predictions.csv
    - b86d_two_stage_dataset.csv
    - b86d_feature_set_registry.csv
    - b86d_combined_pipeline_metrics.csv
Outputs:
    - b86d_anchor_cell_diagnostics.csv
    - b86d_neutral_boundary_diagnostics.csv
    - b86d_unstable_cell_diagnostics.csv
    - b86d_worst_error_inventory.csv
    - b86d_feature_importance_diagnostics.csv
Saved metrics:
    Cell-level anchor, neutral-boundary, unstable-cell, worst-error, and
    non-causal permutation-importance diagnostics for the selected workflow.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from v12_b86d_common import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    classifier_models,
    coerce_feature_frame,
    feature_columns_for_set,
    load_config,
    make_pipeline,
    neutral_class,
    output_path,
    read_csv,
    regressor_models,
    write_csv,
)
from v12_b86d_two_stage_pipeline import select_best_pipeline


@dataclass(frozen=True)
class DiagnosticsResult:
    """Diagnostic result."""

    status: str
    anchor_rows: int
    neutral_rows: int
    unstable_rows: int
    worst_rows: int


def selected_combo(config: dict[str, Any]) -> dict[str, Any]:
    """Select the primary-threshold combo from combined metrics."""
    metrics = read_csv(output_path(config, "combined_pipeline_metrics"))
    return select_best_pipeline(metrics, config)


def cell_rank_diagnostics(predictions: pd.DataFrame, cells: list[str], role: str) -> pd.DataFrame:
    """Create per-cell diagnostics for selected cells."""
    rows: list[dict[str, Any]] = []
    wanted = set(cells)
    for split_family, split_frame in predictions.groupby("split_family", dropna=False):
        by_cell = split_frame.groupby("cell_id", as_index=False).agg(
            n_rows=("row_id", "size"),
            mean_true_delta_tmrt_p90_c=("true_delta", "mean"),
            mean_pred_delta_tmrt_p90_c=("pred_combined_delta", "mean"),
            MAE=("combined_abs_error", "mean"),
        )
        by_cell["true_rank"] = by_cell["mean_true_delta_tmrt_p90_c"].rank(method="min", ascending=True)
        by_cell["pred_rank"] = by_cell["mean_pred_delta_tmrt_p90_c"].rank(method="min", ascending=True)
        by_cell["abs_rank_error"] = (by_cell["pred_rank"] - by_cell["true_rank"]).abs()
        subset = by_cell.loc[by_cell["cell_id"].astype(str).isin(wanted)].copy()
        for _, row in subset.iterrows():
            rows.append(
                {
                    "cell_id": row["cell_id"],
                    "diagnostic_role": role,
                    "split_family": split_family,
                    "n_rows": int(row["n_rows"]),
                    "mean_true_delta_tmrt_p90_c": float(row["mean_true_delta_tmrt_p90_c"]),
                    "mean_pred_delta_tmrt_p90_c": float(row["mean_pred_delta_tmrt_p90_c"]),
                    "MAE": float(row["MAE"]),
                    "true_rank": float(row["true_rank"]),
                    "pred_rank": float(row["pred_rank"]),
                    "abs_rank_error": float(row["abs_rank_error"]),
                    "failure_type": "anchor_underprediction_review" if role == "robust_anchor" else "unstable_cell_review",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
    return pd.DataFrame(rows)


def neutral_boundary_diagnostics(predictions: pd.DataFrame, cells: list[str]) -> pd.DataFrame:
    """Create per-cell neutral-boundary diagnostics."""
    rows: list[dict[str, Any]] = []
    wanted = set(cells)
    for (cell_id, split_family), group in predictions.loc[predictions["cell_id"].astype(str).isin(wanted)].groupby(
        ["cell_id", "split_family"],
        dropna=False,
    ):
        rows.append(
            {
                "cell_id": cell_id,
                "split_family": split_family,
                "n_rows": len(group),
                "true_neutral_fraction": float((group["true_class"] == "neutral").mean()),
                "pred_neutral_fraction": float((group["pred_stage1_class"] == "neutral").mean()),
                "pred_meaningful_cooling_fraction": float((group["pred_stage1_class"] == "meaningful_cooling").mean()),
                "neutral_boundary_classification_accuracy": float((group["true_class"] == group["pred_stage1_class"]).mean()),
                "false_promotion_rate": float(group["combined_false_promotion"].mean()),
                "false_neutral_rate": float(group["combined_false_neutral"].mean()),
                "mean_true_delta_tmrt_p90_c": float(group["true_delta"].mean()),
                "mean_pred_delta_tmrt_p90_c": float(group["pred_combined_delta"].mean()),
                "MAE": float(group["combined_abs_error"].mean()),
                "failure_type": "neutral_boundary_review",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def worst_error_inventory(predictions: pd.DataFrame, max_rows: int = 100) -> pd.DataFrame:
    """Return highest absolute-error validation rows."""
    columns = [
        "row_id",
        "cell_id",
        "forcing_day_id",
        "hour_sgt",
        "typology_label",
        "split_family",
        "split_name",
        "fold_id",
        "true_delta",
        "pred_combined_delta",
        "combined_abs_error",
        "true_class",
        "pred_stage1_class",
        "pred_stage2_delta",
        "combined_false_promotion",
        "combined_false_neutral",
    ]
    out = predictions.sort_values("combined_abs_error", ascending=False).loc[:, columns].head(max_rows).copy()
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def feature_group(feature: str, config: dict[str, Any]) -> str:
    """Assign a diagnostic feature group."""
    name = feature.lower()
    if "_x_" in name:
        return "interactions"
    if "typology" in name or "land_use_hint" in name:
        return "typology_context"
    for group, spec in config["feature_groups"].items():
        if any(token in name for token in spec.get("tokens", [])):
            return group
    return "other_compact"


def permutation_rows(
    dataset: pd.DataFrame,
    registry: pd.DataFrame,
    config: dict[str, Any],
    best: dict[str, Any],
) -> pd.DataFrame:
    """Compute non-causal permutation importance for selected models."""
    primary = config["targets"]["primary_target"]
    threshold = float(best["neutral_threshold_c"])
    features = feature_columns_for_set(registry, dataset, str(best["feature_set"]), config)
    X_all, numeric, categorical = coerce_feature_frame(dataset, features)
    rows: list[dict[str, Any]] = []
    model_specs = [
        ("stage1_classifier", str(best["classifier"]), classifier_models(config)[str(best["classifier"])], "balanced_accuracy"),
        ("stage2_regressor", str(best["regressor"]), regressor_models(config)[str(best["regressor"])], "neg_mean_absolute_error"),
    ]
    for stage, model_name, estimator, scoring in model_specs:
        if stage == "stage1_classifier":
            y = neutral_class(pd.to_numeric(dataset[primary], errors="coerce"), threshold)
            X = X_all
        else:
            mask = pd.to_numeric(dataset[primary], errors="coerce").abs() > threshold
            X = X_all.loc[mask]
            y = pd.to_numeric(dataset.loc[mask, primary], errors="coerce").to_numpy(dtype=float)
        try:
            pipeline = make_pipeline(model_name, estimator, numeric, categorical)
            pipeline.fit(X, y)
            result = permutation_importance(
                pipeline,
                X,
                y,
                n_repeats=3,
                random_state=int(config["random_seed"]),
                scoring=scoring,
                n_jobs=1,
            )
            importances = result.importances_mean
            denom = float(np.sum(np.abs(importances))) or 1.0
            for feature, importance in zip(features, importances):
                rows.append(
                    {
                        "stage": stage,
                        "model": model_name,
                        "feature": feature,
                        "feature_group": feature_group(feature, config),
                        "importance": float(importance),
                        "normalized_abs_importance": float(abs(importance) / denom),
                        "method": f"permutation_importance_{scoring}",
                        "diagnostic_boundary": "Non-causal model diagnostic only; does not prove real-world heat-risk drivers.",
                        "claim_boundary": CLAIM_BOUNDARY,
                    }
                )
        except Exception as exc:  # pragma: no cover - defensive for diagnostics.
            rows.append(
                {
                    "stage": stage,
                    "model": model_name,
                    "feature": "",
                    "feature_group": "not_available",
                    "importance": float("nan"),
                    "normalized_abs_importance": float("nan"),
                    "method": f"failed: {exc}",
                    "diagnostic_boundary": "Non-causal model diagnostic only; does not prove real-world heat-risk drivers.",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    group_rows = (
        frame.groupby(["stage", "model", "feature_group"], dropna=False)["normalized_abs_importance"]
        .sum()
        .reset_index()
        .rename(columns={"normalized_abs_importance": "group_normalized_abs_importance"})
    )
    frame = frame.merge(group_rows, on=["stage", "model", "feature_group"], how="left")
    return frame.sort_values(["stage", "normalized_abs_importance"], ascending=[True, False])


def run(config_path: Path = DEFAULT_CONFIG) -> DiagnosticsResult:
    """Write selected-workflow diagnostics."""
    config = load_config(config_path)
    dataset = read_csv(output_path(config, "two_stage_dataset"))
    registry = read_csv(output_path(config, "feature_set_registry"))
    predictions = read_csv(output_path(config, "oof_predictions"))
    best = selected_combo(config)
    anchor = cell_rank_diagnostics(predictions, config["diagnostic_cells"]["robust_priority_anchors"], "robust_anchor")
    neutral = neutral_boundary_diagnostics(predictions, config["diagnostic_cells"]["neutral_boundary_cells"])
    unstable = cell_rank_diagnostics(predictions, config["diagnostic_cells"]["unstable_review_cells"], "unstable_review")
    worst = worst_error_inventory(predictions)
    importance = permutation_rows(dataset, registry, config, best)
    write_csv(anchor, output_path(config, "anchor_cell_diagnostics"))
    write_csv(neutral, output_path(config, "neutral_boundary_diagnostics"))
    write_csv(unstable, output_path(config, "unstable_cell_diagnostics"))
    write_csv(worst, output_path(config, "worst_error_inventory"))
    write_csv(importance, output_path(config, "feature_importance_diagnostics"))
    return DiagnosticsResult("B86D_DIAGNOSTICS_READY", len(anchor), len(neutral), len(unstable), len(worst))


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Write B8.6d selected-workflow diagnostics.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
