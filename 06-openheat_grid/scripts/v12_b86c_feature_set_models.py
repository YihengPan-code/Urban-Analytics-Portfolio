"""Run B8.6c compact surrogate audits across feature sets and holdouts.

Inputs:
    configs/v12/systemb_b86c_feature_hardening.yaml
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_hardened_surrogate_dataset.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_feature_set_registry.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_model_metrics_by_split.csv

Outputs:
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_feature_set_model_metrics.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_oof_prediction_audit.csv

Saved metrics:
    For each configured feature set, target, model, split, and fold: n_train,
    n_test, MAE, RMSE, R2, Spearman, Pearson, sign accuracy, top5/top10pct/
    top20pct overlap, neutral-boundary accuracy, robust-anchor MAE/rank error,
    unstable-review MAE/rank error, h10 metrics, and improvement over the
    comparable B8.6b baseline where available.

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
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from sklearn.ensemble import HistGradientBoostingRegressor
except Exception:  # pragma: no cover - depends on local sklearn version.
    HistGradientBoostingRegressor = None  # type: ignore[assignment]

from v12_b86c_feature_inventory import DEFAULT_CONFIG, read_config, repo_path


warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", message="Could not find the number of physical cores.*")


@dataclass(frozen=True)
class ModelAuditResult:
    """Compact return record for the B8.6c feature-set model audit."""

    status: str
    metric_rows: int
    oof_rows: int
    feature_sets_evaluated: int
    targets_evaluated: int
    best_feature_set: str
    best_model: str
    best_supporting_headline: str


def parse_pipe_list(value: Any) -> list[str]:
    """Parse a pipe-separated registry value."""
    if pd.isna(value):
        return []
    return [item for item in str(value).split("|") if item]


def bool_value(value: Any) -> bool:
    """Parse bool-like CSV values."""
    return str(value).strip().lower() in {"true", "1", "yes"}


def load_inputs(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the hardened dataset and feature-set registry."""
    dataset = pd.read_csv(
        repo_path(config["outputs"]["hardened_surrogate_dataset"]),
        dtype={"cell_id": "string", "row_id": "string", "forcing_day_id": "string"},
    )
    registry = pd.read_csv(repo_path(config["outputs"]["feature_set_registry"]))
    return dataset, registry


def targets(config: dict[str, Any]) -> list[str]:
    """Return primary and companion target names."""
    return [config["targets"]["primary"], *config["targets"]["companion"]]


def configured_models(config: dict[str, Any]) -> dict[str, Any]:
    """Create documented sklearn model instances for B8.6c."""
    seed = int(config["random_seed"])
    out: dict[str, Any] = {}
    include = set(config["models"]["include"])
    if "dummy_mean" in include:
        out["dummy_mean"] = DummyRegressor(strategy="mean")
    if "ridge" in include:
        out["ridge"] = Ridge(alpha=float(config["models"]["ridge"]["alpha"]))
    if "elasticnet" in include:
        out["elasticnet"] = ElasticNet(
            alpha=float(config["models"]["elasticnet"]["alpha"]),
            l1_ratio=float(config["models"]["elasticnet"]["l1_ratio"]),
            max_iter=10000,
            random_state=seed,
        )
    if "random_forest_regressor" in include:
        cfg = config["models"]["random_forest_regressor"]
        out["random_forest_regressor"] = RandomForestRegressor(
            n_estimators=int(cfg["n_estimators"]),
            max_depth=int(cfg["max_depth"]),
            min_samples_leaf=int(cfg["min_samples_leaf"]),
            random_state=seed,
            n_jobs=1,
        )
    if "hist_gradient_boosting_regressor" in include and HistGradientBoostingRegressor is not None:
        cfg = config["models"]["hist_gradient_boosting_regressor"]
        out["hist_gradient_boosting_regressor"] = HistGradientBoostingRegressor(
            max_iter=int(cfg["max_iter"]),
            learning_rate=float(cfg["learning_rate"]),
            max_leaf_nodes=int(cfg["max_leaf_nodes"]),
            random_state=seed,
        )
    return out


