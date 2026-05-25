#!/usr/bin/env python
"""Run the Level 1 model registry using canonical sklearn Ridge.

Inputs:
    - configs/v11/level1_model_registry.yaml
    - outputs/v11_level1/reproduction/feature_matrix_<dataset_label>.csv

Outputs:
    - outputs/v11_level1/reproduction/oof_predictions_reproduction.csv

Saved metadata in the OOF output:
    - ridge_backend, ridge_backend_requested, imputation_method, scaling_method,
      alpha_used, sklearn_failed, fallback_used.

Models are limited to existing M3_weather_ridge, M4_inertia_ridge, and
M7_compact_weather_ridge Ridge definitions. No fallback solver and no new model
family are used. If sklearn Ridge fails, this script raises and stops.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
IMPUTATION_METHOD = "SimpleImputer(strategy=median)"
SCALING_METHOD = "StandardScaler(with_mean=True, with_std=True)"


def load_registry(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def loso_folds(df: pd.DataFrame) -> list[tuple[str, np.ndarray, np.ndarray]]:
    if "station_id" not in df.columns:
        raise SystemExit("[ERROR] LOSO requires station_id")
    folds: list[tuple[str, np.ndarray, np.ndarray]] = []
    station_series = df["station_id"].astype(str)
    for station_id in sorted(station_series.dropna().unique().tolist()):
        test_mask = station_series.eq(station_id).to_numpy()
        train_mask = ~test_mask
        if test_mask.sum() > 0 and train_mask.sum() > 0:
            folds.append((station_id, np.where(train_mask)[0], np.where(test_mask)[0]))
    return folds


def available_features(df: pd.DataFrame, features: list[str]) -> list[str]:
    return [feature for feature in features if feature in df.columns]


def fit_predict_sklearn_ridge(
    train: pd.DataFrame,
    test: pd.DataFrame,
    y_col: str,
    features: list[str],
    alpha: float,
) -> pd.Series:
    pipe = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", Ridge(alpha=alpha)),
    ])
    pipe.fit(train[features], pd.to_numeric(train[y_col], errors="coerce"))
    return pd.Series(pipe.predict(test[features]), index=test.index)


def run_dataset(
    registry: dict,
    spec: dict,
    out_dir: Path,
    ridge_backend: str,
    command_run: str,
) -> pd.DataFrame:
    if ridge_backend != "sklearn":
        raise SystemExit("[ERROR] canonical Level 1 reproduction supports only ridge_backend=sklearn")
    matrix_path = out_dir / f"feature_matrix_{spec['dataset_label']}.csv"
    if not matrix_path.exists():
        print(f"[WARN] skipping {spec['dataset_label']}: missing {matrix_path}")
        return pd.DataFrame()
    df = pd.read_csv(matrix_path, low_memory=False)
    folds = loso_folds(df)
    alpha = float(registry.get("ridge_alpha", 1.0))
    pred_frames: list[pd.DataFrame] = []
    for model_spec in registry["models"]:
        model_name = model_spec["model"]
        group_name = model_spec["feature_group"]
        features = available_features(df, registry["feature_groups"].get(group_name, []))
        if not features:
            raise SystemExit(f"[ERROR] no available features for {model_name} on {spec['dataset_label']}")
        oof = pd.Series(np.nan, index=df.index)
        fold_used = pd.Series("", index=df.index, dtype=object)
        for fold_name, train_idx, test_idx in folds:
            train = df.iloc[train_idx].copy()
            test = df.iloc[test_idx].copy()
            pred = fit_predict_sklearn_ridge(train, test, spec["target_col"], features, alpha)
            oof.iloc[test_idx] = pred.to_numpy()
            fold_used.iloc[test_idx] = fold_name
        cols = [
            c
            for c in [
                "row_id",
                "timestamp",
                "timestamp_sgt",
                "date",
                "hour",
                "station_id",
                spec["target_col"],
                spec["raw_proxy_col"],
            ]
            if c in df.columns
        ]
        pred_df = df[cols].copy()
        pred_df.insert(0, "dataset_label", spec["dataset_label"])
        pred_df["target_col"] = spec["target_col"]
        pred_df["raw_proxy_col"] = spec["raw_proxy_col"]
        pred_df["model"] = model_name
        pred_df["cv_scheme"] = "loso"
        pred_df["fold"] = fold_used.to_numpy()
        pred_df["n_folds"] = len(folds)
        pred_df["n_features"] = len(features)
        pred_df["features"] = ";".join(features)
        pred_df["ridge_backend_requested"] = "sklearn"
        pred_df["ridge_backend"] = "sklearn"
        pred_df["imputation_method"] = IMPUTATION_METHOD
        pred_df["scaling_method"] = SCALING_METHOD
        pred_df["alpha_used"] = alpha
        pred_df["sklearn_failed"] = False
        pred_df["fallback_used"] = False
        pred_df["sklearn_failure_message"] = ""
        pred_df["sys_executable"] = sys.executable
        pred_df["command_run"] = command_run
        pred_df["prediction_wbgt_c"] = oof.to_numpy()
        pred_df["observed_wbgt_c"] = pd.to_numeric(df[spec["target_col"]], errors="coerce")
        pred_df["residual_obs_minus_pred_c"] = pred_df["observed_wbgt_c"] - pred_df["prediction_wbgt_c"]
        pred_frames.append(pred_df)
        print(f"[OK] {spec['dataset_label']} {model_name}: {len(folds)} LOSO folds, {len(features)} features, backend=sklearn")
    return pd.concat(pred_frames, ignore_index=True, sort=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run registered Level 1 sklearn Ridge models with LOSO OOF prediction.")
    parser.add_argument("--registry", default="configs/v11/level1_model_registry.yaml")
    parser.add_argument(
        "--ridge-backend",
        choices=["sklearn"],
        default="sklearn",
        help="Canonical Ridge backend. Only sklearn is supported.",
    )
    parser.add_argument(
        "--command-run",
        default=" ".join(sys.argv),
        help="Exact command string to record in OOF provenance.",
    )
    args = parser.parse_args()
    registry = load_registry(ROOT / args.registry)
    out_dir = ROOT / registry.get("output_dir", "outputs/v11_level1/reproduction")
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = [run_dataset(registry, spec, out_dir, args.ridge_backend, args.command_run) for spec in registry["datasets"]]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        raise SystemExit("[ERROR] no predictions generated")
    preds = pd.concat(frames, ignore_index=True, sort=False)
    preds.to_csv(out_dir / "oof_predictions_reproduction.csv", index=False)
    print(f"[OK] wrote {out_dir / 'oof_predictions_reproduction.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
