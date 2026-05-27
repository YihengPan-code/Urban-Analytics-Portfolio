"""Run B8.6g2 single-stage direct surrogate regressors.

Inputs:
    b86g2_modeling_dataset.csv, b86g2_feature_set_registry.csv, and
    deterministic B8.6g2 validation folds.
Outputs:
    b86g2_single_stage_metrics.csv.
Saved metrics:
    Fold-level MAE, RMSE, R2, Spearman, Pearson, bias, p90 absolute error,
    sign accuracy, top5/top10pct/top20pct overlap, anchor diagnostics, and
    unstable-cell diagnostics for every configured feature set and regressor.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86g2_common import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    coerce_feature_frame,
    feature_columns_for_set,
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
class SingleStageResult:
    """Single-stage model result."""

    status: str
    metric_rows: int
    feature_sets: int
    models: int


def single_stage_rows(dataset: pd.DataFrame, registry: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Evaluate all configured single-stage regressors."""
    primary = config["primary_target"]
    threshold = float(config["neutral_threshold_c"])
    folds = validation_folds(dataset, config)
    models = regressor_models(config)
    rows: list[dict[str, Any]] = []
    y_all = pd.to_numeric(dataset[primary], errors="coerce")
    for feature_set in config["feature_sets_to_test"]:
        features = feature_columns_for_set(registry, dataset, feature_set)
        if not features:
            continue
        X_all, numeric, categorical = coerce_feature_frame(dataset, features)
        for fold in folds:
            train = dataset.loc[fold.train_index]
            test = dataset.loc[fold.test_index]
            X_train = X_all.loc[fold.train_index]
            X_test = X_all.loc[fold.test_index]
            y_train = y_all.loc[fold.train_index].to_numpy(dtype=float)
            y_test = y_all.loc[fold.test_index].to_numpy(dtype=float)
            for model_name in config["models"]["regressors"]:
                row: dict[str, Any] = {
                    "feature_set": feature_set,
                    "model": model_name,
                    "feature_count": len(features),
                    "split_family": fold.split_family,
                    "split_name": fold.split_name,
                    "fold_id": fold.fold_id,
                    "seed": int(config["random_seed"]),
                    "n_train": len(train),
                    "n_test": len(test),
                    "n_train_cells": int(train["cell_id"].nunique()),
                    "n_test_cells": int(test["cell_id"].nunique()),
                    "target": primary,
                    "neutral_threshold_c": threshold,
                    "claim_boundary": CLAIM_BOUNDARY,
                }
                if model_name not in models or pd.Series(y_train).nunique(dropna=True) < 2:
                    row["status"] = "SKIPPED_INSUFFICIENT_TARGET_VARIATION"
                    rows.append(row)
                    continue
                try:
                    pipeline = make_pipeline(model_name, models[model_name], numeric, categorical)
                    pipeline.fit(X_train, y_train)
                    y_pred = np.asarray(pipeline.predict(X_test), dtype=float)
                    row.update(regression_metrics(test, y_test, y_pred, threshold))
                    anchor_mae, anchor_rank = role_error_and_rank(test, y_test, y_pred, config["diagnostic_cells"]["anchor_cells"])
                    unstable_mae, unstable_rank = role_error_and_rank(
                        test,
                        y_test,
                        y_pred,
                        config["diagnostic_cells"]["unstable_cells"],
                    )
                    row["anchor_MAE"] = anchor_mae
                    row["anchor_mean_rank_error"] = anchor_rank
                    row["unstable_MAE"] = unstable_mae
                    row["unstable_mean_rank_error"] = unstable_rank
                    row["status"] = "OK"
                except Exception as exc:  # pragma: no cover - defensive long-run lane.
                    row["status"] = "FAILED"
                    row["error"] = str(exc)
                rows.append(row)
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> SingleStageResult:
    """Run single-stage direct regressors and write metrics."""
    config = load_config(config_path)
    dataset = read_csv(output_path(config, "modeling_dataset"))
    registry = read_csv(output_path(config, "feature_set_registry"))
    metrics = single_stage_rows(dataset, registry, config)
    write_csv(metrics, output_path(config, "single_stage_metrics"))
    return SingleStageResult(
        "B86G2_SINGLE_STAGE_READY",
        len(metrics),
        int(metrics["feature_set"].nunique()) if not metrics.empty else 0,
        int(metrics["model"].nunique()) if not metrics.empty else 0,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run B8.6g2 single-stage direct surrogate regressors.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
