"""Run B8.6g2 two-stage neutral-gated surrogate models.

Inputs:
    b86g2_modeling_dataset.csv, b86g2_feature_set_registry.csv, and
    deterministic B8.6g2 validation folds.
Outputs:
    b86g2_combined_pipeline_metrics.csv, b86g2_two_stage_metrics.csv,
    b86g2_metrics_by_split.csv, b86g2_metrics_by_spatial_bin.csv,
    b86g2_metrics_by_typology.csv, b86g2_metrics_by_hour.csv, and
    b86g2_oof_predictions.csv.
Saved metrics:
    Stage-1 neutral classification metrics, combined two-stage regression and
    ranking metrics, selected OOF predictions, and selected subgroup metrics.
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
    COMBO_COLS,
    DEFAULT_CONFIG,
    classification_metrics,
    classifier_models,
    coerce_feature_frame,
    feature_columns_for_set,
    load_config,
    make_pipeline,
    metric_group_summary,
    neutral_class,
    output_path,
    read_csv,
    regression_metrics,
    regressor_models,
    role_error_and_rank,
    selected_two_stage_combo,
    validation_folds,
    write_csv,
)


@dataclass(frozen=True)
class TwoStageResult:
    """Two-stage model result."""

    status: str
    fold_metric_rows: int
    aggregate_metric_rows: int
    selected_feature_set: str
    selected_classifier: str
    selected_regressor: str


def _metric_row(
    dataset: pd.DataFrame,
    fold_test: pd.DataFrame,
    y_test: np.ndarray,
    y_true_class: np.ndarray,
    pred_class: np.ndarray,
    stage2_pred: np.ndarray,
    feature_set: str,
    classifier: str,
    regressor: str,
    feature_count: int,
    fold: Any,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Build one fold-level combined metric row."""
    threshold = float(config["neutral_threshold_c"])
    combined_pred = np.where(pred_class == "meaningful_cooling", stage2_pred, 0.0)
    row: dict[str, Any] = {
        "feature_set": feature_set,
        "feature_count": feature_count,
        "neutral_threshold_c": threshold,
        "classifier": classifier,
        "regressor": regressor,
        "split_family": fold.split_family,
        "split_name": fold.split_name,
        "fold_id": fold.fold_id,
        "seed": int(config["random_seed"]),
        "n_test": len(fold_test),
        "n_test_cells": int(fold_test["cell_id"].nunique()),
        "target": config["primary_target"],
        "claim_boundary": CLAIM_BOUNDARY,
        "status": "OK",
    }
    row.update(regression_metrics(fold_test, y_test, combined_pred, threshold))
    row.update(classification_metrics(y_true_class, pred_class))
    anchor_mae, anchor_rank = role_error_and_rank(fold_test, y_test, combined_pred, config["diagnostic_cells"]["anchor_cells"])
    unstable_mae, unstable_rank = role_error_and_rank(fold_test, y_test, combined_pred, config["diagnostic_cells"]["unstable_cells"])
    row["anchor_MAE"] = anchor_mae
    row["anchor_mean_rank_error"] = anchor_rank
    row["unstable_MAE"] = unstable_mae
    row["unstable_mean_rank_error"] = unstable_rank
    return row


