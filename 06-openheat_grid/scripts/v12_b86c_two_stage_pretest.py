"""Run the B8.6c two-stage neutral-boundary surrogate pretest.

Inputs:
    configs/v12/systemb_b86c_feature_hardening.yaml
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_hardened_surrogate_dataset.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_feature_set_registry.csv

Outputs:
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_two_stage_pretest_metrics.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_two_stage_confusion_summary.csv

Saved metrics:
    For each two-stage feature set, neutral threshold, classifier, regressor,
    split, and fold: neutral confusion matrix, neutral accuracy/precision/
    recall, combined MAE/RMSE/R2/Spearman, top10pct overlap, sign accuracy,
    anchor MAE/rank error, unstable MAE/rank error, and h10 caveat metrics.

This script reads compact CSV inputs only. It does not run QGIS or SOLWEIG,
does not read raster files, does not open or copy svfs.zip, does not create
AOI-wide prediction, does not convert Tmrt to WBGT, and does not create WBGT,
hazard_score, risk_score, B9, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
except Exception:  # pragma: no cover - depends on local sklearn version.
    HistGradientBoostingClassifier = None  # type: ignore[assignment]
    HistGradientBoostingRegressor = None  # type: ignore[assignment]

from v12_b86c_feature_inventory import DEFAULT_CONFIG, read_config, repo_path
from v12_b86c_feature_set_models import (
    coerce_feature_frame,
    finite_corr,
    parse_pipe_list,
    role_error_and_rank,
    top_fraction_overlap,
    validation_folds,
)


warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", message="Could not find the number of physical cores.*")


@dataclass(frozen=True)
class TwoStageResult:
    """Compact return record for the B8.6c two-stage pretest."""

    status: str
    metric_rows: int
    confusion_rows: int
    best_two_stage_headline: str


def one_hot_encoder() -> OneHotEncoder:
    """Create a version-compatible one-hot encoder."""
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:  # pragma: no cover - older sklearn.
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def make_preprocessor(model_name: str, numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    """Create a feature preprocessor for classifier or regressor models."""
    transformers: list[tuple[str, Any, list[str]]] = []
    if numeric:
        numeric_steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
        if model_name in {"logistic_regression", "ridge"}:
            numeric_steps.append(("scaler", StandardScaler()))
        transformers.append(("num", Pipeline(numeric_steps), numeric))
    if categorical:
        transformers.append(
            (
                "cat",
                Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", one_hot_encoder())]),
                categorical,
            )
        )
    return ColumnTransformer(transformers=transformers, remainder="drop", sparse_threshold=0.0)


def classifier_models(config: dict[str, Any]) -> dict[str, Any]:
    """Create configured stage-1 neutral classifiers."""
    seed = int(config["random_seed"])
    models: dict[str, Any] = {}
    include = set(config["two_stage"]["classifiers"])
    if "logistic_regression" in include:
        models["logistic_regression"] = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=seed)
    if "random_forest_classifier" in include:
        cfg = config["models"]["random_forest_regressor"]
        models["random_forest_classifier"] = RandomForestClassifier(
            n_estimators=int(cfg["n_estimators"]),
            max_depth=int(cfg["max_depth"]),
            min_samples_leaf=int(cfg["min_samples_leaf"]),
            random_state=seed,
            n_jobs=1,
            class_weight="balanced",
        )
    if "hist_gradient_boosting_classifier" in include and HistGradientBoostingClassifier is not None:
        cfg = config["models"]["hist_gradient_boosting_regressor"]
        models["hist_gradient_boosting_classifier"] = HistGradientBoostingClassifier(
            max_iter=int(cfg["max_iter"]),
            learning_rate=float(cfg["learning_rate"]),
            max_leaf_nodes=int(cfg["max_leaf_nodes"]),
            random_state=seed,
        )
    return models


def regressor_models(config: dict[str, Any]) -> dict[str, Any]:
    """Create configured stage-2 non-neutral regressors."""
    seed = int(config["random_seed"])
    models: dict[str, Any] = {}
    include = set(config["two_stage"]["regressors"])
    if "ridge" in include:
        models["ridge"] = Ridge(alpha=float(config["models"]["ridge"]["alpha"]))
    if "random_forest_regressor" in include:
        cfg = config["models"]["random_forest_regressor"]
        models["random_forest_regressor"] = RandomForestRegressor(
            n_estimators=int(cfg["n_estimators"]),
            max_depth=int(cfg["max_depth"]),
            min_samples_leaf=int(cfg["min_samples_leaf"]),
            random_state=seed,
            n_jobs=1,
        )
    if "hist_gradient_boosting_regressor" in include and HistGradientBoostingRegressor is not None:
        cfg = config["models"]["hist_gradient_boosting_regressor"]
        models["hist_gradient_boosting_regressor"] = HistGradientBoostingRegressor(
            max_iter=int(cfg["max_iter"]),
            learning_rate=float(cfg["learning_rate"]),
            max_leaf_nodes=int(cfg["max_leaf_nodes"]),
            random_state=seed,
        )
    return models


def make_pipeline(model_name: str, estimator: Any, numeric: list[str], categorical: list[str]) -> Pipeline:
    """Create a preprocessing pipeline for one estimator."""
    return Pipeline([("prep", make_preprocessor(model_name, numeric, categorical)), ("model", clone(estimator))])


def load_inputs(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the hardened dataset and feature-set registry."""
    dataset = pd.read_csv(
        repo_path(config["outputs"]["hardened_surrogate_dataset"]),
        dtype={"cell_id": "string", "row_id": "string", "forcing_day_id": "string"},
    )
    registry = pd.read_csv(repo_path(config["outputs"]["feature_set_registry"]))
    return dataset, registry


