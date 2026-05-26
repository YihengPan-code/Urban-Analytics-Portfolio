"""Run B8.2 baseline surrogate/emulator model benchmarks for System B labels.

Inputs:
    configs/v12/systemb_surrogate_b8_model_benchmark.yaml
    outputs/v12_surrogate/b8_dataset_audit/surrogate_label_feature_matrix.csv
    outputs/v12_surrogate/b8_dataset_audit/feature_schema.csv
    outputs/v12_surrogate/b8_validation_protocol/split_manifest_*.csv

Outputs:
    outputs/v12_surrogate/b8_model_benchmark/surrogate_model_metrics.csv
    outputs/v12_surrogate/b8_model_benchmark/surrogate_predictions_oof.csv.gz
    outputs/v12_surrogate/b8_model_benchmark/topk_overlap_by_model.csv
    outputs/v12_surrogate/b8_model_benchmark/stratified_error_by_feature_bin.csv
    outputs/v12_surrogate/b8_model_benchmark/split_family_summary.csv
    outputs/v12_surrogate/b8_model_benchmark/model_family_comparison_report.md
    outputs/v12_surrogate/b8_model_benchmark/B8_2_BENCHMARK_STATUS.md

Saved metrics:
    Fold-level MAE/RMSE/R2/bias/median and p90 absolute error/Spearman/Pearson,
    featureless baseline MAE improvement, top-k overlap at 10% and 20%, cell
    aggregated top-k overlap, stratified test-fold error by physical feature
    bins, skipped split reasons, selected feature counts, and a compact status
    record.

This benchmark uses existing B8.1 split manifests only. It does not create a
random row split, AOI-wide prediction map, hazard_score, risk_score, local
WBGT, or System A/B coupling output. Targets are SOLWEIG-derived Tmrt labels;
the surrogate is not an observed WBGT calibration.
"""

from __future__ import annotations

import argparse
import itertools
import math
import subprocess
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import RegressorMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error, r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.exceptions import ConvergenceWarning

from v12_b8_prepare_surrogate_dataset import read_config, repo_path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_surrogate_b8_model_benchmark.yaml"
GROUP_SAFE_FAMILIES = {"cell_grouped_holdout", "spatial_holdout", "feature_bin_holdout"}
TRANSFER_FAMILIES = {"hour_holdout", "scenario_holdout"}
warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", message="Could not find the number of physical cores.*")


@dataclass(frozen=True)
class FeatureSelection:
    feature_set: str
    features: list[str]
    numeric_features: list[str]
    categorical_features: list[str]
    dropped_all_nan: list[str]
    dropped_constant: list[str]
    hard_blocked: list[str]


@dataclass(frozen=True)
class SplitFold:
    split_family: str
    split_name: str
    fold_id: str
    manifest: pd.DataFrame


@dataclass(frozen=True)
class BenchmarkResult:
    status: str
    metrics_path: Path
    predictions_path: Path
    topk_path: Path
    stratified_path: Path
    summary_path: Path
    report_path: Path
    status_path: Path
    feature_count: int
    models_completed: list[str]
    skipped_splits: list[dict[str, Any]]
    best_cell_grouped_model: str
    best_spatial_model: str
    spearman_topk_headline: str


def command_output(args: list[str]) -> str:
    """Run a lightweight command for status reporting."""
    completed = subprocess.run(args, cwd=ROOT, check=False, capture_output=True, text=True)
    return completed.stdout.strip()


def now_stamp() -> str:
    """Return a compact local timestamp string."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def coerce_list(value: Any) -> list[Any]:
    """Return a config scalar/list as a list."""
    if value is None:
        return [None]
    return value if isinstance(value, list) else [value]


def make_grid(values: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Build a small fixed parameter grid from config lists."""
    keys = list(values)
    return [dict(zip(keys, combo)) for combo in itertools.product(*(values[key] for key in keys))]


def hard_block_reason(name: str, config: dict[str, Any]) -> str | None:
    """Return the hard-block reason for a column name, if any."""
    lower = name.lower()
    contract = config["feature_contract"]
    for prefix in contract.get("hard_block_prefixes", []):
        if lower.startswith(str(prefix).lower()):
            return f"prefix:{prefix}"
    for suffix in contract.get("hard_block_suffixes", []):
        if lower.endswith(str(suffix).lower()):
            return f"suffix:{suffix}"
    for token in contract.get("hard_block_tokens", []):
        if str(token).lower() in lower:
            return f"token:{token}"
    return None