def one_hot_encoder() -> OneHotEncoder:
    """Create a version-compatible one-hot encoder."""
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:  # pragma: no cover - older sklearn.
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def coerce_feature_frame(dataset: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Coerce numeric features and split features into numeric/categorical sets."""
    out = dataset.copy()
    numeric: list[str] = []
    categorical: list[str] = []
    for feature in features:
        if feature not in out.columns:
            continue
        series = out[feature]
        if series.dtype == bool:
            out[feature] = series.astype(int)
            numeric.append(feature)
            continue
        numeric_series = pd.to_numeric(series, errors="coerce")
        numeric_share = float(numeric_series.notna().mean()) if len(series) else 0.0
        if numeric_share >= 0.95:
            if numeric_series.nunique(dropna=True) > 1:
                out[feature] = numeric_series
                numeric.append(feature)
        else:
            if series.astype(str).nunique(dropna=True) > 1:
                out[feature] = series.astype("string").fillna("__missing__")
                categorical.append(feature)
    return out, numeric, categorical


def make_pipeline(model_name: str, estimator: Any, numeric: list[str], categorical: list[str]) -> Pipeline:
    """Create a preprocessing and regression pipeline."""
    transformers: list[tuple[str, Any, list[str]]] = []
    if numeric:
        numeric_steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
        if model_name in {"ridge", "elasticnet"}:
            numeric_steps.append(("scaler", StandardScaler()))
        transformers.append(("num", Pipeline(numeric_steps), numeric))
    if categorical:
        categorical_steps = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", one_hot_encoder()),
            ]
        )
        transformers.append(("cat", categorical_steps, categorical))
    preprocessor = ColumnTransformer(transformers=transformers, remainder="drop", sparse_threshold=0.0)
    return Pipeline([("prep", preprocessor), ("model", clone(estimator))])


def split_rows(
    dataset: pd.DataFrame,
    test_mask: pd.Series,
    split_family: str,
    split_name: str,
    fold_id: str,
) -> tuple[str, str, str, pd.Index, pd.Index]:
    """Return train/test indexes for one split."""
    return split_family, split_name, fold_id, dataset.index[~test_mask], dataset.index[test_mask]


def validation_folds(dataset: pd.DataFrame, config: dict[str, Any]) -> list[tuple[str, str, str, pd.Index, pd.Index]]:
    """Create deterministic B8.6c validation folds."""
    folds: list[tuple[str, str, str, pd.Index, pd.Index]] = []
    for idx, forcing_day in enumerate(sorted(dataset["forcing_day_id"].astype(str).unique()), start=1):
        mask = dataset["forcing_day_id"].astype(str) == forcing_day
        folds.append(split_rows(dataset, mask, "forcing_day_holdout", f"holdout_{forcing_day}", str(idx)))

    cells = np.array(sorted(dataset["cell_id"].astype(str).unique()))
    rng = np.random.default_rng(int(config["random_seed"]))
    rng.shuffle(cells)
    for idx, test_cells in enumerate(np.array_split(cells, int(config["validation"]["cell_group_folds"])), start=1):
        mask = dataset["cell_id"].astype(str).isin(set(test_cells.tolist()))
        folds.append(split_rows(dataset, mask, "cell_group_holdout", "cell_group_5fold", str(idx)))

    cell_frame = dataset.drop_duplicates("cell_id")[["cell_id", "centroid_x", "centroid_y"]].copy()
    cell_frame["centroid_x"] = pd.to_numeric(cell_frame["centroid_x"], errors="coerce")
    cell_frame["centroid_y"] = pd.to_numeric(cell_frame["centroid_y"], errors="coerce")
    x_mid = float(cell_frame["centroid_x"].median())
    y_mid = float(cell_frame["centroid_y"].median())
    cell_frame["spatial_block"] = np.where(cell_frame["centroid_x"] <= x_mid, "west", "east") + "_" + np.where(
        cell_frame["centroid_y"] <= y_mid,
        "south",
        "north",
    )
    for idx, block in enumerate(sorted(cell_frame["spatial_block"].unique()), start=1):
        test_cells = set(cell_frame.loc[cell_frame["spatial_block"] == block, "cell_id"].astype(str))
        mask = dataset["cell_id"].astype(str).isin(test_cells)
        folds.append(split_rows(dataset, mask, "spatial_holdout", f"spatial_{block}", str(idx)))

    min_test = int(config["validation"]["typology_min_test_cells"])
    min_train = int(config["validation"]["typology_min_train_cells"])
    typology_cells = dataset.drop_duplicates("cell_id")[["cell_id", "typology_label"]].dropna()
    fold_id = 1
    for typology in sorted(typology_cells["typology_label"].astype(str).unique()):
        test_cells = set(typology_cells.loc[typology_cells["typology_label"].astype(str) == typology, "cell_id"].astype(str))
        mask = dataset["cell_id"].astype(str).isin(test_cells)
        if len(test_cells) >= min_test and int(dataset.loc[~mask, "cell_id"].nunique()) >= min_train:
            folds.append(split_rows(dataset, mask, "typology_holdout", f"typology_{typology}", str(fold_id)))
        fold_id += 1

    for idx, hour in enumerate(sorted(pd.to_numeric(dataset["hour_sgt"], errors="coerce").dropna().astype(int).unique()), start=1):
        mask = pd.to_numeric(dataset["hour_sgt"], errors="coerce") == hour
        folds.append(split_rows(dataset, mask, "hour_holdout", f"leave_h{hour}_out", str(idx)))
    return folds


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
    return float(np.sum(left * right) / denom) if denom else float("nan")


def cell_average_frame(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:
    """Build per-cell observed/predicted averages for ranking diagnostics."""
    frame = test[["cell_id"]].copy()
    frame["y_true"] = y_true
    frame["y_pred"] = y_pred
    return frame.groupby("cell_id", as_index=False)[["y_true", "y_pred"]].mean(numeric_only=True)


def top_overlap(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, k: int) -> float:
    """Compute low-delta top-k overlap by cell."""
    by_cell = cell_average_frame(test, y_true, y_pred)
    if by_cell.empty:
        return float("nan")
    k = min(max(1, k), len(by_cell))
    true_top = set(by_cell.nsmallest(k, "y_true")["cell_id"].astype(str))
    pred_top = set(by_cell.nsmallest(k, "y_pred")["cell_id"].astype(str))
    return float(len(true_top & pred_top) / k)


def top_fraction_overlap(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, fraction: float) -> float:
    """Compute low-delta top-fraction overlap by cell."""
    return top_overlap(test, y_true, y_pred, max(1, int(math.ceil(fraction * int(test["cell_id"].nunique())))))


def role_error_and_rank(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, mask_column: str) -> tuple[float, float]:
    """Compute MAE and rank error for a diagnostic cell role."""
    if mask_column not in test.columns:
        return float("nan"), float("nan")
    by_cell = cell_average_frame(test, y_true, y_pred)
    if by_cell.empty:
        return float("nan"), float("nan")
    role_cells = set(test.loc[test[mask_column].astype(bool), "cell_id"].astype(str))
    by_cell["true_rank"] = by_cell["y_true"].rank(method="min", ascending=True)
    by_cell["pred_rank"] = by_cell["y_pred"].rank(method="min", ascending=True)
    subset = by_cell.loc[by_cell["cell_id"].astype(str).isin(role_cells)].copy()
    if subset.empty:
        return float("nan"), float("nan")
    mae = float((subset["y_pred"] - subset["y_true"]).abs().mean())
    rank_error = float((subset["pred_rank"] - subset["true_rank"]).abs().mean())
    return mae, rank_error


def neutral_accuracy(y_true: np.ndarray, y_pred: np.ndarray, threshold: float) -> float:
    """Compute neutral-boundary accuracy."""
    return float(np.mean((np.abs(y_true) <= threshold) == (np.abs(y_pred) <= threshold))) if len(y_true) else float("nan")


def h10_metrics(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, config: dict[str, Any]) -> dict[str, float]:
    """Compute h10 caveat metrics for a fold."""
    mask = pd.to_numeric(test["hour_sgt"], errors="coerce") == int(config["diagnostic_cells"]["h10_caveat_hour"])
    if not bool(mask.any()):
        return {"h10_MAE": float("nan"), "h10_Spearman": float("nan"), "h10_top10pct_overlap": float("nan")}
    y_t = y_true[mask.to_numpy()]
    y_p = y_pred[mask.to_numpy()]
    part = test.loc[mask].copy()
    return {
        "h10_MAE": float(mean_absolute_error(y_t, y_p)),
        "h10_Spearman": finite_corr(y_t, y_p, "spearman"),
        "h10_top10pct_overlap": top_fraction_overlap(part, y_t, y_p, 0.10),
    }


def baseline_lookup(config: dict[str, Any]) -> dict[tuple[str, str, str], float]:
    """Load comparable B8.6b baseline MAE values by target/split/model."""
    path = repo_path(config["inputs"]["b86b_context"]["model_metrics_by_split"])
    if not path.exists():
        return {}
    frame = pd.read_csv(path)
    if frame.empty:
        return {}
    grouped = frame.groupby(["target", "split_family", "model"], as_index=False)["MAE"].mean()
    lookup: dict[tuple[str, str, str], float] = {}
    for item in grouped.itertuples(index=False):
        lookup[(str(item.target), str(item.split_family), str(item.model))] = float(item.MAE)
    by_best = frame.loc[frame["model"] != "dummy_mean"].groupby(["target", "split_family", "model"], as_index=False).agg(
        MAE=("MAE", "mean"),
        Spearman_observed_vs_predicted=("Spearman_observed_vs_predicted", "mean"),
        top10pct_overlap=("top10pct_overlap", "mean"),
    )
    for (target, split_family), part in by_best.groupby(["target", "split_family"], sort=True):
        best = part.sort_values(
            ["Spearman_observed_vs_predicted", "top10pct_overlap", "MAE"],
            ascending=[False, False, True],
        ).iloc[0]
        lookup[(str(target), str(split_family), "__best__")] = float(best["MAE"])
    return lookup


def metric_row(
    feature_set: str,
    feature_count: int,
    primary_evidence_allowed: bool,
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
    b86b_lookup: dict[tuple[str, str, str], float],
) -> dict[str, Any]:
    """Compute one B8.6c metric row."""
    residual = y_pred - y_true
    anchor_mae, anchor_rank = role_error_and_rank(test, y_true, y_pred, "robust_anchor_flag")
    unstable_mae, unstable_rank = role_error_and_rank(test, y_true, y_pred, "unstable_review_flag")
    same_model_mae = b86b_lookup.get((target, split_family, model_name), np.nan)
    best_b86b_mae = b86b_lookup.get((target, split_family, "__best__"), np.nan)
    row: dict[str, Any] = {
        "feature_set": feature_set,
        "feature_count": feature_count,
        "primary_evidence_allowed": primary_evidence_allowed,
        "target": target,
        "model": model_name,
        "split_family": split_family,
        "split_name": split_name,
        "fold_id": fold_id,
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
        "sign_accuracy": float(np.mean(np.sign(y_true) == np.sign(y_pred))),
        "top5_overlap": top_overlap(test, y_true, y_pred, 5),
        "top10pct_overlap": top_fraction_overlap(test, y_true, y_pred, 0.10),
        "top20pct_overlap": top_fraction_overlap(test, y_true, y_pred, 0.20),
        "neutral_boundary_classification_accuracy": neutral_accuracy(
            y_true,
            y_pred,
            float(config["targets"]["neutral_delta_abs_threshold_c"]),
        ),
        "robust_anchor_MAE": anchor_mae,
        "robust_anchor_mean_rank_error": anchor_rank,
        "unstable_review_MAE": unstable_mae,
        "unstable_review_mean_rank_error": unstable_rank,
        "b86b_same_model_MAE": same_model_mae,
        "b86b_best_MAE": best_b86b_mae,
        "MAE_improvement_fraction_over_b86b_same_model": (
            float((same_model_mae - mean_absolute_error(y_true, y_pred)) / same_model_mae)
            if not math.isnan(same_model_mae) and same_model_mae > 0
            else np.nan
        ),
        "MAE_improvement_fraction_over_b86b_best": (
            float((best_b86b_mae - mean_absolute_error(y_true, y_pred)) / best_b86b_mae)
            if not math.isnan(best_b86b_mae) and best_b86b_mae > 0
            else np.nan
        ),
        "claim_boundary": "Surrogate audit over SOLWEIG-derived compact F5 labels only; not observed truth or causal feature importance.",
    }
    row.update(h10_metrics(test, y_true, y_pred, config))
    return row


def prediction_rows(
    feature_set: str,
    target: str,
    model_name: str,
    split_family: str,
    split_name: str,
    fold_id: str,
    test: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> pd.DataFrame:
    """Build row-level out-of-fold prediction audit records."""
    keep = [
        "row_id",
        "cell_id",
        "forcing_day_id",
        "hour_sgt",
        "typology_label",
        "robust_anchor_flag",
        "neutral_boundary_flag",
        "unstable_review_flag",
    ]
    out = test[[column for column in keep if column in test.columns]].copy()
    out.insert(0, "fold_id", fold_id)
    out.insert(0, "split_name", split_name)
    out.insert(0, "split_family", split_family)
    out.insert(0, "model", model_name)
    out.insert(0, "target", target)
    out.insert(0, "feature_set", feature_set)
    out["y_true"] = y_true
    out["y_pred"] = y_pred
    out["error"] = out["y_pred"] - out["y_true"]
    out["abs_error"] = out["error"].abs()
    out["claim_boundary"] = "OOF diagnostic only; not an AOI-wide prediction."
    return out


def run_models(dataset: pd.DataFrame, registry: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run all feature-set model audits and return metrics plus selected OOF predictions."""
    folds = validation_folds(dataset, config)
    models = configured_models(config)
    b86b = baseline_lookup(config)
    oof_target = str(config["oof_export"]["target"])
    oof_models = set(config["oof_export"]["models"])
    metrics: list[dict[str, Any]] = []
    predictions: list[pd.DataFrame] = []
    for item in registry.itertuples(index=False):
        if str(item.status) != "AVAILABLE":
            continue
        feature_set = str(item.feature_set)
        features = parse_pipe_list(item.feature_columns)
        if not features:
            continue
        prepared, numeric, categorical = coerce_feature_frame(dataset, features)
        usable_features = numeric + categorical
        if not usable_features:
            continue
        for target in targets(config):
            if target not in prepared.columns:
                continue
            for split_family, split_name, fold_id, train_idx, test_idx in folds:
                train = prepared.loc[train_idx].copy()
                test = prepared.loc[test_idx].copy()
                train = train.loc[train[target].notna()].copy()
                test = test.loc[test[target].notna()].copy()
                if train.empty or test.empty:
                    continue
                y_train = pd.to_numeric(train[target], errors="coerce").to_numpy(dtype=float)
                y_true = pd.to_numeric(test[target], errors="coerce").to_numpy(dtype=float)
                for model_name, estimator in models.items():
                    pipe = make_pipeline(model_name, estimator, numeric, categorical)
                    pipe.fit(train[usable_features], y_train)
                    y_pred = pipe.predict(test[usable_features])
                    metrics.append(
                        metric_row(
                            feature_set=feature_set,
                            feature_count=len(usable_features),
                            primary_evidence_allowed=bool_value(item.primary_evidence_allowed),
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
                            b86b_lookup=b86b,
                        )
                    )
                    if target == oof_target and model_name in oof_models:
                        predictions.append(
                            prediction_rows(feature_set, target, model_name, split_family, split_name, fold_id, test, y_true, y_pred)
                        )
    metrics_frame = pd.DataFrame(metrics)
    oof_frame = pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()
    return metrics_frame, oof_frame


def best_supporting(metrics: pd.DataFrame, config: dict[str, Any]) -> tuple[str, str, str]:
    """Select the strongest feature set/model by weak supporting holdouts."""
    if metrics.empty:
        return "", "", "No model metrics available."
    primary = config["targets"]["primary"]
    support = metrics.loc[
        (metrics["target"] == primary)
        & (metrics["model"] != "dummy_mean")
        & metrics["primary_evidence_allowed"].astype(bool)
        & metrics["split_family"].isin(["cell_group_holdout", "spatial_holdout", "typology_holdout"])
    ].copy()
    if support.empty:
        return "", "", "No supporting-holdout metrics available."
    grouped = support.groupby(["feature_set", "model"], as_index=False).agg(
        MAE=("MAE", "mean"),
        Spearman=("Spearman_observed_vs_predicted", "mean"),
        top10pct=("top10pct_overlap", "mean"),
        b86b_gain=("MAE_improvement_fraction_over_b86b_best", "mean"),
    )
    grouped = grouped.sort_values(["Spearman", "top10pct", "b86b_gain", "MAE"], ascending=[False, False, False, True])
    best = grouped.iloc[0]
    headline = (
        f"{best.feature_set}/{best.model}: supporting Spearman={best.Spearman:.3f}, "
        f"top10pct={best.top10pct:.3f}, MAE gain vs B8.6b best={best.b86b_gain:.1%}."
    )
    return str(best.feature_set), str(best.model), headline


def run(config_path: Path = DEFAULT_CONFIG) -> ModelAuditResult:
    """Run feature-set model audits and write compact metric outputs."""
    config = read_config(config_path)
    repo_path(config["outputs"]["out_dir"]).mkdir(parents=True, exist_ok=True)
    try:
        dataset, registry = load_inputs(config)
    except FileNotFoundError:
        pd.DataFrame().to_csv(repo_path(config["outputs"]["feature_set_model_metrics"]), index=False)
        pd.DataFrame().to_csv(repo_path(config["outputs"]["oof_prediction_audit"]), index=False)
        return ModelAuditResult("B86C_BLOCKED_INPUT", 0, 0, 0, 0, "", "", "Inputs blocked.")

    metrics, oof = run_models(dataset, registry, config)
    metrics.to_csv(repo_path(config["outputs"]["feature_set_model_metrics"]), index=False)
    oof.to_csv(repo_path(config["outputs"]["oof_prediction_audit"]), index=False)
    best_set, best_model, headline = best_supporting(metrics, config)
    return ModelAuditResult(
        status="B86C_FEATURE_SET_MODELS_READY" if not metrics.empty else "B86C_BLOCKED_INPUT",
        metric_rows=int(len(metrics)),
        oof_rows=int(len(oof)),
        feature_sets_evaluated=int(metrics["feature_set"].nunique()) if not metrics.empty else 0,
        targets_evaluated=int(metrics["target"].nunique()) if not metrics.empty else 0,
        best_feature_set=best_set,
        best_model=best_model,
        best_supporting_headline=headline,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run B8.6c surrogate model audits across compact feature sets and non-random holdouts."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6c YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
