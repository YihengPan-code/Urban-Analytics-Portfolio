"""Run B8.6 System B surrogate baseline gate benchmarks and reports.

Inputs:
    configs/v12/systemb_b86_surrogate_protocol.yaml
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_surrogate_dataset.csv
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_feature_schema.csv
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_target_schema.csv
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_validation_splits.csv
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_n24_stress_validation_bridge.csv

Outputs:
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_baseline_model_metrics.csv
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_holdout_metrics.csv
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_target_sensitivity_metrics.csv
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_surrogate_decision_matrix.csv
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_promotion_gate.md
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_model_card_draft.md
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_report.md
    outputs/v12_surrogate/b8_6_surrogate_protocol/B8_6_STATUS.md
    docs/v12/OpenHeat_SystemB_B8_6_surrogate_protocol_CN.md

Saved metrics:
    For each target/model/split/fold: n_train, n_test, MAE, RMSE, R2,
    Spearman, Pearson, bias, p90 absolute error, top-k overlap for delta
    cooling-priority cells, sign accuracy for delta targets, worst-cell error,
    robust priority anchor errors, neutral-boundary classification accuracy,
    dummy improvement, split-family summaries, target sensitivity summaries,
    and the B8.6 promotion-gate decision.

This script uses modest sklearn baselines only. It does not run QGIS or
SOLWEIG, does not read raster files, does not create an N150 execution runner
or manifest, does not create AOI-wide prediction, does not convert Tmrt to
WBGT, and does not create local WBGT, hazard_score, risk_score, B9, or
System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import time
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
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from v12_b86_surrogate_inventory import DEFAULT_CONFIG, read_config, repo_path


warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", message="Could not find the number of physical cores.*")


@dataclass(frozen=True)
class BaselineResult:
    """Compact return record for the B8.6 baseline/report step."""

    status: str
    dataset_shape: str
    primary_target_available: bool
    main_validation_splits_available: list[str]
    best_baseline_headline: str
    n24_bridge_headline: str
    n150_multi_forcing_recommendation: str
    b9_status: str
    files_created: list[str]


def now_stamp() -> str:
    """Return a compact local timestamp string."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def command_output(args: list[str]) -> str:
    """Run a lightweight command for status reporting."""
    completed = subprocess.run(args, cwd=repo_path("."), check=False, capture_output=True, text=True)
    return completed.stdout.strip()


def bool_series(series: pd.Series) -> pd.Series:
    """Parse CSV booleans robustly."""
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def selected_features(schema: pd.DataFrame) -> list[str]:
    """Return B8.6 baseline features from the feature schema."""
    if schema.empty or "include_in_baseline" not in schema.columns:
        return []
    return schema.loc[bool_series(schema["include_in_baseline"]), "column_name"].astype(str).tolist()


def available_targets(target_schema: pd.DataFrame) -> list[str]:
    """Return available B8.6 targets from the target schema."""
    if target_schema.empty or "available" not in target_schema.columns:
        return []
    return target_schema.loc[bool_series(target_schema["available"]), "target_name"].astype(str).tolist()


def split_folds(splits: pd.DataFrame) -> list[tuple[str, str, str, pd.DataFrame]]:
    """Return valid train/test fold manifests."""
    if splits.empty:
        return []
    valid = splits.loc[
        splits["role"].isin(["train", "test"])
        & splits["split_status"].isin(["AVAILABLE", "DIAGNOSTIC_ONLY"])
    ].copy()
    folds: list[tuple[str, str, str, pd.DataFrame]] = []
    for (family, name, fold_id), part in valid.groupby(["split_family", "split_name", "fold_id"], sort=True):
        if set(part["role"].astype(str)) == {"train", "test"}:
            folds.append((str(family), str(name), str(fold_id), part.copy()))
    return folds