def neutral_confusion(y_true: np.ndarray, neutral_pred: np.ndarray, threshold: float) -> dict[str, float]:
    """Compute neutral-class confusion matrix metrics."""
    neutral_true = np.abs(y_true) <= threshold
    tp = int(np.sum(neutral_true & neutral_pred))
    tn = int(np.sum(~neutral_true & ~neutral_pred))
    fp = int(np.sum(~neutral_true & neutral_pred))
    fn = int(np.sum(neutral_true & ~neutral_pred))
    precision = tp / (tp + fp) if (tp + fp) else np.nan
    recall = tp / (tp + fn) if (tp + fn) else np.nan
    return {
        "neutral_true_positive": tp,
        "neutral_true_negative": tn,
        "neutral_false_positive": fp,
        "neutral_false_negative": fn,
        "neutral_accuracy": float((tp + tn) / max(1, len(y_true))),
        "neutral_precision": float(precision) if not math.isnan(precision) else np.nan,
        "neutral_recall": float(recall) if not math.isnan(recall) else np.nan,
    }


def h10_metrics(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, config: dict[str, Any]) -> dict[str, float]:
    """Compute h10 metrics for the combined two-stage pipeline."""
    mask = pd.to_numeric(test["hour_sgt"], errors="coerce") == int(config["diagnostic_cells"]["h10_caveat_hour"])
    if not bool(mask.any()):
        return {"h10_MAE": np.nan, "h10_Spearman": np.nan, "h10_top10pct_overlap": np.nan}
    part = test.loc[mask].copy()
    y_t = y_true[mask.to_numpy()]
    y_p = y_pred[mask.to_numpy()]
    return {
        "h10_MAE": float(mean_absolute_error(y_t, y_p)),
        "h10_Spearman": finite_corr(y_t, y_p, "spearman"),
        "h10_top10pct_overlap": top_fraction_overlap(part, y_t, y_p, 0.10),
    }