def select_headline_features(matrix: pd.DataFrame, schema: pd.DataFrame, config: dict[str, Any]) -> FeatureSelection:
    """Select the physical-core headline feature set from feature_schema.csv."""
    contract = config["feature_contract"]
    candidates = schema.loc[schema["role"].astype(str).str.lower() == str(contract["headline_role"]).lower()].copy()
    if "predictor_tier" in candidates.columns:
        tier = str(contract.get("headline_predictor_tier", "physical_core")).lower()
        candidates = candidates.loc[candidates["predictor_tier"].astype(str).str.lower() == tier].copy()
    hard_blocked = [
        name for name in candidates["column_name"].astype(str).tolist() if hard_block_reason(name, config) is not None
    ]
    candidates = candidates.loc[~candidates["column_name"].isin(hard_blocked)].copy()
    features = [name for name in candidates["column_name"].astype(str).tolist() if name in matrix.columns]
    dropped_all_nan: list[str] = []
    dropped_constant: list[str] = []
    retained: list[str] = []
    for name in features:
        series = matrix[name]
        if series.notna().sum() == 0:
            dropped_all_nan.append(name)
            continue
        if series.nunique(dropna=True) <= 1:
            dropped_constant.append(name)
            continue
        retained.append(name)

    max_cardinality = int(config.get("max_categorical_cardinality", 20))
    categorical: list[str] = []
    numeric: list[str] = []
    for name in retained:
        numeric_values = pd.to_numeric(matrix[name], errors="coerce")
        if numeric_values.notna().sum() >= matrix[name].notna().sum() and numeric_values.nunique(dropna=True) > 1:
            numeric.append(name)
            matrix[name] = numeric_values
            continue
        if matrix[name].nunique(dropna=True) <= max_cardinality:
            categorical.append(name)
        else:
            dropped_constant.append(name)
    retained = numeric + categorical
    if not retained:
        raise ValueError("No eligible physical-core features remained after feature-contract filtering.")
    return FeatureSelection(
        feature_set=str(config.get("feature_set", "physical_core")),
        features=retained,
        numeric_features=numeric,
        categorical_features=categorical,
        dropped_all_nan=dropped_all_nan,
        dropped_constant=dropped_constant,
        hard_blocked=hard_blocked,
    )


def make_preprocessor(selection: FeatureSelection, scaled: bool) -> ColumnTransformer:
    """Create the fold preprocessing pipeline."""
    transformers: list[tuple[str, Pipeline, list[str]]] = []
    numeric_steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if scaled:
        numeric_steps.append(("scaler", StandardScaler()))
    if selection.numeric_features:
        transformers.append(("num", Pipeline(numeric_steps), selection.numeric_features))
    if selection.categorical_features:
        categorical_pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
            ]
        )
        transformers.append(("cat", categorical_pipeline, selection.categorical_features))
    return ColumnTransformer(transformers=transformers, remainder="drop", sparse_threshold=0.0)


def model_specs(config: dict[str, Any]) -> dict[str, tuple[RegressorMixin, dict[str, list[Any]], bool]]:
    """Return model estimators, parameter grids, and scaling flags."""
    seed = int(config.get("random_seed", 42))
    models = config["models"]
    rf = models["random_forest"]
    et = models["extra_trees"]
    hgb = models["hist_gradient_boosting"]
    return {
        "ridge": (
            Ridge(solver="lsqr"),
            {"model__alpha": coerce_list(models["ridge"]["alpha"])},
            True,
        ),
        "elasticnet": (
            ElasticNet(max_iter=10000, random_state=seed),
            {
                "model__alpha": coerce_list(models["elasticnet"]["alpha"]),
                "model__l1_ratio": coerce_list(models["elasticnet"]["l1_ratio"]),
            },
            True,
        ),
        "random_forest": (
            RandomForestRegressor(
                n_estimators=int(rf["n_estimators"]),
                random_state=seed,
                n_jobs=int(rf.get("n_jobs", -1)),
            ),
            {
                "model__max_depth": coerce_list(rf["max_depth"]),
                "model__min_samples_leaf": coerce_list(rf["min_samples_leaf"]),
            },
            False,
        ),
        "extra_trees": (
            ExtraTreesRegressor(
                n_estimators=int(et["n_estimators"]),
                random_state=seed,
                n_jobs=int(et.get("n_jobs", -1)),
            ),
            {
                "model__max_depth": coerce_list(et["max_depth"]),
                "model__min_samples_leaf": coerce_list(et["min_samples_leaf"]),
            },
            False,
        ),
        "hist_gradient_boosting": (
            HistGradientBoostingRegressor(random_state=seed),
            {
                "model__max_iter": coerce_list(hgb["max_iter"]),
                "model__learning_rate": coerce_list(hgb["learning_rate"]),
                "model__max_leaf_nodes": coerce_list(hgb["max_leaf_nodes"]),
            },
            False,
        ),
    }