def coerce_model_features(dataset: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Coerce feature columns to numeric where possible and drop unusable columns."""
    out = dataset.copy()
    retained: list[str] = []
    for column in features:
        if column not in out.columns:
            continue
        numeric = pd.to_numeric(out[column], errors="coerce")
        if numeric.notna().sum() == 0 or numeric.nunique(dropna=True) <= 1:
            continue
        out[column] = numeric
        retained.append(column)
    return out, retained


def make_models(config: dict[str, Any]) -> dict[str, Any]:
    """Create modest sklearn baseline models."""
    seed = int(config["random_seed"])
    rf_cfg = config["baseline"]["random_forest"]
    hgb_cfg = config["baseline"]["hist_gradient_boosting"]
    return {
        "dummy_mean": DummyRegressor(strategy="mean"),
        "linear_regression": LinearRegression(),
        "ridge": Ridge(alpha=float(config["baseline"]["ridge"]["alpha"])),
        "elasticnet": ElasticNet(
            alpha=float(config["baseline"]["elasticnet"]["alpha"]),
            l1_ratio=float(config["baseline"]["elasticnet"]["l1_ratio"]),
            max_iter=10000,
            random_state=seed,
        ),
        "random_forest_regressor": RandomForestRegressor(
            n_estimators=int(rf_cfg["n_estimators"]),
            max_depth=int(rf_cfg["max_depth"]),
            min_samples_leaf=int(rf_cfg["min_samples_leaf"]),
            random_state=seed,
            n_jobs=1,
        ),
        "hist_gradient_boosting_regressor": HistGradientBoostingRegressor(
            max_iter=int(hgb_cfg["max_iter"]),
            learning_rate=float(hgb_cfg["learning_rate"]),
            max_leaf_nodes=int(hgb_cfg["max_leaf_nodes"]),
            random_state=seed,
        ),
    }


def make_pipeline(model_name: str, estimator: Any, features: list[str]) -> Pipeline:
    """Create a numeric preprocessing and regression pipeline."""
    steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if model_name in {"linear_regression", "ridge", "elasticnet"}:
        steps.append(("scaler", StandardScaler()))
    preprocessor = ColumnTransformer(
        transformers=[("num", Pipeline(steps), features)],
        remainder="drop",
        sparse_threshold=0.0,
    )
    return Pipeline([("prep", preprocessor), ("model", clone(estimator))])


def finite_corr(y_true: np.ndarray, y_pred: np.ndarray, method: str) -> float:
    """Compute Pearson or Spearman only when numerically meaningful."""
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


def top_k_overlap(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, target: str, config: dict[str, Any]) -> float:
    """Compute cooling-priority top-k overlap for delta targets."""
    if not target.startswith("delta_tmrt"):
        return float("nan")
    frame = test[["cell_id"]].copy()
    frame["y_true"] = y_true
    frame["y_pred"] = y_pred
    by_cell = frame.groupby("cell_id", as_index=False)[["y_true", "y_pred"]].mean(numeric_only=True)
    if by_cell.empty:
        return float("nan")
    k = max(1, int(math.ceil(float(config["baseline"]["top_k_fraction"]) * len(by_cell))))
    true_top = set(by_cell.nsmallest(k, "y_true")["cell_id"].astype(str))
    pred_top = set(by_cell.nsmallest(k, "y_pred")["cell_id"].astype(str))
    return float(len(true_top & pred_top) / k)


def sign_accuracy(y_true: np.ndarray, y_pred: np.ndarray, target: str) -> float:
    """Compute sign agreement for delta targets."""
    if not target.startswith("delta_tmrt"):
        return float("nan")
    return float(np.mean(np.sign(y_true) == np.sign(y_pred))) if len(y_true) else float("nan")


def worst_cell_error(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray) -> tuple[str, float]:
    """Return the worst mean absolute error cell in a fold."""
    frame = test[["cell_id"]].copy()
    frame["abs_error"] = np.abs(y_pred - y_true)
    if frame.empty:
        return "", float("nan")
    by_cell = frame.groupby("cell_id")["abs_error"].mean().sort_values(ascending=False)
    return str(by_cell.index[0]), float(by_cell.iloc[0])


def anchor_error_columns(
    test: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    config: dict[str, Any],
) -> dict[str, float]:
    """Return robust priority anchor error columns."""
    frame = test[["cell_id"]].copy()
    frame["abs_error"] = np.abs(y_pred - y_true)
    anchors = config["n24_bridge"]["robust_priority_anchor_cells"]
    rows: dict[str, float] = {}
    anchor_values: list[float] = []
    for cell_id in anchors:
        values = frame.loc[frame["cell_id"].astype(str) == cell_id, "abs_error"]
        value = float(values.mean()) if not values.empty else float("nan")
        rows[f"anchor_{cell_id}_abs_error"] = value
        if not math.isnan(value):
            anchor_values.append(value)
    rows["robust_priority_anchor_mae"] = float(np.mean(anchor_values)) if anchor_values else float("nan")
    return rows


def neutral_boundary_accuracy(
    test: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    target: str,
    neutral_cells: set[str],
    config: dict[str, Any],
) -> float:
    """Classify neutral-boundary cells for delta targets."""
    if not target.startswith("delta_tmrt") or not neutral_cells:
        return float("nan")
    frame = test[["cell_id"]].copy()
    frame["y_true"] = y_true
    frame["y_pred"] = y_pred
    frame = frame.loc[frame["cell_id"].astype(str).isin(neutral_cells)]
    if frame.empty:
        return float("nan")
    threshold = float(config["targets"]["neutral_delta_abs_threshold_c"])
    return float(np.mean((frame["y_true"].abs() <= threshold) == (frame["y_pred"].abs() <= threshold)))


def metric_row(
    *,
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
    neutral_cells: set[str],
) -> dict[str, Any]:
    """Compute fold metrics."""
    residual = y_pred - y_true
    worst_id, worst_error = worst_cell_error(test, y_true, y_pred)
    row: dict[str, Any] = {
        "target": target,
        "model": model_name,
        "split_family": split_family,
        "split_name": split_name,
        "fold_id": fold_id,
        "split_role": "main" if split_family in config["validation"]["main_split_families"] else "diagnostic_only",
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
        "top_k_overlap": top_k_overlap(test, y_true, y_pred, target, config),
        "sign_accuracy": sign_accuracy(y_true, y_pred, target),
        "worst_cell_id": worst_id,
        "worst_cell_error": worst_error,
        "neutral_boundary_classification_accuracy": neutral_boundary_accuracy(test, y_true, y_pred, target, neutral_cells, config),
    }
    row.update(anchor_error_columns(test, y_true, y_pred, config))
    return row


def add_dummy_improvement(metrics: pd.DataFrame) -> pd.DataFrame:
    """Attach same-fold dummy MAE and improvement fractions."""
    keys = ["target", "split_family", "split_name", "fold_id"]
    dummy = metrics.loc[metrics["model"] == "dummy_mean", keys + ["MAE"]].rename(columns={"MAE": "dummy_MAE"})
    out = metrics.merge(dummy, on=keys, how="left")
    out["MAE_improvement_over_dummy"] = out["dummy_MAE"] - out["MAE"]
    out["MAE_improvement_fraction_over_dummy"] = np.where(out["dummy_MAE"] > 0, out["MAE_improvement_over_dummy"] / out["dummy_MAE"], np.nan)
    return out


def run_models(
    dataset: pd.DataFrame,
    schema: pd.DataFrame,
    target_schema: pd.DataFrame,
    splits: pd.DataFrame,
    bridge: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Run all configured baselines for available targets and splits."""
    features = selected_features(schema)
    dataset, features = coerce_model_features(dataset, features)
    targets = [target for target in available_targets(target_schema) if target in dataset.columns]
    folds = split_folds(splits)
    models = make_models(config)
    neutral_cells = set(bridge.loc[bridge["bridge_role"].astype(str).str.contains("neutral", case=False, na=False), "cell_id"].astype(str)) if not bridge.empty else set()
    metrics: list[dict[str, Any]] = []
    row_lookup = dataset.set_index("row_id", drop=False)
    for target in targets:
        for split_family, split_name, fold_id, manifest in folds:
            train_ids = manifest.loc[manifest["role"] == "train", "row_id"].astype(str)
            test_ids = manifest.loc[manifest["role"] == "test", "row_id"].astype(str)
            train = row_lookup.loc[train_ids].copy()
            test = row_lookup.loc[test_ids].copy()
            train = train.loc[train[target].notna()].copy()
            test = test.loc[test[target].notna()].copy()
            if train.empty or test.empty:
                continue
            x_train = train[features]
            x_test = test[features]
            y_train = pd.to_numeric(train[target], errors="coerce").to_numpy(dtype=float)
            y_true = pd.to_numeric(test[target], errors="coerce").to_numpy(dtype=float)
            for model_name, estimator in models.items():
                pipe = make_pipeline(model_name, estimator, features)
                pipe.fit(x_train, y_train)
                y_pred = pipe.predict(x_test)
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
                        neutral_cells=neutral_cells,
                    )
                )
    return add_dummy_improvement(pd.DataFrame(metrics)) if metrics else pd.DataFrame()