def evaluate_two_stage_with_features(
    dataset: pd.DataFrame,
    features: list[str],
    feature_set: str,
    config: dict[str, Any],
    classifier_names: list[str] | None = None,
    regressor_names: list[str] | None = None,
    return_predictions: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate two-stage models for one feature list."""
    threshold = float(config["neutral_threshold_c"])
    primary = config["primary_target"]
    classifier_names = classifier_names or list(config["models"]["classifiers"])
    regressor_names = regressor_names or list(config["models"]["regressors"])
    folds = validation_folds(dataset, config)
    classifiers = classifier_models(config)
    regressors = regressor_models(config)
    X_all, numeric, categorical = coerce_feature_frame(dataset, features)
    y_delta = pd.to_numeric(dataset[primary], errors="coerce")
    y_class_all = neutral_class(y_delta.to_numpy(dtype=float), threshold)
    metric_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []

    for fold in folds:
        X_train = X_all.loc[fold.train_index]
        X_test = X_all.loc[fold.test_index]
        test = dataset.loc[fold.test_index].copy()
        y_train_class = y_class_all[dataset.index.get_indexer(fold.train_index)]
        y_test_class = y_class_all[dataset.index.get_indexer(fold.test_index)]
        y_test = y_delta.loc[fold.test_index].to_numpy(dtype=float)
        classifier_predictions: dict[str, np.ndarray] = {}
        for classifier_name in classifier_names:
            if classifier_name not in classifiers:
                continue
            if len(set(y_train_class)) < 2:
                classifier_predictions[classifier_name] = np.full(len(test), y_train_class[0], dtype=object)
                continue
            pipeline = make_pipeline(classifier_name, classifiers[classifier_name], numeric, categorical)
            pipeline.fit(X_train, y_train_class)
            classifier_predictions[classifier_name] = np.asarray(pipeline.predict(X_test), dtype=object)

        train_non_neutral = y_delta.loc[fold.train_index].abs() > threshold
        train_index = fold.train_index[train_non_neutral.to_numpy()]
        regressor_predictions: dict[str, np.ndarray] = {}
        for regressor_name in regressor_names:
            if regressor_name not in regressors:
                continue
            if len(train_index) < 5 or y_delta.loc[train_index].nunique(dropna=True) < 2:
                regressor_predictions[regressor_name] = np.zeros(len(test), dtype=float)
                continue
            pipeline = make_pipeline(regressor_name, regressors[regressor_name], numeric, categorical)
            pipeline.fit(X_all.loc[train_index], y_delta.loc[train_index].to_numpy(dtype=float))
            regressor_predictions[regressor_name] = np.asarray(pipeline.predict(X_test), dtype=float)

        for classifier_name, pred_class in classifier_predictions.items():
            for regressor_name, stage2_pred in regressor_predictions.items():
                row = _metric_row(
                    dataset,
                    test,
                    y_test,
                    y_test_class,
                    pred_class,
                    stage2_pred,
                    feature_set,
                    classifier_name,
                    regressor_name,
                    len(features),
                    fold,
                    config,
                )
                metric_rows.append(row)
                if return_predictions:
                    combined_pred = np.where(pred_class == "meaningful_cooling", stage2_pred, 0.0)
                    pred = test[
                        [
                            "row_id",
                            "cell_id",
                            "forcing_day_id",
                            "hour_sgt",
                            "typology_label",
                            primary,
                            "anchor_cell_flag",
                            "known_neutral_cell_flag",
                            "unstable_cell_flag",
                        ]
                    ].copy()
                    pred["row_index"] = pred.index
                    pred["feature_set"] = feature_set
                    pred["neutral_threshold_c"] = threshold
                    pred["classifier"] = classifier_name
                    pred["regressor"] = regressor_name
                    pred["split_family"] = fold.split_family
                    pred["split_name"] = fold.split_name
                    pred["fold_id"] = fold.fold_id
                    pred["seed"] = int(config["random_seed"])
                    pred["true_class"] = y_test_class
                    pred["pred_stage1_class"] = pred_class
                    pred["pred_stage2_delta"] = stage2_pred
                    pred["pred_combined_delta"] = combined_pred
                    pred["true_delta"] = y_test
                    pred["combined_abs_error"] = np.abs(combined_pred - y_test)
                    pred["combined_false_promotion"] = (pred["true_class"] == "neutral") & (
                        pred["pred_stage1_class"] == "meaningful_cooling"
                    )
                    pred["combined_false_neutral"] = (pred["true_class"] == "meaningful_cooling") & (
                        pred["pred_stage1_class"] == "neutral"
                    )
                    pred["claim_boundary"] = CLAIM_BOUNDARY
                    prediction_rows.append(pred)

    metrics = pd.DataFrame(metric_rows)
    predictions = pd.concat(prediction_rows, ignore_index=True) if prediction_rows else pd.DataFrame()
    return metrics, predictions


def all_two_stage_metrics(dataset: pd.DataFrame, registry: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Evaluate all requested feature sets, classifiers, and regressors."""
    frames: list[pd.DataFrame] = []
    for feature_set in config["feature_sets_to_test"]:
        features = feature_columns_for_set(registry, dataset, feature_set)
        if not features:
            continue
        metrics, _ = evaluate_two_stage_with_features(dataset, features, feature_set, config, return_predictions=False)
        frames.append(metrics)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def selected_oof_predictions(dataset: pd.DataFrame, registry: pd.DataFrame, config: dict[str, Any], best: dict[str, Any]) -> pd.DataFrame:
    """Rerun the selected combo and return selected OOF predictions."""
    feature_set = str(best["feature_set"])
    features = feature_columns_for_set(registry, dataset, feature_set)
    _, predictions = evaluate_two_stage_with_features(
        dataset,
        features,
        feature_set,
        config,
        classifier_names=[str(best["classifier"])],
        regressor_names=[str(best["regressor"])],
        return_predictions=True,
    )
    return predictions


def subgroup_metrics(predictions: pd.DataFrame, group_col: str, threshold: float) -> pd.DataFrame:
    """Compute selected OOF subgroup metrics."""
    rows: list[dict[str, Any]] = []
    if predictions.empty:
        return pd.DataFrame()
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
        row.update(classification_metrics(group["true_class"].to_numpy(), group["pred_stage1_class"].to_numpy()))
        rows.append(row)
    return pd.DataFrame(rows)


def selected_by_split(combined: pd.DataFrame, best: dict[str, Any]) -> pd.DataFrame:
    """Aggregate selected fold metrics by split family/name."""
    selected = combined.copy()
    for column in COMBO_COLS:
        selected = selected.loc[selected[column].astype(str).eq(str(best[column]))]
    return metric_group_summary(selected, ["split_family", "split_name"])


def run(config_path: Path = DEFAULT_CONFIG) -> TwoStageResult:
    """Run the full B8.6g2 two-stage model suite."""
    config = load_config(config_path)
    dataset = read_csv(output_path(config, "modeling_dataset"))
    registry = read_csv(output_path(config, "feature_set_registry"))
    combined = all_two_stage_metrics(dataset, registry, config)
    write_csv(combined, output_path(config, "combined_pipeline_metrics"))
    aggregate = metric_group_summary(combined, COMBO_COLS + ["split_family"])
    write_csv(aggregate, output_path(config, "two_stage_metrics"))
    best = selected_two_stage_combo(combined, config)
    oof = selected_oof_predictions(dataset, registry, config, best)
    write_csv(oof, output_path(config, "oof_predictions"))
    by_split = selected_by_split(combined, best)
    write_csv(by_split, output_path(config, "metrics_by_split"))
    threshold = float(best.get("neutral_threshold_c", config["neutral_threshold_c"]))
    spatial_oof = oof.loc[oof["split_family"].astype(str).eq("spatial_holdout")].copy()
    write_csv(subgroup_metrics(spatial_oof, "split_name", threshold), output_path(config, "metrics_by_spatial_bin"))
    write_csv(subgroup_metrics(oof, "typology_label", threshold), output_path(config, "metrics_by_typology"))
    write_csv(subgroup_metrics(oof, "hour_sgt", threshold), output_path(config, "metrics_by_hour"))
    return TwoStageResult(
        "B86G2_TWO_STAGE_READY",
        len(combined),
        len(aggregate),
        str(best.get("feature_set", "")),
        str(best.get("classifier", "")),
        str(best.get("regressor", "")),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run B8.6g2 two-stage neutral-gated surrogate models.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
