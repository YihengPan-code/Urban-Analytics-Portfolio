"""Run B8.6b surrogate model benchmarks.

Inputs:
    configs/v12/systemb_b86b_surrogate_promotion.yaml
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_surrogate_dataset.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_feature_schema.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_target_schema.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_validation_splits.csv

Outputs:
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_model_metrics_by_split.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_forcing_day_holdout_metrics.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_cell_group_holdout_metrics.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_hour_holdout_metrics.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_spatial_holdout_metrics.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_typology_holdout_metrics.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_target_sensitivity_metrics.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_topk_overlap_metrics.csv

Saved metrics:
    For each target/model/split/fold: n_train, n_test, MAE, RMSE, R2,
    Spearman, Pearson, bias, p90 absolute error, sign accuracy, top5/top10pct/
    top20pct overlap, worst-cell error, robust-anchor MAE and rank error,
    neutral-boundary accuracy, unstable-review error, h10 caveat metrics, and
    MAE improvement over dummy.

This script uses standard sklearn models only. It does not run QGIS or
SOLWEIG, does not read raster files, does not create AOI-wide prediction, does
not convert Tmrt to WBGT, and does not create WBGT, hazard_score, risk_score,
B9, or System A/B coupling outputs.
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
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:  # HistGradientBoosting is available in modern sklearn, but keep fallback explicit.
    from sklearn.ensemble import HistGradientBoostingRegressor
except Exception:  # pragma: no cover - depends on local sklearn version.
    HistGradientBoostingRegressor = None  # type: ignore[assignment]

from v12_b86b_surrogate_inventory import DEFAULT_CONFIG, read_config, repo_path


warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", message="Could not find the number of physical cores.*")


@dataclass(frozen=True)
class ModelResult:
    """Compact return record for the B8.6b model step."""

    status: str
    metrics_rows: int
    best_primary_model: str
    forcing_day_headline: str
    target_sensitivity_headline: str


def bool_series(series: pd.Series) -> pd.Series:
    """Parse CSV booleans robustly."""
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def load_inputs(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load dataset, feature schema, target schema, and validation split manifest."""
    dataset = pd.read_csv(
        repo_path(config["outputs"]["surrogate_dataset"]),
        dtype={"cell_id": "string", "row_id": "string", "forcing_day_id": "string"},
    )
    schema = pd.read_csv(repo_path(config["outputs"]["feature_schema"]))
    target_schema = pd.read_csv(repo_path(config["outputs"]["target_schema"]))
    splits = pd.read_csv(
        repo_path(config["outputs"]["validation_splits"]),
        dtype={"cell_id": "string", "row_id": "string", "forcing_day_id": "string", "fold_id": "string"},
    )
    return dataset, schema, target_schema, splits


def selected_features(schema: pd.DataFrame) -> list[str]:
    """Return selected B8.6b predictor columns."""
    if schema.empty or "include_in_model" not in schema.columns:
        return []
    return schema.loc[bool_series(schema["include_in_model"]), "column_name"].astype(str).tolist()


def available_targets(target_schema: pd.DataFrame) -> list[str]:
    """Return available B8.6b target names."""
    if target_schema.empty or "available" not in target_schema.columns:
        return []
    return target_schema.loc[bool_series(target_schema["available"]), "target_name"].astype(str).tolist()


