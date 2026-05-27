"""Stage 1 neutral-boundary classifier for B8.6d.

Inputs:
    - b86d_two_stage_dataset.csv
    - b86d_feature_set_registry.csv
    - deterministic B8.6d validation folds from config.
Outputs:
    - b86d_stage1_classifier_metrics.csv when run as a CLI or by the runner.
Saved metrics:
    Accuracy, balanced accuracy, neutral/cooling precision and recall, false
    promotion rate, false neutral rate, confusion matrix JSON, and per-fold
    split metadata for each configured threshold/classifier/feature set.
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
    classification_metrics,
    classifier_models,
    coerce_feature_frame,
    feature_columns_for_set,
    load_config,
    make_pipeline,
    neutral_class,
    output_path,
    read_csv,
    validation_folds,
    write_csv,
)


@dataclass(frozen=True)
class Stage1Result:
    """Stage 1 run result."""

    status: str
    metric_rows: int
    prediction_rows: int


def stage1_for_config(
    dataset: pd.DataFrame,
    registry: pd.DataFrame,
    config: dict[str, Any],
    thresholds: list[float] | None = None,
    model_names: list[str] | None = None,
    feature_sets: list[str] | None = None,
    seed: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit/evaluate stage-1 classifiers and return metrics plus OOF predictions."""
    primary = config["targets"]["primary_target"]
    thresholds = thresholds or [float(value) for value in config["neutral_thresholds_c"]]
    model_names = model_names or list(config["models"]["classifiers"])
    feature_sets = feature_sets or list(config["feature_sets_to_test"])
    folds = validation_folds(dataset, config)
    models = classifier_models(config, seed=seed)
    metric_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []

    for feature_set in feature_sets:
        features = feature_columns_for_set(registry, dataset, feature_set, config)
        if not features:
            continue
        X_all, numeric, categorical = coerce_feature_frame(dataset, features)
        for threshold in thresholds:
            y_class_all = neutral_class(pd.to_numeric(dataset[primary], errors="coerce"), threshold)
            for fold in folds:
                X_train = X_all.loc[fold.train_index]
                X_test = X_all.loc[fold.test_index]
                y_train = y_class_all[dataset.index.get_indexer(fold.train_index)]
                y_test = y_class_all[dataset.index.get_indexer(fold.test_index)]
                test = dataset.loc[fold.test_index]
                for model_name in model_names:
                    if model_name not in models:
                        continue
                    row: dict[str, Any] = {
                        "feature_set": feature_set,
                        "feature_count": len(features),
                        "neutral_threshold_c": threshold,
                        "classifier": model_name,
                        "split_family": fold.split_family,
                        "split_name": fold.split_name,
                        "fold_id": fold.fold_id,
                        "seed": int(config["random_seed"] if seed is None else seed),
                        "n_train": len(X_train),
                        "n_test": len(X_test),
                        "n_train_cells": int(dataset.loc[fold.train_index, "cell_id"].nunique()),
                        "n_test_cells": int(test["cell_id"].nunique()),
                        "claim_boundary": CLAIM_BOUNDARY,
                    }
                    if len(set(y_train)) < 2:
                        row.update({"status": "SKIPPED_ONE_CLASS_TRAIN"})
                        metric_rows.append(row)
                        continue
                    try:
                        pipeline = make_pipeline(model_name, models[model_name], numeric, categorical)
                        pipeline.fit(X_train, y_train)
                        y_pred = pipeline.predict(X_test)
                        row.update(classification_metrics(y_test, y_pred))
                        row["status"] = "OK"
                        pred = test[
                            ["row_id", "cell_id", "forcing_day_id", "hour_sgt", "typology_label", primary]
                        ].copy()
                        pred["row_index"] = pred.index
                        pred["feature_set"] = feature_set
                        pred["neutral_threshold_c"] = threshold
                        pred["classifier"] = model_name
                        pred["split_family"] = fold.split_family
                        pred["split_name"] = fold.split_name
                        pred["fold_id"] = fold.fold_id
                        pred["seed"] = int(config["random_seed"] if seed is None else seed)
                        pred["true_class"] = y_test
                        pred["pred_stage1_class"] = y_pred
                        pred["stage1_false_promotion"] = (pred["true_class"] == "neutral") & (
                            pred["pred_stage1_class"] == "meaningful_cooling"
                        )
                        pred["stage1_false_neutral"] = (pred["true_class"] == "meaningful_cooling") & (
                            pred["pred_stage1_class"] == "neutral"
                        )
                        prediction_rows.append(pred)
                    except Exception as exc:  # pragma: no cover - defensive for long-run lane.
                        row.update({"status": "FAILED", "error": str(exc)})
                    metric_rows.append(row)

    metrics = pd.DataFrame(metric_rows)
    predictions = pd.concat(prediction_rows, ignore_index=True) if prediction_rows else pd.DataFrame()
    return metrics, predictions


def run(config_path: Path = DEFAULT_CONFIG) -> Stage1Result:
    """Run stage 1 and write metrics."""
    config = load_config(config_path)
    dataset = read_csv(output_path(config, "two_stage_dataset"))
    registry = read_csv(output_path(config, "feature_set_registry"))
    metrics, predictions = stage1_for_config(dataset, registry, config)
    write_csv(metrics, output_path(config, "stage1_classifier_metrics"))
    return Stage1Result("B86D_STAGE1_READY", len(metrics), len(predictions))


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run B8.6d stage-1 neutral-boundary classifiers and write metrics.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