def summarize_holdouts(metrics: pd.DataFrame) -> pd.DataFrame:
    """Summarize fold metrics by target/model/split family."""
    if metrics.empty:
        return pd.DataFrame()
    group_cols = ["target", "model", "split_family", "split_role"]
    columns = [
        "n_train",
        "n_test",
        "MAE",
        "RMSE",
        "R2",
        "Spearman_observed_vs_predicted",
        "Pearson_observed_vs_predicted",
        "bias",
        "p90_abs_error",
        "top_k_overlap",
        "sign_accuracy",
        "worst_cell_error",
        "robust_priority_anchor_mae",
        "neutral_boundary_classification_accuracy",
        "MAE_improvement_fraction_over_dummy",
    ]
    summary = metrics.groupby(group_cols, as_index=False)[columns].mean(numeric_only=True)
    counts = metrics.groupby(group_cols, as_index=False).agg(n_folds=("fold_id", "nunique"), n_test_rows=("n_test", "sum"))
    return summary.merge(counts, on=group_cols, how="left")


def best_primary_headline(holdout: pd.DataFrame, config: dict[str, Any]) -> str:
    """Return the best primary-target baseline headline."""
    primary = config["targets"]["primary"]
    subset = holdout.loc[
        (holdout["target"] == primary)
        & (holdout["model"] != "dummy_mean")
        & (holdout["split_family"].isin(config["validation"]["main_split_families"]))
    ].copy()
    if subset.empty:
        return "No non-dummy primary-target main holdout result available."
    by_model = subset.groupby("model", as_index=False).agg(
        mean_MAE=("MAE", "mean"),
        mean_R2=("R2", "mean"),
        mean_spearman=("Spearman_observed_vs_predicted", "mean"),
        mean_dummy_improvement=("MAE_improvement_fraction_over_dummy", "mean"),
    )
    row = by_model.sort_values(["mean_MAE", "model"]).iloc[0]
    return (
        f"{row['model']} on delta_tmrt_p90_c: mean main-holdout MAE={row['mean_MAE']:.4f}, "
        f"R2={row['mean_R2']:.3f}, Spearman={row['mean_spearman']:.3f}, "
        f"MAE improvement vs dummy={row['mean_dummy_improvement']:.1%}"
    )


def baseline_promising(holdout: pd.DataFrame, config: dict[str, Any]) -> bool:
    """Return whether one non-dummy model beats dummy under main holdout families."""
    primary = config["targets"]["primary"]
    required = {"cell_group_holdout", "typology_holdout", "hour_holdout"}
    threshold = float(config["baseline"]["promising_min_mae_improvement_fraction"])
    subset = holdout.loc[
        (holdout["target"] == primary)
        & (holdout["model"] != "dummy_mean")
        & (holdout["split_family"].isin(required))
    ].copy()
    if subset.empty:
        return False
    pivot = subset.pivot_table(index="model", columns="split_family", values="MAE_improvement_fraction_over_dummy", aggfunc="mean")
    for _, row in pivot.iterrows():
        if required.issubset(set(row.dropna().index)) and bool((row[list(required)] > threshold).all()):
            return True
    return False