def load_split_folds(config: dict[str, Any], matrix: pd.DataFrame) -> tuple[list[SplitFold], list[dict[str, Any]]]:
    """Load existing split manifests and return valid train/test folds."""
    folds: list[SplitFold] = []
    skipped: list[dict[str, Any]] = []
    matrix_row_ids = set(matrix["row_id"].astype(str))
    validation = config["validation"]
    for family, manifest_path in config["inputs"]["manifests"].items():
        path = repo_path(manifest_path)
        manifest = pd.read_csv(path, dtype={"cell_id": "string", "row_id": "string", "fold_id": "string"})
        if family == "feature_bin_holdout":
            statuses = {str(value).upper() for value in validation.get("skip_feature_bin_statuses", [])}
            status_col = manifest.get("split_status", pd.Series("VALID", index=manifest.index)).astype(str).str.upper()
            min_train = int(validation["feature_bin_min_train_cells"])
            min_test = int(validation["feature_bin_min_test_cells"])
            invalid_mask = status_col.isin(statuses)
            invalid_mask |= manifest["row_id"].isna()
            invalid_mask |= pd.to_numeric(manifest.get("train_cell_count", min_train), errors="coerce").fillna(0) < min_train
            invalid_mask |= pd.to_numeric(manifest.get("test_cell_count", min_test), errors="coerce").fillna(0) < min_test
            for (split_name, fold_id), group in manifest.loc[invalid_mask].groupby(["split_name", "fold_id"], sort=True):
                skipped.append(
                    {
                        "split_family": family,
                        "split_name": split_name,
                        "fold": str(fold_id),
                        "reason": "blocked_or_below_min_cell_threshold",
                    }
                )
            manifest = manifest.loc[~invalid_mask].copy()
        missing = sorted(set(manifest["row_id"].astype(str)) - matrix_row_ids)
        if missing:
            raise ValueError(f"{family} manifest contains row_id values missing from matrix: {missing[:5]}")
        for (split_name, fold_id), group in manifest.groupby(["split_name", "fold_id"], sort=True):
            roles = set(group["role"].astype(str))
            if roles != {"train", "test"}:
                skipped.append(
                    {
                        "split_family": family,
                        "split_name": split_name,
                        "fold": str(fold_id),
                        "reason": "missing_train_or_test_role",
                    }
                )
                continue
            if group.duplicated(["row_id", "role"]).any():
                raise ValueError(f"Duplicate row_id-role in {family}/{split_name}/{fold_id}.")
            train_cells = set(group.loc[group["role"] == "train", "cell_id"].astype(str))
            test_cells = set(group.loc[group["role"] == "test", "cell_id"].astype(str))
            if family in GROUP_SAFE_FAMILIES and train_cells.intersection(test_cells):
                raise ValueError(f"Cell leakage detected in group-safe split {family}/{split_name}/{fold_id}.")
            folds.append(SplitFold(family, str(split_name), str(fold_id), group.copy()))
    return folds, skipped