def coerce_model_features(dataset: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Coerce selected predictors to numeric and drop unusable constants."""
    out = dataset.copy()
    retained: list[str] = []
    for feature in features:
        if feature not in out.columns:
            continue
        numeric = pd.to_numeric(out[feature], errors="coerce")
        if numeric.notna().sum() == 0 or numeric.nunique(dropna=True) <= 1:
            continue
        out[feature] = numeric
        retained.append(feature)
    return out, retained


def split_folds(splits: pd.DataFrame) -> list[tuple[str, str, str, pd.DataFrame]]:
    """Return valid train/test split fold manifests."""
    valid = splits.loc[
        splits["role"].isin(["train", "test"])
        & splits["split_status"].isin(["AVAILABLE", "DIAGNOSTIC_ONLY"])
    ].copy()
    folds: list[tuple[str, str, str, pd.DataFrame]] = []
    for (family, name, fold_id), part in valid.groupby(["split_family", "split_name", "fold_id"], sort=True):
        if set(part["role"].astype(str)) == {"train", "test"}:
            folds.append((str(family), str(name), str(fold_id), part.copy()))
    return folds


def make_models(config: dict[str, Any]) -> dict[str, Any]:
    """Create modest documented sklearn models."""
    seed = int(config["random_seed"])
    models: dict[str, Any] = {}
    include = set(config["models"]["include"])
    if "dummy_mean" in include:
        models["dummy_mean"] = DummyRegressor(strategy="mean")
    if "linear_regression" in include:
        models["linear_regression"] = LinearRegression()
    if "ridge" in include:
        models["ridge"] = Ridge(alpha=float(config["models"]["ridge"]["alpha"]))
    if "elasticnet" in include:
        models["elasticnet"] = ElasticNet(
            alpha=float(config["models"]["elasticnet"]["alpha"]),
            l1_ratio=float(config["models"]["elasticnet"]["l1_ratio"]),
            max_iter=10000,
            random_state=seed,
        )
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
    elif "hist_gradient_boosting_regressor" in include:
        cfg = config["models"]["gradient_boosting_regressor"]
        models["gradient_boosting_regressor"] = GradientBoostingRegressor(
            n_estimators=int(cfg["n_estimators"]),
            learning_rate=float(cfg["learning_rate"]),
            max_depth=int(cfg["max_depth"]),
            random_state=seed,
        )
    return models


def make_pipeline(model_name: str, estimator: Any, features: list[str]) -> Pipeline:
    """Create a numeric preprocessing and regression pipeline."""
    numeric_steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if model_name in {"linear_regression", "ridge", "elasticnet"}:
        numeric_steps.append(("scaler", StandardScaler()))
    preprocessor = ColumnTransformer(
        transformers=[("num", Pipeline(numeric_steps), features)],
        remainder="drop",
        sparse_threshold=0.0,
    )
    return Pipeline([("prep", preprocessor), ("model", clone(estimator))])


def finite_corr(y_true: np.ndarray, y_pred: np.ndarray, method: str) -> float:
    """Compute Pearson or Spearman correlation when meaningful."""
    frame = pd.DataFrame({"true": y_true, "pred": y_pred}).dropna()
    if len(frame) < 2 or frame["true"].nunique() <= 1 or frame["pred"].nunique() <= 1:
        return float("nan")
    if method == "spearman":
        left = frame["true"].rank(method="average").to_numpy(dtype=float)
        right = frame["pred"].rank(method="average").to_numpy(dtype=float)
    else:
        left = frame["true"].to_numpy(dtype=float)
        right = frame["pred"].to_numpy(dtype=float)
    left = left - float(np.mean(left))
    right = right - float(np.mean(right))
    denom = math.sqrt(float(np.sum(left * left)) * float(np.sum(right * right)))
    if denom == 0:
        return float("nan")
    return float(np.sum(left * right) / denom)


def priority_low_is_top(target: str) -> bool:
    """Return whether lower target values define cooling-priority top-k."""
    return target.startswith("delta_tmrt")


def cell_average_frame(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:
    """Build per-cell observed/predicted averages for ranking diagnostics."""
    frame = test[["cell_id"]].copy()
    frame["y_true"] = y_true
    frame["y_pred"] = y_pred
    return frame.groupby("cell_id", as_index=False)[["y_true", "y_pred"]].mean(numeric_only=True)


def top_overlap(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, target: str, k: int) -> float:
    """Compute per-cell top-k overlap."""
    by_cell = cell_average_frame(test, y_true, y_pred)
    if by_cell.empty:
        return float("nan")
    k = min(max(1, k), len(by_cell))
    if priority_low_is_top(target):
        true_top = set(by_cell.nsmallest(k, "y_true")["cell_id"].astype(str))
        pred_top = set(by_cell.nsmallest(k, "y_pred")["cell_id"].astype(str))
    else:
        true_top = set(by_cell.nlargest(k, "y_true")["cell_id"].astype(str))
        pred_top = set(by_cell.nlargest(k, "y_pred")["cell_id"].astype(str))
    return float(len(true_top & pred_top) / k)


def top_fraction_overlap(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, target: str, fraction: float) -> float:
    """Compute per-cell top fraction overlap."""
    n_cells = int(test["cell_id"].nunique())
    return top_overlap(test, y_true, y_pred, target, max(1, int(math.ceil(fraction * n_cells))))


def sign_accuracy(y_true: np.ndarray, y_pred: np.ndarray, target: str) -> float:
    """Compute sign agreement for delta targets."""
    if not target.startswith("delta_tmrt") or len(y_true) == 0:
        return float("nan")
    return float(np.mean(np.sign(y_true) == np.sign(y_pred)))


def worst_cell_error(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray) -> tuple[str, float]:
    """Return the worst per-cell mean absolute error."""
    frame = test[["cell_id"]].copy()
    frame["abs_error"] = np.abs(y_pred - y_true)
    by_cell = frame.groupby("cell_id")["abs_error"].mean().sort_values(ascending=False)
    if by_cell.empty:
        return "", float("nan")
    return str(by_cell.index[0]), float(by_cell.iloc[0])


def role_error_and_rank(
    test: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    cells: list[str],
    target: str,
) -> tuple[float, float]:
    """Compute mean absolute error and mean rank error for configured cells."""
    by_cell = cell_average_frame(test, y_true, y_pred)
    if by_cell.empty:
        return float("nan"), float("nan")
    ascending = priority_low_is_top(target)
    by_cell["true_rank"] = by_cell["y_true"].rank(method="min", ascending=ascending)
    by_cell["pred_rank"] = by_cell["y_pred"].rank(method="min", ascending=ascending)
    subset = by_cell.loc[by_cell["cell_id"].astype(str).isin(cells)].copy()
    if subset.empty:
        return float("nan"), float("nan")
    mae = float((subset["y_pred"] - subset["y_true"]).abs().mean())
    rank_error = float((subset["pred_rank"] - subset["true_rank"]).abs().mean())
    return mae, rank_error


def neutral_accuracy(y_true: np.ndarray, y_pred: np.ndarray, target: str, threshold: float) -> float:
    """Classify neutral-boundary rows for delta targets."""
    if not target.startswith("delta_tmrt") or len(y_true) == 0:
        return float("nan")
    return float(np.mean((np.abs(y_true) <= threshold) == (np.abs(y_pred) <= threshold)))


def subset_metrics(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, mask: pd.Series, target: str) -> dict[str, float]:
    """Compute h10 caveat metrics for a subset of a test fold."""
    if not bool(mask.any()):
        return {"h10_MAE": float("nan"), "h10_Spearman": float("nan"), "h10_top10pct_overlap": float("nan")}
    y_t = y_true[mask.to_numpy()]
    y_p = y_pred[mask.to_numpy()]
    test_part = test.loc[mask].copy()
    return {
        "h10_MAE": float(mean_absolute_error(y_t, y_p)),
        "h10_Spearman": finite_corr(y_t, y_p, "spearman"),
        "h10_top10pct_overlap": top_fraction_overlap(test_part, y_t, y_p, target, 0.10),
    }


def metric_row(
    target: str,
    model_name: str,
    split_family: str,
    split_name: str,
    fold_id: str,
    train: pd.DataFrame,
    test: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Compute one target/model/fold metric row."""
    residual = y_pred - y_true
    worst_id, worst_error = worst_cell_error(test, y_true, y_pred)
    anchors = list(config["diagnostic_cells"]["robust_priority_anchors"])
    unstable = list(config["diagnostic_cells"]["unstable_review_cells"])
    anchor_mae, anchor_rank_error = role_error_and_rank(test, y_true, y_pred, anchors, target)
    unstable_mae, unstable_rank_error = role_error_and_rank(test, y_true, y_pred, unstable, target)
    h10_mask = pd.to_numeric(test["hour_sgt"], errors="coerce") == int(config["diagnostic_cells"]["h10_caveat_hour"])
    row: dict[str, Any] = {
        "target": target,
        "model": model_name,
        "split_family": split_family,
        "split_name": split_name,
        "fold_id": fold_id,
        "split_role": "diagnostic_only" if split_family in config["validation"]["diagnostic_split_families"] else "main",
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "n_train_cells": int(train["cell_id"].nunique()),
        "n_test_cells": int(test["cell_id"].nunique()),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 and np.nanstd(y_true) > 0 else float("nan"),
        "Spearman_observed_vs_predicted": finite_corr(y_true, y_pred, "spearman"),
        "Pearson_observed_vs_predicted": finite_corr(y_true, y_pred, "pearson"),
        "bias": float(np.mean(residual)),
        "p90_abs_error": float(np.percentile(np.abs(residual), 90)),
        "sign_accuracy": sign_accuracy(y_true, y_pred, target),
        "top5_overlap": top_overlap(test, y_true, y_pred, target, 5),
        "top10pct_overlap": top_fraction_overlap(test, y_true, y_pred, target, 0.10),
        "top20pct_overlap": top_fraction_overlap(test, y_true, y_pred, target, 0.20),
        "worst_cell_id": worst_id,
        "worst_cell_error": worst_error,
        "robust_anchor_MAE": anchor_mae,
        "robust_anchor_mean_rank_error": anchor_rank_error,
        "neutral_boundary_classification_accuracy": neutral_accuracy(
            y_true,
            y_pred,
            target,
            float(config["targets"]["neutral_delta_abs_threshold_c"]),
        ),
        "unstable_review_MAE": unstable_mae,
        "unstable_review_mean_rank_error": unstable_rank_error,
    }
    row.update(subset_metrics(test, y_true, y_pred, h10_mask, target))
    return row


def add_dummy_improvement(metrics: pd.DataFrame) -> pd.DataFrame:
    """Attach same-fold dummy MAE and improvement over dummy."""
    if metrics.empty:
        return metrics
    keys = ["target", "split_family", "split_name", "fold_id"]
    dummy = metrics.loc[metrics["model"] == "dummy_mean", keys + ["MAE"]].rename(columns={"MAE": "dummy_MAE"})
    out = metrics.merge(dummy, on=keys, how="left")
    out["MAE_improvement_over_dummy"] = out["dummy_MAE"] - out["MAE"]
    out["MAE_improvement_fraction_over_dummy"] = np.where(out["dummy_MAE"] > 0, out["MAE_improvement_over_dummy"] / out["dummy_MAE"], np.nan)
    return out


def prediction_records_for_model(
    dataset: pd.DataFrame,
    schema: pd.DataFrame,
    splits: pd.DataFrame,
    config: dict[str, Any],
    target: str,
    model_name: str,
) -> pd.DataFrame:
    """Return row-level predictions for one target/model across all split folds."""
    features = selected_features(schema)
    dataset, features = coerce_model_features(dataset, features)
    if not features:
        return pd.DataFrame()
    models = make_models(config)
    if model_name not in models:
        return pd.DataFrame()
    row_lookup = dataset.set_index("row_id", drop=False)
    rows: list[pd.DataFrame] = []
    for split_family, split_name, fold_id, manifest in split_folds(splits):
        train_ids = manifest.loc[manifest["role"] == "train", "row_id"].dropna().astype(str)
        test_ids = manifest.loc[manifest["role"] == "test", "row_id"].dropna().astype(str)
        train = row_lookup.loc[train_ids].copy()
        test = row_lookup.loc[test_ids].copy()
        train = train.loc[train[target].notna()].copy()
        test = test.loc[test[target].notna()].copy()
        if train.empty or test.empty:
            continue
        pipe = make_pipeline(model_name, models[model_name], features)
        pipe.fit(train[features], pd.to_numeric(train[target], errors="coerce").to_numpy(dtype=float))
        y_true = pd.to_numeric(test[target], errors="coerce").to_numpy(dtype=float)
        y_pred = pipe.predict(test[features])
        part = test[["row_id", "cell_id", "forcing_day_id", "hour_sgt"]].copy()
        part["target"] = target
        part["model"] = model_name
        part["split_family"] = split_family
        part["split_name"] = split_name
        part["fold_id"] = fold_id
        part["y_true"] = y_true
        part["y_pred"] = y_pred
        part["error"] = part["y_pred"] - part["y_true"]
        part["abs_error"] = part["error"].abs()
        rows.append(part)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def run_model_metrics(
    dataset: pd.DataFrame,
    schema: pd.DataFrame,
    target_schema: pd.DataFrame,
    splits: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Run every configured sklearn model over every available target and split."""
    features = selected_features(schema)
    dataset, features = coerce_model_features(dataset, features)
    targets = [target for target in available_targets(target_schema) if target in dataset.columns]
    models = make_models(config)
    row_lookup = dataset.set_index("row_id", drop=False)
    metrics: list[dict[str, Any]] = []
    for target in targets:
        for split_family, split_name, fold_id, manifest in split_folds(splits):
            train_ids = manifest.loc[manifest["role"] == "train", "row_id"].dropna().astype(str)
            test_ids = manifest.loc[manifest["role"] == "test", "row_id"].dropna().astype(str)
            train = row_lookup.loc[train_ids].copy()
            test = row_lookup.loc[test_ids].copy()
            train = train.loc[train[target].notna()].copy()
            test = test.loc[test[target].notna()].copy()
            if train.empty or test.empty:
                continue
            y_train = pd.to_numeric(train[target], errors="coerce").to_numpy(dtype=float)
            y_true = pd.to_numeric(test[target], errors="coerce").to_numpy(dtype=float)
            for model_name, estimator in models.items():
                pipe = make_pipeline(model_name, estimator, features)
                pipe.fit(train[features], y_train)
                y_pred = pipe.predict(test[features])
                metrics.append(
                    metric_row(
                        target=target,
                        model_name=model_name,
                        split_family=split_family,
                        split_name=split_name,
                        fold_id=fold_id,
                        train=train,
                        test=test,
                        y_true=y_true,
                        y_pred=y_pred,
                        config=config,
                    )
                )
    return add_dummy_improvement(pd.DataFrame(metrics))


def summarize_split(metrics: pd.DataFrame, split_family: str) -> pd.DataFrame:
    """Summarize model metrics for one split family by target/model."""
    subset = metrics.loc[metrics["split_family"] == split_family].copy()
    if subset.empty:
        return pd.DataFrame()
    numeric_cols = [
        "n_train",
        "n_test",
        "n_train_cells",
        "n_test_cells",
        "MAE",
        "RMSE",
        "R2",
        "Spearman_observed_vs_predicted",
        "Pearson_observed_vs_predicted",
        "bias",
        "p90_abs_error",
        "sign_accuracy",
        "top5_overlap",
        "top10pct_overlap",
        "top20pct_overlap",
        "worst_cell_error",
        "robust_anchor_MAE",
        "robust_anchor_mean_rank_error",
        "neutral_boundary_classification_accuracy",
        "unstable_review_MAE",
        "unstable_review_mean_rank_error",
        "h10_MAE",
        "h10_Spearman",
        "h10_top10pct_overlap",
        "MAE_improvement_fraction_over_dummy",
    ]
    summary = subset.groupby(["target", "model", "split_family", "split_role"], as_index=False)[numeric_cols].mean(numeric_only=True)
    folds = subset.groupby(["target", "model", "split_family", "split_role"], as_index=False).agg(
        n_folds=("fold_id", "nunique"),
        n_test_rows_total=("n_test", "sum"),
    )
    return summary.merge(folds, on=["target", "model", "split_family", "split_role"], how="left")


def best_primary_model(metrics: pd.DataFrame, config: dict[str, Any]) -> str:
    """Select best primary-target model from forcing-day evidence."""
    primary = config["targets"]["primary"]
    subset = metrics.loc[
        (metrics["target"] == primary)
        & (metrics["model"] != "dummy_mean")
        & (metrics["split_family"] == "forcing_day_holdout")
    ].copy()
    if subset.empty:
        return ""
    by_model = subset.groupby("model", as_index=False).agg(
        forcing_day_MAE=("MAE", "mean"),
        forcing_day_spearman=("Spearman_observed_vs_predicted", "mean"),
        forcing_day_top10pct=("top10pct_overlap", "mean"),
        forcing_day_improvement=("MAE_improvement_fraction_over_dummy", "mean"),
    )
    by_model = by_model.sort_values(
        ["forcing_day_spearman", "forcing_day_top10pct", "forcing_day_improvement", "forcing_day_MAE", "model"],
        ascending=[False, False, False, True, True],
    )
    return str(by_model.iloc[0]["model"])


def target_sensitivity(metrics: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Summarize target sensitivity using forcing-day evidence first."""
    targets = [config["targets"]["primary"], *config["targets"]["sensitivity"]]
    rows: list[dict[str, Any]] = []
    for target in targets:
        subset = metrics.loc[
            (metrics["target"] == target)
            & (metrics["model"] != "dummy_mean")
            & (metrics["split_family"] == "forcing_day_holdout")
        ].copy()
        if subset.empty:
            rows.append(
                {
                    "target": target,
                    "available": False,
                    "best_model": "",
                    "forcing_day_MAE": np.nan,
                    "forcing_day_R2": np.nan,
                    "forcing_day_spearman": np.nan,
                    "forcing_day_top10pct_overlap": np.nan,
                    "robust_anchor_mean_rank_error": np.nan,
                    "target_predictability_rank": np.nan,
                    "target_card_verdict": "NOT_AVAILABLE",
                }
            )
            continue
        by_model = subset.groupby("model", as_index=False).agg(
            forcing_day_MAE=("MAE", "mean"),
            forcing_day_R2=("R2", "mean"),
            forcing_day_spearman=("Spearman_observed_vs_predicted", "mean"),
            forcing_day_top10pct_overlap=("top10pct_overlap", "mean"),
            robust_anchor_mean_rank_error=("robust_anchor_mean_rank_error", "mean"),
            forcing_day_improvement=("MAE_improvement_fraction_over_dummy", "mean"),
        )
        by_model = by_model.sort_values(
            ["forcing_day_spearman", "forcing_day_top10pct_overlap", "forcing_day_improvement", "forcing_day_MAE"],
            ascending=[False, False, False, True],
        )
        best = by_model.iloc[0].to_dict()
        if target == config["targets"]["primary"]:
            verdict = "PRIMARY_REMAINS_TARGET_CARD_VARIABLE"
        elif str(target).startswith("delta_tmrt_mean") or str(target).startswith("delta_tmrt_p50"):
            verdict = "COMPANION_TARGET_RECOMMENDED_FOR_MEAN_MEDIAN_SENSITIVITY"
        else:
            verdict = "SECONDARY_SENSITIVITY_NOT_PRIMARY_REPLACEMENT"
        best.update({"target": target, "available": True, "target_card_verdict": verdict})
        rows.append(best)
    out = pd.DataFrame(rows)
    if "forcing_day_spearman" in out.columns:
        valid = out["forcing_day_spearman"].rank(method="dense", ascending=False, na_option="bottom")
        out["target_predictability_rank"] = valid
    return out


def topk_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    """Extract top-k overlap metrics in long form."""
    if metrics.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for item in metrics.itertuples(index=False):
        for metric in ["top5_overlap", "top10pct_overlap", "top20pct_overlap"]:
            rows.append(
                {
                    "target": item.target,
                    "model": item.model,
                    "split_family": item.split_family,
                    "split_name": item.split_name,
                    "fold_id": item.fold_id,
                    "metric": metric,
                    "value": getattr(item, metric),
                    "split_role": item.split_role,
                }
            )
    return pd.DataFrame(rows)


def forcing_day_headline(metrics: pd.DataFrame, config: dict[str, Any]) -> str:
    """Return a concise primary forcing-day holdout headline."""
    model = best_primary_model(metrics, config)
    if not model:
        return "Forcing-day holdout unavailable."
    subset = metrics.loc[
        (metrics["target"] == config["targets"]["primary"])
        & (metrics["model"] == model)
        & (metrics["split_family"] == "forcing_day_holdout")
    ]
    return (
        f"{model}: MAE={subset['MAE'].mean():.4f}, R2={subset['R2'].mean():.3f}, "
        f"Spearman={subset['Spearman_observed_vs_predicted'].mean():.3f}, "
        f"top10pct={subset['top10pct_overlap'].mean():.3f}, "
        f"MAE improvement={subset['MAE_improvement_fraction_over_dummy'].mean():.1%}"
    )


def target_sensitivity_headline(sensitivity: pd.DataFrame, config: dict[str, Any]) -> str:
    """Return a concise target sensitivity headline."""
    if sensitivity.empty:
        return "Target sensitivity unavailable."
    valid = sensitivity.loc[sensitivity["available"].astype(bool)].copy()
    if valid.empty:
        return "Target sensitivity unavailable."
    best = valid.sort_values(["forcing_day_spearman", "forcing_day_top10pct_overlap"], ascending=[False, False]).iloc[0]
    primary = valid.loc[valid["target"] == config["targets"]["primary"]]
    primary_text = ""
    if not primary.empty:
        primary_text = f"; primary p90 Spearman={float(primary.iloc[0]['forcing_day_spearman']):.3f}"
    return f"Most predictable forcing-day target: {best['target']} with Spearman={float(best['forcing_day_spearman']):.3f}{primary_text}."


def run(config_path: Path = DEFAULT_CONFIG) -> ModelResult:
    """Run B8.6b surrogate benchmarks and write metric outputs."""
    config = read_config(config_path)
    try:
        dataset, schema, targets, splits = load_inputs(config)
    except FileNotFoundError:
        empty = pd.DataFrame()
        for key in [
            "model_metrics_by_split",
            "forcing_day_holdout_metrics",
            "cell_group_holdout_metrics",
            "hour_holdout_metrics",
            "spatial_holdout_metrics",
            "typology_holdout_metrics",
            "target_sensitivity_metrics",
            "topk_overlap_metrics",
        ]:
            empty.to_csv(repo_path(config["outputs"][key]), index=False)
        return ModelResult("B86B_BLOCKED_LABEL_INPUT", 0, "", "Inputs blocked.", "Inputs blocked.")

    metrics = run_model_metrics(dataset, schema, targets, splits, config)
    metrics.to_csv(repo_path(config["outputs"]["model_metrics_by_split"]), index=False)
    for family, key in [
        ("forcing_day_holdout", "forcing_day_holdout_metrics"),
        ("cell_group_holdout", "cell_group_holdout_metrics"),
        ("hour_holdout", "hour_holdout_metrics"),
        ("spatial_holdout", "spatial_holdout_metrics"),
        ("typology_holdout", "typology_holdout_metrics"),
    ]:
        summarize_split(metrics, family).to_csv(repo_path(config["outputs"][key]), index=False)
    sensitivity = target_sensitivity(metrics, config)
    sensitivity.to_csv(repo_path(config["outputs"]["target_sensitivity_metrics"]), index=False)
    topk_summary(metrics).to_csv(repo_path(config["outputs"]["topk_overlap_metrics"]), index=False)

    best_model = best_primary_model(metrics, config)
    return ModelResult(
        status="B86B_MODELS_READY" if not metrics.empty else "B86B_BLOCKED_FEATURE_INPUT",
        metrics_rows=int(len(metrics)),
        best_primary_model=best_model,
        forcing_day_headline=forcing_day_headline(metrics, config),
        target_sensitivity_headline=target_sensitivity_headline(sensitivity, config),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run B8.6b surrogate model benchmarks.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6b YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