def target_sensitivity(holdout: pd.DataFrame, target_schema: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Summarize target sensitivity without comparing unlike target units naively."""
    rows: list[dict[str, Any]] = []
    available = available_targets(target_schema)
    main = holdout.loc[holdout["split_family"].isin(config["validation"]["main_split_families"])] if not holdout.empty else pd.DataFrame()
    for target in [config["targets"]["primary"], *config["targets"]["secondary"]]:
        target_rows = main.loc[(main["target"] == target) & (main["model"] != "dummy_mean")].copy() if not main.empty else pd.DataFrame()
        dummy_rows = main.loc[(main["target"] == target) & (main["model"] == "dummy_mean")].copy() if not main.empty else pd.DataFrame()
        if target_rows.empty:
            rows.append(
                {
                    "target": target,
                    "available": target in available,
                    "best_model": "not_available",
                    "mean_main_MAE": np.nan,
                    "mean_main_R2": np.nan,
                    "mean_main_spearman": np.nan,
                    "mean_dummy_MAE": float(dummy_rows["MAE"].mean()) if not dummy_rows.empty else np.nan,
                    "mean_improvement_fraction_over_dummy": np.nan,
                    "b86_target_card_verdict": "UNAVAILABLE_OR_NOT_EVALUATED",
                    "notes": "Target not available or not evaluated under main holdout splits.",
                }
            )
            continue
        best_by_model = target_rows.groupby("model", as_index=False).agg(
            mean_main_MAE=("MAE", "mean"),
            mean_main_R2=("R2", "mean"),
            mean_main_spearman=("Spearman_observed_vs_predicted", "mean"),
            mean_improvement_fraction_over_dummy=("MAE_improvement_fraction_over_dummy", "mean"),
        )
        best = best_by_model.sort_values(["mean_main_MAE", "model"]).iloc[0]
        rows.append(
            {
                "target": target,
                "available": target in available,
                "best_model": best["model"],
                "mean_main_MAE": float(best["mean_main_MAE"]),
                "mean_main_R2": float(best["mean_main_R2"]),
                "mean_main_spearman": float(best["mean_main_spearman"]),
                "mean_dummy_MAE": float(dummy_rows["MAE"].mean()) if not dummy_rows.empty else np.nan,
                "mean_improvement_fraction_over_dummy": float(best["mean_improvement_fraction_over_dummy"]),
                "b86_target_card_verdict": (
                    "PRIMARY_REMAINS_B8_6_TARGET_CARD"
                    if target == config["targets"]["primary"]
                    else "SECONDARY_CONTEXT_ONLY_NOT_PROMOTION_TARGET"
                ),
                "notes": (
                    "Primary target remains best for B8.6 because it matches the F4 overhead-minus-base target card."
                    if target == config["targets"]["primary"]
                    else "Secondary metric is sensitivity/context only; units and interpretation are not directly interchangeable with the primary delta target."
                ),
            }
        )
    return pd.DataFrame(rows)


def final_status(
    dataset: pd.DataFrame,
    target_schema: pd.DataFrame,
    splits: pd.DataFrame,
    metrics: pd.DataFrame,
    holdout: pd.DataFrame,
    config: dict[str, Any],
) -> str:
    """Derive the B8.6 decision status."""
    if dataset.empty:
        return "BLOCKED_LABEL_INPUT"
    primary_available = config["targets"]["primary"] in available_targets(target_schema)
    features_available = bool(selected_features(pd.read_csv(repo_path(config["outputs"]["feature_schema"]))))
    main_splits = set(splits.loc[(splits["split_status"] == "AVAILABLE") & splits["split_family"].isin(config["validation"]["main_split_families"]), "split_family"].unique())
    protocol_ready = primary_available and features_available and {"cell_group_holdout", "spatial_holdout", "typology_holdout", "hour_holdout"}.issubset(main_splits) and not metrics.empty
    forcing_future_required = bool((splits["split_family"] == "forcing_day_holdout").any())
    if not primary_available:
        return "BLOCKED_LABEL_INPUT"
    if not features_available:
        return "BLOCKED_FEATURE_INPUT"
    if not protocol_ready:
        return "FAILED"
    if forcing_future_required:
        return "B86_WEAK_BASELINE_NEEDS_N150_MULTIFORCING"
    if baseline_promising(holdout, config):
        return "B86_BASELINE_PROMISING"
    return "B86_SURROGATE_PROTOCOL_PASS"


def decision_matrix(
    status: str,
    dataset: pd.DataFrame,
    schema: pd.DataFrame,
    target_schema: pd.DataFrame,
    splits: pd.DataFrame,
    metrics: pd.DataFrame,
    holdout: pd.DataFrame,
    bridge: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Build the machine-readable B8.6 decision matrix."""
    available_split_families = sorted(splits.loc[splits["split_status"] == "AVAILABLE", "split_family"].unique().tolist()) if not splits.empty else []
    rows = [
        {
            "gate": "label_input",
            "status": "PASS" if config["targets"]["primary"] in available_targets(target_schema) else "BLOCKED_LABEL_INPUT",
            "evidence": f"Dataset rows={len(dataset)}, targets={','.join(available_targets(target_schema))}.",
            "next_action": "Use compact N150 pairwise labels only; do not rerun SOLWEIG.",
            "claim_boundary": "Labels are SOLWEIG-derived Tmrt, not WBGT, risk, observed truth, or causal effect.",
        },
        {
            "gate": "feature_input",
            "status": "PASS" if selected_features(schema) else "BLOCKED_FEATURE_INPUT",
            "evidence": f"Baseline feature count={len(selected_features(schema))}.",
            "next_action": "Keep features compact and non-raster; do not derive new raster features in this lane.",
            "claim_boundary": "Features support surrogate baseline only; feature importance is not causal proof.",
        },
        {
            "gate": "validation_protocol",
            "status": "PASS" if {"cell_group_holdout", "spatial_holdout", "typology_holdout", "hour_holdout"}.issubset(set(available_split_families)) else "WEAK",
            "evidence": f"Available split families: {','.join(available_split_families)}.",
            "next_action": "Treat random_split as diagnostic only; keep grouped/holdout evidence primary.",
            "claim_boundary": "No random row split as main evidence.",
        },
        {
            "gate": "baseline_gate",
            "status": "BASELINE_PROMISING" if baseline_promising(holdout, config) else "WEAK",
            "evidence": best_primary_headline(holdout, config) if not holdout.empty else "No metrics.",
            "next_action": "Review grouped/typology/hour holdout metrics before any promotion.",
            "claim_boundary": "A baseline is an emulator of SOLWEIG labels only.",
        },
        {
            "gate": "forcing_day_holdout",
            "status": "FUTURE_REQUIRED",
            "evidence": "Existing N150 labels are single-forcing; no forcing-day holdout exists.",
            "next_action": "Run a future controlled N150 multi-forcing precheck/execution lane before B9 or promotion.",
            "claim_boundary": "Do not claim forcing generalisation from single-forcing N150 labels.",
        },
        {
            "gate": "n24_stress_validation_bridge",
            "status": "PASS" if not bridge.empty else "WEAK",
            "evidence": f"N24 bridge rows={len(bridge)}; stress-validation only.",
            "next_action": "Use N24 anchors/neutral/unstable cells for interpretation checks, not training.",
            "claim_boundary": "N24 cannot validate N150 generalisation, observed truth, WBGT, risk, B9, or AOI-wide prediction.",
        },
        {
            "gate": "b9_status",
            "status": "BLOCKED",
            "evidence": "B8.6 is surrogate protocol / baseline gate only.",
            "next_action": "Keep B9 blocked until separately scoped after N150 multi-forcing and promotion review.",
            "claim_boundary": "Do not call this B9.",
        },
        {
            "gate": "final_status",
            "status": status,
            "evidence": "Protocol artifacts and baseline metrics were produced from compact inputs.",
            "next_action": "N150 multi-forcing remains the next hardening recommendation unless blockers are found.",
            "claim_boundary": "No local WBGT, risk, hazard_score, System A/B coupling, raster commit, or Tmrt-to-WBGT conversion.",
        },
    ]
    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 20) -> str:
    """Return a small markdown table or a placeholder."""
    if frame.empty:
        return "_No rows available._"
    return frame[columns].head(max_rows).to_markdown(index=False)