def split_train_test(matrix: pd.DataFrame, fold: SplitFold, target: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Join one split fold to the label-feature matrix and return train/test rows."""
    joined = fold.manifest.merge(matrix, on="row_id", how="left", suffixes=("_split", ""), validate="many_to_one")
    if joined[target].isna().any():
        raise ValueError(f"Missing target values after joining {fold.split_family}/{fold.split_name}/{fold.fold_id}.")
    train = joined.loc[joined["role"] == "train"].copy()
    test = joined.loc[joined["role"] == "test"].copy()
    return train, test


def finite_correlation(left: pd.Series, right: pd.Series, method: str) -> float:
    """Compute a correlation only when it is numerically meaningful."""
    data = pd.DataFrame({"left": left, "right": right}).dropna()
    if len(data) < 2 or data["left"].nunique() <= 1 or data["right"].nunique() <= 1:
        return float("nan")
    if method == "spearman":
        x = data["left"].rank(method="average").to_numpy(dtype=float)
        y = data["right"].rank(method="average").to_numpy(dtype=float)
    else:
        x = data["left"].to_numpy(dtype=float)
        y = data["right"].to_numpy(dtype=float)
    x_centered = x - float(np.mean(x))
    y_centered = y - float(np.mean(y))
    denom = math.sqrt(float(np.sum(x_centered * x_centered)) * float(np.sum(y_centered * y_centered)))
    if denom == 0:
        return float("nan")
    return float(np.sum(x_centered * y_centered) / denom)


def metric_row(
    *,
    target: str,
    model_name: str,
    feature_set: str,
    fold: SplitFold,
    train: pd.DataFrame,
    test: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    best_params: dict[str, Any],
) -> dict[str, Any]:
    """Compute all required fold metrics."""
    residual = y_pred - y_true
    target_std = float(np.nanstd(y_true, ddof=1)) if len(y_true) > 1 else float("nan")
    r2 = float(r2_score(y_true, y_pred)) if len(y_true) > 1 and np.nanstd(y_true) > 0 else float("nan")
    return {
        "target": target,
        "model": model_name,
        "feature_set": feature_set,
        "split_family": fold.split_family,
        "split_name": fold.split_name,
        "fold": fold.fold_id,
        "n_train_rows": int(len(train)),
        "n_test_rows": int(len(test)),
        "n_train_cells": int(train["cell_id"].astype(str).nunique()),
        "n_test_cells": int(test["cell_id"].astype(str).nunique()),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": r2,
        "bias": float(np.nanmean(residual)),
        "median_abs_error": float(median_absolute_error(y_true, y_pred)),
        "p90_abs_error": float(np.nanpercentile(np.abs(residual), 90)),
        "spearman": finite_correlation(pd.Series(y_true), pd.Series(y_pred), "spearman"),
        "pearson": finite_correlation(pd.Series(y_true), pd.Series(y_pred), "pearson"),
        "target_std_test": target_std,
        "best_params": ";".join(f"{key}={value}" for key, value in sorted(best_params.items())),
    }


def fit_predict_model(
    *,
    model_name: str,
    estimator: RegressorMixin,
    param_grid: dict[str, list[Any]],
    scaled: bool,
    selection: FeatureSelection,
    train: pd.DataFrame,
    test: pd.DataFrame,
    target: str,
    config: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Fit one model with grouped inner CV and predict the outer test fold."""
    pipeline = Pipeline([("prep", make_preprocessor(selection, scaled=scaled)), ("model", estimator)])
    groups = train["cell_id"].astype(str)
    unique_groups = groups.nunique()
    cv_splits = min(int(config.get("inner_cv_splits", 3)), unique_groups)
    if cv_splits < 2:
        pipeline.set_params(**{key: values[0] for key, values in param_grid.items()})
        pipeline.fit(train[selection.features], train[target])
        return pipeline.predict(test[selection.features]), pipeline.get_params()
    search = GridSearchCV(
        pipeline,
        param_grid=param_grid,
        scoring="neg_mean_absolute_error",
        cv=GroupKFold(n_splits=cv_splits),
        n_jobs=int(config.get("grid_n_jobs", 1)),
        refit=True,
    )
    search.fit(train[selection.features], train[target], groups=groups)
    return search.predict(test[selection.features]), search.best_params_


def prediction_rows(
    test: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    *,
    target: str,
    model_name: str,
    feature_set: str,
    fold: SplitFold,
) -> pd.DataFrame:
    """Build row-level out-of-fold predictions for one target/model/fold."""
    columns = ["row_id", "cell_id", "scenario", "hour_sgt"]
    out = test[columns].copy()
    out.insert(0, "fold", fold.fold_id)
    out.insert(0, "split_name", fold.split_name)
    out.insert(0, "split_family", fold.split_family)
    out.insert(0, "feature_set", feature_set)
    out.insert(0, "model", model_name)
    out.insert(0, "target", target)
    out["y_true"] = y_true
    out["y_pred"] = y_pred
    out["error"] = out["y_pred"] - out["y_true"]
    out["abs_error"] = out["error"].abs()
    if "m_rad_pct01" in test.columns:
        out["m_rad_pct01"] = test["m_rad_pct01"].to_numpy()
    return out


def add_baseline_improvement(metrics: pd.DataFrame) -> pd.DataFrame:
    """Attach same-fold featureless MAE and improvement columns."""
    keys = ["target", "feature_set", "split_family", "split_name", "fold"]
    baseline = metrics.loc[metrics["model"] == "featureless_mean", keys + ["MAE"]].rename(columns={"MAE": "baseline_MAE_for_same_fold"})
    out = metrics.merge(baseline, on=keys, how="left")
    out["improvement_over_featureless_MAE"] = out["baseline_MAE_for_same_fold"] - out["MAE"]
    return out


def compute_topk(predictions: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Compute row-level and cell-aggregated top-k overlap diagnostics."""
    rows: list[dict[str, Any]] = []
    fractions = [float(value) for value in config["topk"]["fractions"]]
    min_n = int(config["topk"].get("min_n", 10))
    group_cols = ["target", "model", "feature_set", "split_family", "split_name", "fold"]
    for keys, group in predictions.groupby(group_cols, sort=True):
        for aggregation_level, frame, id_col in [
            ("row", group.copy(), "row_id"),
            (
                "cell",
                group.groupby("cell_id", as_index=False)[["y_true", "y_pred"]].mean(numeric_only=True),
                "cell_id",
            ),
        ]:
            n = len(frame)
            for frac in fractions:
                k = max(1, int(math.ceil(n * frac)))
                if n < min_n:
                    rows.append(
                        dict(
                            zip(group_cols, keys),
                            aggregation_level=aggregation_level,
                            k_fraction=frac,
                            k_count=k,
                            overlap_count=np.nan,
                            predicted_topk_count=np.nan,
                            true_topk_count=np.nan,
                            topk_overlap_fraction=np.nan,
                            status="insufficient_n",
                        )
                    )
                    continue
                true_top = set(frame.nlargest(k, "y_true")[id_col].astype(str))
                pred_top = set(frame.nlargest(k, "y_pred")[id_col].astype(str))
                overlap = len(true_top.intersection(pred_top))
                rows.append(
                    dict(
                        zip(group_cols, keys),
                        aggregation_level=aggregation_level,
                        k_fraction=frac,
                        k_count=k,
                        overlap_count=overlap,
                        predicted_topk_count=len(pred_top),
                        true_topk_count=len(true_top),
                        topk_overlap_fraction=overlap / len(true_top) if true_top else np.nan,
                        status="ok",
                    )
                )
    return pd.DataFrame(rows)


def selected_stratification_features(selection: FeatureSelection, config: dict[str, Any]) -> dict[str, str]:
    """Choose one non-leaky physical feature per requested stratification family."""
    available = set(selection.features)
    chosen: dict[str, str] = {}
    for family, candidates in config["stratification"]["families"].items():
        for candidate in candidates:
            if candidate in available:
                chosen[family] = candidate
                break
    return chosen


def bin_test_values(train: pd.DataFrame, test: pd.DataFrame, feature: str) -> pd.Series:
    """Create low/mid/high bins on test rows using train-fold tertiles."""
    train_values = pd.to_numeric(train[feature], errors="coerce")
    test_values = pd.to_numeric(test[feature], errors="coerce")
    q1 = train_values.quantile(1 / 3)
    q2 = train_values.quantile(2 / 3)
    if pd.isna(q1) or pd.isna(q2) or q1 == q2:
        return pd.Series("unbinned_degenerate", index=test.index)
    return pd.cut(test_values, bins=[-np.inf, q1, q2, np.inf], labels=["low", "mid", "high"], include_lowest=True).astype(str)


def compute_stratified_errors(
    predictions: pd.DataFrame,
    fold_cache: dict[tuple[str, str, str, str], tuple[pd.DataFrame, pd.DataFrame]],
    selection: FeatureSelection,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Summarize test-fold errors by physical feature bins."""
    chosen = selected_stratification_features(selection, config)
    rows: list[dict[str, Any]] = []
    group_cols = ["target", "model", "feature_set", "split_family", "split_name", "fold"]
    for keys, group in predictions.groupby(group_cols, sort=True):
        target, _model, _feature_set, split_family, split_name, fold_id = keys
        train, test = fold_cache[(str(target), str(split_family), str(split_name), str(fold_id))]
        test_features = test[["row_id", *chosen.values()]].copy()
        merged = group.merge(test_features, on="row_id", how="left")
        for family, feature in chosen.items():
            bins = bin_test_values(train, test, feature)
            bin_frame = pd.DataFrame({"row_id": test["row_id"].astype(str), "bin": bins.astype(str)})
            values = merged.merge(bin_frame, on="row_id", how="left")
            for bin_name, bin_group in values.groupby("bin", dropna=False, sort=True):
                if len(bin_group) == 0:
                    continue
                y_true = bin_group["y_true"].to_numpy()
                y_pred = bin_group["y_pred"].to_numpy()
                rows.append(
                    dict(
                        zip(group_cols, keys),
                        stratification_family=family,
                        stratification_feature=feature,
                        bin=str(bin_name),
                        bin_policy=config["stratification"].get("bin_policy", "train_fold_tertiles"),
                        n=int(len(bin_group)),
                        MAE=float(mean_absolute_error(y_true, y_pred)),
                        RMSE=float(math.sqrt(mean_squared_error(y_true, y_pred))),
                        bias=float(np.nanmean(y_pred - y_true)),
                    )
                )
    return pd.DataFrame(rows)


def summarize_by_split_family(metrics: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fold metrics by target/model/split family."""
    group_cols = ["target", "model", "feature_set", "split_family"]
    columns = ["MAE", "RMSE", "R2", "bias", "median_abs_error", "p90_abs_error", "spearman", "pearson", "improvement_over_featureless_MAE"]
    summary = metrics.groupby(group_cols, as_index=False)[columns].mean(numeric_only=True)
    counts = metrics.groupby(group_cols, as_index=False).agg(n_folds=("fold", "nunique"), n_test_rows=("n_test_rows", "sum"))
    return summary.merge(counts, on=group_cols, how="left")


def best_model(summary: pd.DataFrame, target: str, split_family: str) -> str:
    """Return the lowest-MAE non-featureless model for a target/split family."""
    subset = summary.loc[
        (summary["target"] == target)
        & (summary["split_family"] == split_family)
        & (summary["model"] != "featureless_mean")
    ].copy()
    if subset.empty:
        return "not_available"
    row = subset.sort_values(["MAE", "model"]).iloc[0]
    return f"{row['model']} (MAE={row['MAE']:.4f})"


def headline_spearman_topk(metrics: pd.DataFrame, topk: pd.DataFrame, target: str) -> str:
    """Create a compact top-k/Spearman headline for reports."""
    subset = metrics.loc[(metrics["target"] == target) & (metrics["split_family"].isin(["cell_grouped_holdout", "spatial_holdout"]))]
    if subset.empty:
        return "No cell-grouped/spatial Spearman results available."
    best = subset.loc[subset["model"] != "featureless_mean"].groupby("model")["spearman"].mean(numeric_only=True).sort_values(ascending=False)
    best_model_name = str(best.index[0]) if not best.empty else "not_available"
    topk_subset = topk.loc[
        (topk["target"] == target)
        & (topk["model"] == best_model_name)
        & (topk["split_family"].isin(["cell_grouped_holdout", "spatial_holdout"]))
        & (topk["aggregation_level"] == "cell")
        & (topk["k_fraction"] == 0.1)
    ]
    topk_value = topk_subset["topk_overlap_fraction"].mean(numeric_only=True)
    spearman_value = best.iloc[0] if not best.empty else np.nan
    return f"{best_model_name}: mean cell/spatial Spearman={spearman_value:.3f}; mean cell-level top-10% overlap={topk_value:.3f}"


def write_report(
    *,
    config: dict[str, Any],
    selection: FeatureSelection,
    metrics: pd.DataFrame,
    topk: pd.DataFrame,
    stratified: pd.DataFrame,
    summary: pd.DataFrame,
    skipped_splits: list[dict[str, Any]],
    models_completed: list[str],
    report_path: Path,
) -> None:
    """Write the Markdown model-family comparison report."""
    primary = config["targets"]["primary"]
    secondary = config["targets"]["secondary"]
    cell_best = best_model(summary, primary, "cell_grouped_holdout")
    spatial_best = best_model(summary, primary, "spatial_holdout")
    primary_summary = summary.loc[summary["target"] == primary].sort_values(["split_family", "MAE"])
    secondary_summary = summary.loc[summary["target"] == secondary].sort_values(["split_family", "MAE"])
    promote = "No. Results are baseline evidence for B8.3 model-card review only; no final AOI-wide surrogate is promoted here."
    lines = [
        "# B8.2 System B Baseline Surrogate Benchmark",
        "",
        f"Generated: {now_stamp()}",
        "",
        "## 1. Input Files And Feature Contract",
        "",
        f"- Matrix: `{config['inputs']['matrix']}`",
        f"- Feature schema: `{config['inputs']['feature_schema']}`",
        "- Split manifests: existing B8.1 cell-grouped, spatial, feature-bin, hour, and scenario holdouts.",
        f"- Headline feature set: `role == feature` and `predictor_tier == {selection.feature_set}`.",
        f"- Feature count used: {len(selection.features)} ({len(selection.numeric_features)} numeric, {len(selection.categorical_features)} categorical).",
        f"- Dropped all-NaN features: {len(selection.dropped_all_nan)}.",
        f"- Dropped constant/non-usable features: {len(selection.dropped_constant)}.",
        f"- Hard-blocked by name contract: {len(selection.hard_blocked)}.",
        "",
        "## 2. Target Definitions And Claim Boundary",
        "",
        f"- Primary target: `{primary}`.",
        f"- Secondary target: `{secondary}`.",
        "- Retained label: `m_rad_pct01` for post-prediction rank interpretation only.",
        "- Labels are SOLWEIG-derived Tmrt targets. This is not observed WBGT calibration, not local WBGT prediction, and not a risk map.",
        "",
        "## 3. Models Benchmarked",
        "",
        *[f"- `{model}`" for model in models_completed],
        "",
        "Tree ensembles used a reduced fixed grid (`n_estimators=80`, two depth settings, one leaf setting, single-thread fits) to keep the full multi-split benchmark reasonable on the B8.2 lane.",
        "",
        "## 4. Validation Split Families Consumed",
        "",
        *[f"- `{family}`" for family in sorted(metrics["split_family"].unique())],
        "",
        "Group-safe split families assert no cell_id overlap between train and test. Hour and scenario holdouts may reuse cells by design.",
        "",
        "## 5. Splits Skipped",
        "",
    ]
    if skipped_splits:
        lines.extend([f"- `{item['split_family']}` / `{item['split_name']}` fold `{item['fold']}`: {item['reason']}" for item in skipped_splits])
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## 6. Primary Target Results",
            "",
            f"- Best non-featureless cell-grouped model by MAE: {cell_best}.",
            f"- Best non-featureless spatial model by MAE: {spatial_best}.",
            "",
            primary_summary[["split_family", "model", "n_folds", "MAE", "RMSE", "R2", "spearman", "improvement_over_featureless_MAE"]].to_markdown(index=False),
            "",
            "## 7. Secondary Target Results",
            "",
            secondary_summary[["split_family", "model", "n_folds", "MAE", "RMSE", "R2", "spearman", "improvement_over_featureless_MAE"]].to_markdown(index=False),
            "",
            "## 8. Top-k / Spearman Interpretation",
            "",
            f"- {headline_spearman_topk(metrics, topk, primary)}.",
            "- Top-k overlap is diagnostic for prioritisation ranking, not evidence of risk prediction.",
            "",
            "## 9. Stratified Error Summary",
            "",
        ]
    )
    if stratified.empty:
        lines.append("- No stratification features were available.")
    else:
        strat_summary = (
            stratified.groupby(["target", "stratification_family", "model"], as_index=False)["MAE"]
            .mean(numeric_only=True)
            .sort_values(["target", "stratification_family", "MAE"])
        )
        lines.append(strat_summary.to_markdown(index=False))
    lines.extend(
        [
            "",
            "## 10. B8.3 Model-card Promotion Readiness",
            "",
            f"- {promote}",
            "",
            "## 11. Caveats",
            "",
            "- N150 only.",
            "- Single forcing setup.",
            "- SOLWEIG-derived labels only.",
            "- No local WBGT.",
            "- No risk map.",
            "- No causal feature importance.",
            "- No final AOI-wide prediction map was created.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_status(
    *,
    config: dict[str, Any],
    result_status: str,
    selection: FeatureSelection,
    models_completed: list[str],
    split_families: list[str],
    skipped_splits: list[dict[str, Any]],
    summary: pd.DataFrame,
    topk_headline: str,
    commands: list[str],
    status_path: Path,
) -> None:
    """Write B8_2_BENCHMARK_STATUS.md."""
    primary = config["targets"]["primary"]
    branch = command_output(["git", "branch", "--show-current"])
    cell_best = best_model(summary, primary, "cell_grouped_holdout")
    spatial_best = best_model(summary, primary, "spatial_holdout")
    files = [
        "configs/v12/systemb_surrogate_b8_model_benchmark.yaml",
        "scripts/v12_b8_surrogate_model_benchmark.py",
        "scripts/v12_b8_run_model_benchmark.py",
        "docs/v12/OpenHeat_SystemB_surrogate_baseline_benchmark_CN.md",
        "outputs/v12_surrogate/b8_model_benchmark/surrogate_model_metrics.csv",
        "outputs/v12_surrogate/b8_model_benchmark/surrogate_predictions_oof.csv.gz",
        "outputs/v12_surrogate/b8_model_benchmark/topk_overlap_by_model.csv",
        "outputs/v12_surrogate/b8_model_benchmark/stratified_error_by_feature_bin.csv",
        "outputs/v12_surrogate/b8_model_benchmark/split_family_summary.csv",
        "outputs/v12_surrogate/b8_model_benchmark/model_family_comparison_report.md",
        "outputs/v12_surrogate/b8_model_benchmark/B8_2_BENCHMARK_STATUS.md",
    ]
    lines = [
        "# B8.2 Benchmark Status",
        "",
        f"Status: {result_status}",
        f"Branch: {branch}",
        "Scope: Lane B8.2 baseline surrogate/emulator benchmark for SOLWEIG-derived System B targets only.",
        "",
        "## Commands run",
        "",
        *[f"- `{command}`" for command in commands],
        "",
        "## Files created / modified",
        "",
        *[f"- `{path}`" for path in files],
        "",
        "## Feature set used",
        "",
        f"- Feature set: `{selection.feature_set}`.",
        f"- Feature count: {len(selection.features)}.",
        f"- Numeric features: {len(selection.numeric_features)}.",
        f"- Categorical features: {len(selection.categorical_features)}.",
        f"- Dropped all-NaN features: {len(selection.dropped_all_nan)}.",
        f"- Dropped constant/non-usable features: {len(selection.dropped_constant)}.",
        f"- Hard-blocked candidate features: {len(selection.hard_blocked)}.",
        "",
        "## Models run",
        "",
        *[f"- `{model}`" for model in models_completed],
        "",
        "## Split families run",
        "",
        *[f"- `{family}`" for family in split_families],
        "",
        "## Key results",
        "",
        f"- Best cell-grouped model for `{primary}` by MAE: {cell_best}.",
        f"- Best spatial model for `{primary}` by MAE: {spatial_best}.",
        f"- Spearman / top-k headline: {topk_headline}.",
        f"- Skipped split count: {len(skipped_splits)}.",
        "",
        "## Caveats",
        "",
        "- N150 only.",
        "- Single forcing setup.",
        "- SOLWEIG-derived labels only.",
        "- No local WBGT.",
        "- No risk map.",
        "- No causal feature importance.",
        "- No final AOI-wide prediction map.",
        "- Tree grids were reduced for runtime and documented in the benchmark report.",
        "",
        "## Safe to commit",
        "",
        "- Compact B8.2 config, scripts, docs, and outputs under `outputs/v12_surrogate/b8_model_benchmark/` after review.",
        "",
        "## Not safe to commit",
        "",
        "- `data/solweig/`, `data/rasters/`, raw archive files, `.tif`, `.tiff`, `svfs.zip`, patch zip packages, large hourly forecast CSVs, AOI-wide prediction maps, local WBGT, hazard_score, risk_score, or System A/B coupling outputs.",
        "",
        "## Next recommended action",
        "",
        "- Review B8.2 metrics/report and decide whether a clearly caveated B8.3 model-card review is warranted, without promoting any model to final AOI-wide inference.",
    ]
    status_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path, commands: list[str] | None = None) -> BenchmarkResult:
    """Run the full B8.2 benchmark workflow."""
    commands = commands or []
    config = read_config(config_path)
    out_dir = repo_path(config["outputs"]["benchmark_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix = pd.read_csv(repo_path(config["inputs"]["matrix"]), dtype={"cell_id": "string", "row_id": "string"})
    schema = pd.read_csv(repo_path(config["inputs"]["feature_schema"]))
    selection = select_headline_features(matrix, schema, config)
    folds, skipped_splits = load_split_folds(config, matrix)
    targets = [config["targets"]["primary"], config["targets"]["secondary"]]
    specs = model_specs(config)
    metrics_rows: list[dict[str, Any]] = []
    prediction_frames: list[pd.DataFrame] = []
    fold_cache: dict[tuple[str, str, str, str], tuple[pd.DataFrame, pd.DataFrame]] = {}
    models_completed = ["featureless_mean", *specs.keys()]

    for target in targets:
        for fold in folds:
            print(f"[B8.2] target={target} split={fold.split_family}/{fold.split_name}/fold{fold.fold_id}", flush=True)
            train, test = split_train_test(matrix, fold, target)
            fold_cache[(target, fold.split_family, fold.split_name, fold.fold_id)] = (train.copy(), test.copy())
            y_true = test[target].to_numpy(dtype=float)
            baseline_pred = np.repeat(float(train[target].mean()), len(test))
            metrics_rows.append(
                metric_row(
                    target=target,
                    model_name="featureless_mean",
                    feature_set=selection.feature_set,
                    fold=fold,
                    train=train,
                    test=test,
                    y_true=y_true,
                    y_pred=baseline_pred,
                    best_params={"strategy": "train_mean"},
                )
            )
            prediction_frames.append(
                prediction_rows(
                    test,
                    y_true,
                    baseline_pred,
                    target=target,
                    model_name="featureless_mean",
                    feature_set=selection.feature_set,
                    fold=fold,
                )
            )
            for model_name, (estimator, param_grid, scaled) in specs.items():
                y_pred, best_params = fit_predict_model(
                    model_name=model_name,
                    estimator=estimator,
                    param_grid=param_grid,
                    scaled=scaled,
                    selection=selection,
                    train=train,
                    test=test,
                    target=target,
                    config=config,
                )
                metrics_rows.append(
                    metric_row(
                        target=target,
                        model_name=model_name,
                        feature_set=selection.feature_set,
                        fold=fold,
                        train=train,
                        test=test,
                        y_true=y_true,
                        y_pred=y_pred,
                        best_params=best_params,
                    )
                )
                prediction_frames.append(
                    prediction_rows(
                        test,
                        y_true,
                        y_pred,
                        target=target,
                        model_name=model_name,
                        feature_set=selection.feature_set,
                        fold=fold,
                    )
                )

    metrics = add_baseline_improvement(pd.DataFrame(metrics_rows))
    predictions = pd.concat(prediction_frames, ignore_index=True)
    topk = compute_topk(predictions, config)
    stratified = compute_stratified_errors(predictions, fold_cache, selection, config)
    summary = summarize_by_split_family(metrics)

    metrics_path = repo_path(config["outputs"]["metrics"])
    predictions_path = repo_path(config["outputs"]["predictions"])
    topk_path = repo_path(config["outputs"]["topk_overlap"])
    stratified_path = repo_path(config["outputs"]["stratified_error"])
    summary_path = repo_path(config["outputs"]["split_family_summary"])
    report_path = repo_path(config["outputs"]["report"])
    status_path = repo_path(config["outputs"]["status"])
    metrics.to_csv(metrics_path, index=False)
    predictions.to_csv(predictions_path, index=False, compression="gzip")
    topk.to_csv(topk_path, index=False)
    stratified.to_csv(stratified_path, index=False)
    summary.to_csv(summary_path, index=False)
    write_report(
        config=config,
        selection=selection,
        metrics=metrics,
        topk=topk,
        stratified=stratified,
        summary=summary,
        skipped_splits=skipped_splits,
        models_completed=models_completed,
        report_path=report_path,
    )
    topk_headline = headline_spearman_topk(metrics, topk, config["targets"]["primary"])
    split_families = sorted(metrics["split_family"].unique().tolist())
    status = "PASS"
    required_models = {"featureless_mean", "ridge", "elasticnet", "random_forest", "extra_trees", "hist_gradient_boosting"}
    if not required_models.issubset(set(models_completed)):
        status = "FAILED"
    if not {"cell_grouped_holdout", "spatial_holdout"}.issubset(set(split_families)):
        status = "FAILED"
    write_status(
        config=config,
        result_status=status,
        selection=selection,
        models_completed=models_completed,
        split_families=split_families,
        skipped_splits=skipped_splits,
        summary=summary,
        topk_headline=topk_headline,
        commands=commands,
        status_path=status_path,
    )
    return BenchmarkResult(
        status=status,
        metrics_path=metrics_path,
        predictions_path=predictions_path,
        topk_path=topk_path,
        stratified_path=stratified_path,
        summary_path=summary_path,
        report_path=report_path,
        status_path=status_path,
        feature_count=len(selection.features),
        models_completed=models_completed,
        skipped_splits=skipped_splits,
        best_cell_grouped_model=best_model(summary, config["targets"]["primary"], "cell_grouped_holdout"),
        best_spatial_model=best_model(summary, config["targets"]["primary"], "spatial_holdout"),
        spearman_topk_headline=topk_headline,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Run B8.2 System B baseline surrogate benchmarks over existing B8.1 "
            "split manifests. Outputs fold metrics, OOF predictions, top-k overlap, "
            "stratified errors, a comparison report, and a status file."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Benchmark YAML config path.")
    args = parser.parse_args()
    result = run(repo_path(args.config), commands=[f"python scripts/v12_b8_run_model_benchmark.py --config {args.config.as_posix()}"])
    print(f"Status: {result.status}")
    print(f"Feature count: {result.feature_count}")
    print(f"Models completed: {', '.join(result.models_completed)}")
    print(f"Best cell_grouped delta_tmrt_p90_c: {result.best_cell_grouped_model}")
    print(f"Best spatial delta_tmrt_p90_c: {result.best_spatial_model}")
    print(f"Spearman/top-k headline: {result.spearman_topk_headline}")
    print(f"Report: {result.report_path}")
    print(f"Status file: {result.status_path}")


if __name__ == "__main__":
    main()