def combined_metric_row(
    feature_set: str,
    threshold: float,
    classifier_name: str,
    regressor_name: str,
    split_family: str,
    split_name: str,
    fold_id: str,
    train: pd.DataFrame,
    test: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    neutral_pred: np.ndarray,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Compute one combined two-stage metric row."""
    anchor_mae, anchor_rank = role_error_and_rank(test, y_true, y_pred, "robust_anchor_flag")
    unstable_mae, unstable_rank = role_error_and_rank(test, y_true, y_pred, "unstable_review_flag")
    row: dict[str, Any] = {
        "feature_set": feature_set,
        "neutral_threshold_c": threshold,
        "classifier": classifier_name,
        "regressor": regressor_name,
        "split_family": split_family,
        "split_name": split_name,
        "fold_id": fold_id,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "n_train_cells": int(train["cell_id"].nunique()),
        "n_test_cells": int(test["cell_id"].nunique()),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 and np.nanstd(y_true) > 0 else np.nan,
        "Spearman_observed_vs_predicted": finite_corr(y_true, y_pred, "spearman"),
        "top10pct_overlap": top_fraction_overlap(test, y_true, y_pred, 0.10),
        "sign_accuracy": float(np.mean(np.sign(y_true) == np.sign(y_pred))),
        "robust_anchor_MAE": anchor_mae,
        "robust_anchor_mean_rank_error": anchor_rank,
        "unstable_review_MAE": unstable_mae,
        "unstable_review_mean_rank_error": unstable_rank,
        "claim_boundary": "Two-stage pretest over compact SOLWEIG-derived labels only; not AOI-wide prediction.",
    }
    row.update(neutral_confusion(y_true, neutral_pred, threshold))
    row.update(h10_metrics(test, y_true, y_pred, config))
    return row


def fit_classifier(
    train: pd.DataFrame,
    usable_features: list[str],
    numeric: list[str],
    categorical: list[str],
    y_class: np.ndarray,
    classifier_name: str,
    classifier: Any,
) -> Pipeline:
    """Fit a classifier, falling back to a deterministic dummy if one class exists."""
    estimator = DummyClassifier(strategy="most_frequent") if len(np.unique(y_class)) < 2 else classifier
    pipe = make_pipeline(classifier_name, estimator, numeric, categorical)
    pipe.fit(train[usable_features], y_class)
    return pipe


def fit_regressor(
    train: pd.DataFrame,
    usable_features: list[str],
    numeric: list[str],
    categorical: list[str],
    target: str,
    threshold: float,
    regressor_name: str,
    regressor: Any,
) -> Pipeline:
    """Fit a non-neutral regressor, falling back to dummy if needed."""
    y = pd.to_numeric(train[target], errors="coerce")
    non_neutral = y.abs() > threshold
    train_stage2 = train.loc[non_neutral].copy()
    if len(train_stage2) < 5 or y.loc[non_neutral].nunique() <= 1:
        estimator = DummyRegressor(strategy="mean")
        train_stage2 = train.copy()
    else:
        estimator = regressor
    pipe = make_pipeline(regressor_name, estimator, numeric, categorical)
    pipe.fit(train_stage2[usable_features], pd.to_numeric(train_stage2[target], errors="coerce").to_numpy(dtype=float))
    return pipe


def run_two_stage(dataset: pd.DataFrame, registry: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run all configured two-stage pretests."""
    primary = config["targets"]["primary"]
    thresholds = [float(config["targets"]["neutral_delta_abs_threshold_c"]), *[float(v) for v in config["targets"]["neutral_sensitivity_thresholds_c"]]]
    classifiers = classifier_models(config)
    regressors = regressor_models(config)
    folds = validation_folds(dataset, config)
    metrics: list[dict[str, Any]] = []
    confusion_rows: list[dict[str, Any]] = []
    registry = registry.loc[registry["feature_set"].astype(str).isin(config["two_stage"]["feature_sets"])].copy()
    for item in registry.itertuples(index=False):
        features = parse_pipe_list(item.feature_columns)
        if not features:
            continue
        feature_set = str(item.feature_set)
        prepared, numeric, categorical = coerce_feature_frame(dataset, features)
        usable_features = numeric + categorical
        if not usable_features:
            continue
        for threshold in thresholds:
            for split_family, split_name, fold_id, train_idx, test_idx in folds:
                train = prepared.loc[train_idx].copy()
                test = prepared.loc[test_idx].copy()
                train = train.loc[train[primary].notna()].copy()
                test = test.loc[test[primary].notna()].copy()
                if train.empty or test.empty:
                    continue
                y_train = pd.to_numeric(train[primary], errors="coerce").to_numpy(dtype=float)
                y_true = pd.to_numeric(test[primary], errors="coerce").to_numpy(dtype=float)
                y_class = np.abs(y_train) <= threshold
                for classifier_name, classifier in classifiers.items():
                    classifier_pipe = fit_classifier(
                        train,
                        usable_features,
                        numeric,
                        categorical,
                        y_class,
                        classifier_name,
                        classifier,
                    )
                    neutral_pred = classifier_pipe.predict(test[usable_features]).astype(bool)
                    for regressor_name, regressor in regressors.items():
                        regressor_pipe = fit_regressor(
                            train,
                            usable_features,
                            numeric,
                            categorical,
                            primary,
                            threshold,
                            regressor_name,
                            regressor,
                        )
                        reg_pred = regressor_pipe.predict(test[usable_features])
                        y_pred = np.where(neutral_pred, 0.0, reg_pred)
                        row = combined_metric_row(
                            feature_set,
                            threshold,
                            classifier_name,
                            regressor_name,
                            split_family,
                            split_name,
                            fold_id,
                            train,
                            test,
                            y_true,
                            y_pred,
                            neutral_pred,
                            config,
                        )
                        metrics.append(row)
                        confusion = {
                            key: row[key]
                            for key in [
                                "feature_set",
                                "neutral_threshold_c",
                                "classifier",
                                "regressor",
                                "split_family",
                                "split_name",
                                "fold_id",
                                "n_test",
                                "neutral_true_positive",
                                "neutral_true_negative",
                                "neutral_false_positive",
                                "neutral_false_negative",
                                "neutral_accuracy",
                                "neutral_precision",
                                "neutral_recall",
                            ]
                        }
                        confusion["claim_boundary"] = "Neutral-class confusion diagnostic only."
                        confusion_rows.append(confusion)
    return pd.DataFrame(metrics), pd.DataFrame(confusion_rows)


def best_headline(metrics: pd.DataFrame) -> str:
    """Return a concise headline for the best two-stage pretest."""
    if metrics.empty:
        return "Two-stage pretest unavailable."
    support = metrics.loc[metrics["split_family"].isin(["spatial_holdout", "typology_holdout", "cell_group_holdout"])].copy()
    if support.empty:
        return "Two-stage supporting holdouts unavailable."
    grouped = support.groupby(["feature_set", "neutral_threshold_c", "classifier", "regressor"], as_index=False).agg(
        MAE=("MAE", "mean"),
        Spearman=("Spearman_observed_vs_predicted", "mean"),
        top10pct=("top10pct_overlap", "mean"),
        neutral_accuracy=("neutral_accuracy", "mean"),
        anchor_mae=("robust_anchor_MAE", "mean"),
    )
    grouped = grouped.sort_values(["neutral_accuracy", "Spearman", "top10pct", "anchor_mae", "MAE"], ascending=[False, False, False, True, True])
    best = grouped.iloc[0]
    return (
        f"{best.feature_set}, threshold={best.neutral_threshold_c:.2f}, "
        f"{best.classifier}+{best.regressor}: neutral_accuracy={best.neutral_accuracy:.3f}, "
        f"supporting Spearman={best.Spearman:.3f}, top10pct={best.top10pct:.3f}."
    )


def run(config_path: Path = DEFAULT_CONFIG) -> TwoStageResult:
    """Run the B8.6c two-stage pretest and write compact outputs."""
    config = read_config(config_path)
    try:
        dataset, registry = load_inputs(config)
    except FileNotFoundError:
        pd.DataFrame().to_csv(repo_path(config["outputs"]["two_stage_pretest_metrics"]), index=False)
        pd.DataFrame().to_csv(repo_path(config["outputs"]["two_stage_confusion_summary"]), index=False)
        return TwoStageResult("B86C_BLOCKED_INPUT", 0, 0, "Inputs blocked.")
    metrics, confusion = run_two_stage(dataset, registry, config)
    metrics.to_csv(repo_path(config["outputs"]["two_stage_pretest_metrics"]), index=False)
    confusion.to_csv(repo_path(config["outputs"]["two_stage_confusion_summary"]), index=False)
    return TwoStageResult(
        status="B86C_TWO_STAGE_PRETEST_READY" if not metrics.empty else "B86C_BLOCKED_INPUT",
        metric_rows=int(len(metrics)),
        confusion_rows=int(len(confusion)),
        best_two_stage_headline=best_headline(metrics),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run the B8.6c two-stage neutral-boundary surrogate pretest.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6c YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
