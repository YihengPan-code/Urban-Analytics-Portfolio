"""Stage 2 non-neutral magnitude/ranking regressor for B8.6d.

Inputs:
    - b86d_two_stage_dataset.csv
    - b86d_feature_set_registry.csv
    - deterministic validation folds.
Outputs:
    - b86d_stage2_regressor_metrics.csv when run as a CLI or by the runner.
Saved metrics:
    MAE, RMSE, R2, Spearman, Pearson, bias, p90 absolute error, sign accuracy,
    top5/top10pct/top20pct overlap, robust-anchor MAE/rank error, unstable-cell
    MAE/rank error, and h10/core-hour metrics.
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
    coerce_feature_frame,
    feature_columns_for_set,
    h10_metrics,
    load_config,
    make_pipeline,
    output_path,
    read_csv,
    regression_metrics,
    regressor_models,
    role_error_and_rank,
    validation_folds,
    write_csv,
)


@dataclass(frozen=True)
class Stage2Result:
    """Stage 2 run result."""

    status: str
    metric_rows: int
    prediction_rows: int


def stage2_for_config(
    dataset: pd.DataFrame,
    registry: pd.DataFrame,
    config: dict[str, Any],
    target: str | None = None,
    thresholds: list[float] | None = None,
    model_names: list[str] | None = None,
    feature_sets: list[str] | None = None,
    seed: int | None = None,
    train_non_neutral_only: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit/evaluate stage-2 regressors and return metrics plus OOF predictions."""
    primary = config["targets"]["primary_target"]
    target = target or primary
    thresholds = thresholds or [float(config["primary_neutral_threshold_c"])]
    model_names = model_names or list(config["models"]["regressors"])
    feature_sets = feature_sets or list(config["feature_sets_to_test"])
    folds = validation_folds(dataset, config)
    models = regressor_models(config, seed=seed)
    y_primary_all = pd.to_numeric(dataset[primary], errors="coerce")
    y_target_all = pd.to_numeric(dataset[target], errors="coerce")
    metric_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []

    for feature_set in feature_sets:
        features = feature_columns_for_set(registry, dataset, feature_set, config)
        if not features:
            continue
        X_all, numeric, categorical = coerce_feature_frame(dataset, features)
        for threshold in thresholds:
            non_neutral_mask_all = y_primary_all.abs() > float(threshold)
            for fold in folds:
                fold_train_index = fold.train_index
                if train_non_neutral_only:
                    train_index = fold_train_index[non_neutral_mask_all.loc[fold_train_index].to_numpy()]
                else:
                    train_index = fold_train_index
                test_index = fold.test_index
                X_train = X_all.loc[train_index]
                X_test = X_all.loc[test_index]
                y_train = y_target_all.loc[train_index].to_numpy(dtype=float)
                y_test_full = y_target_all.loc[test_index].to_numpy(dtype=float)
                eval_mask = non_neutral_mask_all.loc[test_index].to_numpy() if train_non_neutral_only else np.ones(len(test_index), dtype=bool)
                test = dataset.loc[test_index]
                eval_test = test.loc[eval_mask]
                for model_name in model_names:
                    if model_name not in models:
                        continue
                    row: dict[str, Any] = {
                        "feature_set": feature_set,
                        "feature_count": len(features),
                        "target": target,
                        "neutral_threshold_c": threshold,
                        "regressor": model_name,
                        "split_family": fold.split_family,
                        "split_name": fold.split_name,
                        "fold_id": fold.fold_id,
                        "seed": int(config["random_seed"] if seed is None else seed),
                        "n_train": len(X_train),
                        "n_test": len(X_test),
                        "n_eval_non_neutral": int(eval_mask.sum()),
                        "n_train_cells": int(dataset.loc[train_index, "cell_id"].nunique()) if len(train_index) else 0,
                        "n_test_cells": int(test["cell_id"].nunique()),
                        "claim_boundary": CLAIM_BOUNDARY,
                    }
                    if len(X_train) < 5 or pd.Series(y_train).nunique(dropna=True) < 2 or int(eval_mask.sum()) < 2:
                        row.update({"status": "SKIPPED_INSUFFICIENT_NON_NEUTRAL"})
                        metric_rows.append(row)
                        continue
                    try:
                        pipeline = make_pipeline(model_name, models[model_name], numeric, categorical)
                        pipeline.fit(X_train, y_train)
                        y_pred_full = pipeline.predict(X_test)
                        y_eval = y_test_full[eval_mask]
                        pred_eval = y_pred_full[eval_mask]
                        row.update(regression_metrics(eval_test, y_eval, pred_eval, threshold))
                        anchor_mae, anchor_rank = role_error_and_rank(
                            eval_test,
                            y_eval,
                            pred_eval,
                            config["diagnostic_cells"]["robust_priority_anchors"],
                        )
                        unstable_mae, unstable_rank = role_error_and_rank(
                            eval_test,
                            y_eval,
                            pred_eval,
                            config["diagnostic_cells"]["unstable_review_cells"],
                        )
                        row["robust_anchor_MAE"] = anchor_mae
                        row["robust_anchor_mean_rank_error"] = anchor_rank
                        row["unstable_review_MAE"] = unstable_mae
                        row["unstable_review_mean_rank_error"] = unstable_rank
                        row.update(h10_metrics(test, y_test_full, y_pred_full, config, threshold))
                        row["status"] = "OK"
                        pred_columns = list(
                            dict.fromkeys(["row_id", "cell_id", "forcing_day_id", "hour_sgt", "typology_label", primary, target])
                        )
                        pred = test[pred_columns].copy()
                        pred["row_index"] = pred.index
                        pred["feature_set"] = feature_set
                        pred["target"] = target
                        pred["neutral_threshold_c"] = threshold
                        pred["regressor"] = model_name
                        pred["split_family"] = fold.split_family
                        pred["split_name"] = fold.split_name
                        pred["fold_id"] = fold.fold_id
                        pred["seed"] = int(config["random_seed"] if seed is None else seed)
                        pred["true_non_neutral_for_stage2"] = eval_mask
                        pred["pred_stage2_delta"] = y_pred_full
                        prediction_rows.append(pred)
                    except Exception as exc:  # pragma: no cover - defensive for long-run lane.
                        row.update({"status": "FAILED", "error": str(exc)})
                    metric_rows.append(row)

    metrics = pd.DataFrame(metric_rows)
    predictions = pd.concat(prediction_rows, ignore_index=True) if prediction_rows else pd.DataFrame()
    return metrics, predictions


def run(config_path: Path = DEFAULT_CONFIG) -> Stage2Result:
    """Run stage 2 and write metrics."""
    config = load_config(config_path)
    dataset = read_csv(output_path(config, "two_stage_dataset"))
    registry = read_csv(output_path(config, "feature_set_registry"))
    metrics, predictions = stage2_for_config(dataset, registry, config)
    write_csv(metrics, output_path(config, "stage2_regressor_metrics"))
    return Stage2Result("B86D_STAGE2_READY", len(metrics), len(predictions))


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run B8.6d stage-2 non-neutral regressors and write metrics.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