def write_promotion_gate(path: Path, status: str, holdout: pd.DataFrame, sensitivity: pd.DataFrame, config: dict[str, Any]) -> None:
    """Write the B8.6 promotion gate Markdown."""
    promising = baseline_promising(holdout, config)
    lines = [
        "# B8.6 Promotion Gate",
        "",
        f"Status: `{status}`",
        "",
        "## Gate Result",
        "",
        f"- Protocol-ready artifacts: {'yes' if status.startswith('B86_') else 'no'}",
        f"- Baseline promising under cell/typology/hour holdouts: {'yes' if promising else 'no'}",
        "- Forcing-day holdout: `FUTURE_REQUIRED` because existing N150 labels are single-forcing.",
        "- B9 status: `BLOCKED`.",
        "",
        "## Target-Card Verdict",
        "",
        markdown_table(sensitivity, ["target", "available", "best_model", "mean_main_MAE", "mean_main_spearman", "b86_target_card_verdict"], 10),
        "",
        "## Promotion Boundary",
        "",
        "B8.6 may support a reviewed surrogate protocol baseline, but it does not authorize AOI-wide prediction, B9, local WBGT, risk, hazard_score, causal feature importance, or System A/B coupling.",
        "",
        "## Next Action",
        "",
        "Run a future N150 multi-forcing precheck and controlled execution lane before any surrogate promotion beyond this weak/single-forcing baseline gate.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_model_card(path: Path, status: str, dataset: pd.DataFrame, schema: pd.DataFrame, holdout: pd.DataFrame, bridge: pd.DataFrame, config: dict[str, Any]) -> None:
    """Write the B8.6 model card draft."""
    lines = [
        "# B8.6 System B Surrogate Model Card Draft",
        "",
        f"Generated: {now_stamp()}",
        "",
        "## Intended Role",
        "",
        "Protocol and baseline benchmarking for a surrogate/emulator of SOLWEIG-derived System B radiative labels in Toa Payoh.",
        "",
        "## Current Decision",
        "",
        f"`{status}`",
        "",
        "## Dataset",
        "",
        f"- Rows: {len(dataset)}",
        f"- Cells: {dataset['cell_id'].nunique() if not dataset.empty else 0}",
        f"- Hours: {', '.join(str(value) for value in sorted(dataset['hour_sgt'].dropna().unique())) if not dataset.empty else '(none)'}",
        "- Primary target: `delta_tmrt_p90_c = overhead_as_canopy - base`.",
        f"- Baseline predictors: {len(selected_features(schema))} compact physical/hour-aware columns.",
        "",
        "## Validation Families",
        "",
        "- Main: `cell_group_holdout`, `spatial_holdout`, `typology_holdout`, `hour_holdout`.",
        "- Diagnostic only: `random_split`.",
        "- Future required: `forcing_day_holdout`, `scenario_holdout` for non-pairwise scenario-labelled targets.",
        "",
        "## Baseline Headline",
        "",
        f"- {best_primary_headline(holdout, config)}",
        "",
        "## N24 Stress-Validation Bridge",
        "",
        f"- Bridge rows: {len(bridge)}.",
        "- N24 validates stress interpretation only; it is not training evidence here.",
        "",
        "## Explicit Non-Claims",
        "",
        "- Not B9.",
        "- Not local WBGT.",
        "- Not risk.",
        "- Not observed truth.",
        "- Not causal feature importance.",
        "- No raster committed.",
        "- No Tmrt-to-WBGT conversion.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(
    path: Path,
    status: str,
    dataset: pd.DataFrame,
    label_inventory: pd.DataFrame,
    feature_inventory: pd.DataFrame,
    schema: pd.DataFrame,
    target_schema_frame: pd.DataFrame,
    splits: pd.DataFrame,
    holdout: pd.DataFrame,
    sensitivity: pd.DataFrame,
    bridge: pd.DataFrame,
    decision: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    """Write the full B8.6 Markdown report."""
    available_split_families = sorted(splits.loc[splits["split_status"] == "AVAILABLE", "split_family"].unique().tolist()) if not splits.empty else []
    lines = [
        "# B8.6 System B Surrogate Protocol / Baseline Gate",
        "",
        f"Generated: {now_stamp()}",
        "",
        f"Status: `{status}`",
        "",
        "## 1. Why B8.6 Follows F4",
        "",
        "B8.5-F4 passed the N24 decision matrix and froze the target-card interpretation for `delta_tmrt_p90_c = overhead_as_canopy - base`. B8.6 therefore uses existing compact N150 labels, when available, to test a surrogate protocol and baseline gate. N24/F4 remains stress-validation context only.",
        "",
        "## 2. Label Source Inventory",
        "",
        markdown_table(label_inventory, ["candidate_name", "path", "exists", "row_count", "has_delta_tmrt_p90_c", "usable_for_b86_primary"], 12),
        "",
        "## 3. Feature Source Inventory",
        "",
        markdown_table(feature_inventory, ["candidate_name", "path", "exists", "row_count", "available_feature_count", "usable_for_b86_features"], 12),
        "",
        "## 4. Dataset Shape And Targets",
        "",
        f"- Dataset shape: {dataset.shape[0]} rows x {dataset.shape[1]} columns.",
        f"- Unique cells: {dataset['cell_id'].nunique() if not dataset.empty else 0}.",
        f"- Scenario context: `{config['expected']['scenario_context']}`.",
        "",
        markdown_table(target_schema_frame, ["target_name", "role", "available", "non_null_count", "source_definition"], 10),
        "",
        "## 5. Validation Split Protocol",
        "",
        f"- Available main split families: {', '.join(available_split_families) if available_split_families else '(none)'}.",
        "- `random_split` is diagnostic only and is not main evidence.",
        "- `forcing_day_holdout` is future-required because existing N150 labels are single-forcing.",
        "",
        "## 6. Baseline Model Results",
        "",
        f"- {best_primary_headline(holdout, config)}",
        "",
        markdown_table(
            holdout.loc[(holdout["target"] == config["targets"]["primary"]) & (holdout["split_role"] == "main")].sort_values(["split_family", "MAE"]),
            ["split_family", "model", "MAE", "RMSE", "R2", "Spearman_observed_vs_predicted", "MAE_improvement_fraction_over_dummy"],
            30,
        ),
        "",
        "## 7. Holdout Weaknesses",
        "",
        "- No forcing-day holdout is available for existing N150 labels.",
        "- Scenario holdout is not applicable to the primary pairwise delta target because scenario has already been differenced.",
        "- h10 remains caveated from F4 and is not anchor evidence.",
        "- Any promising baseline remains a surrogate of SOLWEIG labels, not observed local heat truth.",
        "",
        "## 8. Target Sensitivity",
        "",
        markdown_table(sensitivity, ["target", "available", "best_model", "mean_main_MAE", "mean_main_spearman", "b86_target_card_verdict"], 10),
        "",
        "## 9. N24 Stress-Validation Bridge",
        "",
        markdown_table(bridge, ["cell_id", "bridge_role", "n150_label_present", "training_role"], 20),
        "",
        "## 10. Surrogate Role Decision",
        "",
        markdown_table(decision, ["gate", "status", "evidence", "next_action"], 20),
        "",
        "## 11. Claim Boundaries",
        "",
        "- This is not B9.",
        "- This is not local WBGT.",
        "- This is not risk.",
        "- This is not observed truth.",
        "- This is not causal feature importance.",
        "- No raster is committed.",
        "- No Tmrt-to-WBGT conversion is performed.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_cn_doc(path: Path, status: str, dataset: pd.DataFrame, holdout: pd.DataFrame, sensitivity: pd.DataFrame, decision: pd.DataFrame, bridge: pd.DataFrame, config: dict[str, Any]) -> None:
    """Write the UTF-8 Chinese B8.6 protocol document."""
    lines = [
        "# OpenHeat System B B8.6 surrogate protocol / baseline gate 中文说明",
        "",
        f"生成时间：{now_stamp()}",
        "",
        "## 结论",
        "",
        f"- B8.6 状态：`{status}`",
        f"- 数据集规模：{dataset.shape[0]} 行 x {dataset.shape[1]} 列",
        f"- 主目标：`delta_tmrt_p90_c = overhead_as_canopy - base`",
        f"- 最佳基线摘要：{best_primary_headline(holdout, config)}",
        "- B9 状态：`BLOCKED`",
        "",
        "## 1. 为什么 B8.6 接在 F4 后面",
        "",
        "F4 已确认 N24 核心小时稳定性，并把 `delta_tmrt_p90_c` 作为目标卡变量。B8.6 只消费既有紧凑 N150 标签和紧凑特征表，用来建立 surrogate 协议、验证划分和基线门槛；N24/F4 只作为 stress-validation 解释上下文。",
        "",
        "## 2. 数据集和目标定义",
        "",
        f"- 行粒度：cell × hour × `{config['expected']['scenario_context']}`。",
        "- `cell_id` 是分组标识，不作为数值预测特征。",
        "- `hour_sgt` 被允许进入 hour-aware 基线模型，但同时必须评估 hour holdout。",
        "- scenario 不作为主目标预测特征，因为主目标已经是 overhead 与 base 的差值。",
        "",
        "## 3. 验证协议",
        "",
        "- 主证据：cell_group_holdout、spatial_holdout、typology_holdout、hour_holdout。",
        "- random_split 仅为诊断，不作为主证据。",
        "- forcing-day holdout 当前不可用，因为既有 N150 标签是 single-forcing；后续需要 N150 multi-forcing。",
        "",
        "## 4. 基线模型结果",
        "",
        markdown_table(
            holdout.loc[(holdout["target"] == config["targets"]["primary"]) & (holdout["split_role"] == "main")].sort_values(["split_family", "MAE"]),
            ["split_family", "model", "MAE", "RMSE", "R2", "Spearman_observed_vs_predicted", "MAE_improvement_fraction_over_dummy"],
            24,
        ),
        "",
        "## 5. 目标敏感性",
        "",
        markdown_table(sensitivity, ["target", "available", "best_model", "mean_main_MAE", "mean_main_spearman", "b86_target_card_verdict"], 10),
        "",
        "## 6. N24 stress-validation bridge",
        "",
        f"- bridge 行数：{len(bridge)}。",
        "- robust priority anchors、neutral-boundary cells 和 unstable-review cells 只用于解释压力测试，不进入训练。",
        "- h10 仍保留 caveat，不能作为 priority anchor 证据。",
        "",
        "## 7. Surrogate 角色决定",
        "",
        markdown_table(decision, ["gate", "status", "next_action"], 20),
        "",
        "## 8. Claim boundaries",
        "",
        "- 这不是 B9。",
        "- 这不是 local WBGT。",
        "- 这不是 risk。",
        "- 这不是 observed truth。",
        "- 这不是 causal feature importance。",
        "- 没有提交 raster。",
        "- 没有 Tmrt-to-WBGT conversion。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def output_files(config: dict[str, Any]) -> list[str]:
    """Return the B8.6 files created by this lane."""
    keys = [
        "input_inventory",
        "label_source_inventory",
        "feature_source_inventory",
        "surrogate_dataset",
        "feature_schema",
        "target_schema",
        "validation_splits",
        "baseline_model_metrics",
        "holdout_metrics",
        "target_sensitivity_metrics",
        "n24_stress_validation_bridge",
        "surrogate_decision_matrix",
        "promotion_gate",
        "model_card_draft",
        "report",
        "status",
        "cn_doc",
    ]
    return [config["outputs"][key] for key in keys]


def write_status_file(path: Path, result: BaselineResult, status: str, config: dict[str, Any]) -> None:
    """Write the B8.6 lane status file."""
    branch = command_output(["git", "branch", "--show-current"])
    lines = [
        "# B8.6 Status",
        "",
        f"Status: {status}",
        f"Branch: {branch}",
        "Scope: System B surrogate protocol / baseline gate only.",
        "",
        "## Commands run",
        "",
        "- `python --version` (plain `python` was not on PATH in this shell)",
        "- `C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat python -m compileall scripts/v12_b86_surrogate_inventory.py scripts/v12_b86_surrogate_dataset.py scripts/v12_b86_surrogate_baseline.py scripts/v12_b86_run_surrogate_protocol.py`",
        "- `C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat python scripts/v12_b86_run_surrogate_protocol.py --config configs/v12/systemb_b86_surrogate_protocol.yaml`",
        "- `C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat python -c \"...mojibake check...\"`",
        "- `git status --short -- .`",
        "- PowerShell forbidden-file check over `git status --porcelain -- .`",
        "",
        "## Files created / modified",
        "",
        "- `configs/v12/systemb_b86_surrogate_protocol.yaml`",
        "- `scripts/v12_b86_surrogate_inventory.py`",
        "- `scripts/v12_b86_surrogate_dataset.py`",
        "- `scripts/v12_b86_surrogate_baseline.py`",
        "- `scripts/v12_b86_run_surrogate_protocol.py`",
        *[f"- `{path_value}`" for path_value in output_files(config)],
        "",
        "## Key results",
        "",
        f"- N150 label source found: {'yes' if result.primary_target_available else 'no'}",
        f"- Dataset shape: {result.dataset_shape}",
        f"- Primary target availability: {result.primary_target_available}",
        f"- Main validation splits available: {', '.join(result.main_validation_splits_available)}",
        f"- Best baseline headline: {result.best_baseline_headline}",
        f"- N24 stress-validation bridge headline: {result.n24_bridge_headline}",
        f"- N150 multi-forcing recommendation: {result.n150_multi_forcing_recommendation}",
        f"- B9 status: {result.b9_status}",
        "",
        "## Caveats",
        "",
        "- Existing N150 labels are single-forcing.",
        "- N24 is stress-validation context only.",
        "- No QGIS/SOLWEIG/raster operation was run by this lane.",
        "- No local WBGT, hazard_score, risk_score, or System A/B coupling output was created.",
        "- No Tmrt-to-WBGT conversion was performed.",
        "",
        "## Safe to commit",
        "",
        "- Compact B8.6 config, scripts, docs, CSV, and Markdown outputs after review.",
        "",
        "## Not safe to commit",
        "",
        "- Rasters, `.tif`, `.tiff`, `svfs.zip`, `data/solweig/`, `data/rasters/`, raw archives, patch zip packages, and AOI-wide prediction outputs.",
        "",
        "## Next recommended action",
        "",
        "- N150 multi-forcing precheck and controlled execution/hardening before surrogate promotion or B9.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_blocked_outputs(config: dict[str, Any], status: str) -> BaselineResult:
    """Write required outputs for a blocked/failed baseline step."""
    empty = pd.DataFrame()
    empty.to_csv(repo_path(config["outputs"]["baseline_model_metrics"]), index=False)
    empty.to_csv(repo_path(config["outputs"]["holdout_metrics"]), index=False)
    empty.to_csv(repo_path(config["outputs"]["target_sensitivity_metrics"]), index=False)
    decision = pd.DataFrame(
        [
            {
                "gate": "final_status",
                "status": status,
                "evidence": "Dataset or feature inputs are blocked.",
                "next_action": "Fix exact label/feature blocker from inventories.",
                "claim_boundary": "No surrogate baseline is trained.",
            }
        ]
    )
    decision.to_csv(repo_path(config["outputs"]["surrogate_decision_matrix"]), index=False)
    for key in ["promotion_gate", "model_card_draft", "report", "status", "cn_doc"]:
        repo_path(config["outputs"][key]).write_text(f"# B8.6\n\nStatus: `{status}`\n\nFix label/feature blocker from inventories.\n", encoding="utf-8")
    return BaselineResult(status, "0 x 0", False, [], "No baseline run.", "No bridge.", "Fix blocker first.", "BLOCKED", output_files(config))


def run(config_path: Path = DEFAULT_CONFIG) -> BaselineResult:
    """Run B8.6 baseline metrics and reports."""
    config = read_config(config_path)
    out_dir = repo_path(config["outputs"]["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = repo_path(config["outputs"]["surrogate_dataset"])
    schema_path = repo_path(config["outputs"]["feature_schema"])
    target_schema_path = repo_path(config["outputs"]["target_schema"])
    splits_path = repo_path(config["outputs"]["validation_splits"])
    bridge_path = repo_path(config["outputs"]["n24_stress_validation_bridge"])
    if not all(path.exists() for path in [dataset_path, schema_path, target_schema_path, splits_path, bridge_path]):
        return write_blocked_outputs(config, "BLOCKED_LABEL_INPUT")

    dataset = pd.read_csv(dataset_path, dtype={"cell_id": "string", "row_id": "string"})
    schema = pd.read_csv(schema_path)
    target_schema_frame = pd.read_csv(target_schema_path)
    splits = pd.read_csv(splits_path, dtype={"row_id": "string", "cell_id": "string", "fold_id": "string"})
    bridge = pd.read_csv(bridge_path, dtype={"cell_id": "string"}) if bridge_path.exists() else pd.DataFrame()
    if dataset.empty or schema.empty or target_schema_frame.empty:
        return write_blocked_outputs(config, "BLOCKED_LABEL_INPUT")

    metrics = run_models(dataset, schema, target_schema_frame, splits, bridge, config)
    holdout = summarize_holdouts(metrics)
    sensitivity = target_sensitivity(holdout, target_schema_frame, config)
    status = final_status(dataset, target_schema_frame, splits, metrics, holdout, config)
    decision = decision_matrix(status, dataset, schema, target_schema_frame, splits, metrics, holdout, bridge, config)

    metrics.to_csv(repo_path(config["outputs"]["baseline_model_metrics"]), index=False)
    holdout.to_csv(repo_path(config["outputs"]["holdout_metrics"]), index=False)
    sensitivity.to_csv(repo_path(config["outputs"]["target_sensitivity_metrics"]), index=False)
    decision.to_csv(repo_path(config["outputs"]["surrogate_decision_matrix"]), index=False)

    best_headline = best_primary_headline(holdout, config)
    n24_headline = f"{len(bridge)} bridge rows; robust anchors/neutral-boundary/unstable cells are stress-validation only."
    n150_recommendation = "N150 multi-forcing precheck and controlled execution are required before promotion/B9."
    b9_status = "BLOCKED"
    result = BaselineResult(
        status=status,
        dataset_shape=f"{dataset.shape[0]} x {dataset.shape[1]}",
        primary_target_available=config["targets"]["primary"] in available_targets(target_schema_frame),
        main_validation_splits_available=sorted(splits.loc[splits["split_status"] == "AVAILABLE", "split_family"].unique().tolist()),
        best_baseline_headline=best_headline,
        n24_bridge_headline=n24_headline,
        n150_multi_forcing_recommendation=n150_recommendation,
        b9_status=b9_status,
        files_created=output_files(config),
    )

    write_promotion_gate(repo_path(config["outputs"]["promotion_gate"]), status, holdout, sensitivity, config)
    write_model_card(repo_path(config["outputs"]["model_card_draft"]), status, dataset, schema, holdout, bridge, config)
    label_inventory = pd.read_csv(repo_path(config["outputs"]["label_source_inventory"])) if repo_path(config["outputs"]["label_source_inventory"]).exists() else pd.DataFrame()
    feature_inventory = pd.read_csv(repo_path(config["outputs"]["feature_source_inventory"])) if repo_path(config["outputs"]["feature_source_inventory"]).exists() else pd.DataFrame()
    write_report(
        repo_path(config["outputs"]["report"]),
        status,
        dataset,
        label_inventory,
        feature_inventory,
        schema,
        target_schema_frame,
        splits,
        holdout,
        sensitivity,
        bridge,
        decision,
        config,
    )
    write_cn_doc(repo_path(config["outputs"]["cn_doc"]), status, dataset, holdout, sensitivity, decision, bridge, config)
    write_status_file(repo_path(config["outputs"]["status"]), result, status, config)
    return result


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run B8.6 surrogate baseline gate and reports.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6 YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
