"""Run the B8.6e diagnostic spatial-closure engineered-feature probe.

Inputs:
    b86e_safe_engineered_feature_dataset.csv,
    b86e_safe_engineered_feature_catalog.csv, B8.6c feature-set registry, and
    B8.6d selected metrics from the B8.6e config.
Outputs:
    b86e_spatial_closure_probe_metrics.csv
Saved metrics:
    Diagnostic-only two-stage logistic-regression + ridge results for
    spatial_holdout, typology_holdout, and cell_group_holdout, comparing the
    B8.6d selected baseline to safe engineered feature variants. Coordinate and
    distance variants are explicitly labelled diagnostic-only.
"""

from __future__ import annotations

import argparse
import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from v12_b86e_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    finite_corr,
    forbidden_feature_name,
    full_safe_compact_columns,
    input_path,
    load_config,
    output_path,
    read_csv,
    top_fraction_overlap,
    write_csv,
)

warnings.filterwarnings("ignore", category=FutureWarning, module="sklearn")
warnings.filterwarnings("ignore", category=ConvergenceWarning)


@dataclass(frozen=True)
class ClosureProbeResult:
    """Spatial closure probe result."""

    status: str
    metric_rows: int
    best_status: str


def neutral_class(values: pd.Series, threshold: float) -> np.ndarray:
    """Map deltas to B8.6d neutral/cooling/other classes."""
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    labels = np.full(numeric.shape, "other_warming_or_weak_positive", dtype=object)
    labels[np.abs(numeric) <= threshold] = "neutral"
    labels[numeric < -threshold] = "meaningful_cooling"
    return labels


def one_hot_encoder() -> OneHotEncoder:
    """Create a version-compatible OneHotEncoder."""
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def split_features(frame: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Prepare numeric/categorical feature columns."""
    data = frame[features].copy()
    numeric: list[str] = []
    categorical: list[str] = []
    for column in features:
        converted = pd.to_numeric(data[column], errors="coerce")
        if converted.notna().sum() >= max(1, int(0.95 * data[column].notna().sum())):
            data[column] = converted
            numeric.append(column)
        else:
            data[column] = data[column].astype("string")
            categorical.append(column)
    return data, numeric, categorical


def make_preprocessor(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    """Build compact preprocessing for linear models."""
    transformers: list[tuple[str, Pipeline, list[str]]] = []
    if numeric:
        transformers.append(
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), numeric)
        )
    if categorical:
        transformers.append(
            (
                "cat",
                Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", one_hot_encoder())]),
                categorical,
            )
        )
    return ColumnTransformer(transformers=transformers, remainder="drop", sparse_threshold=0.0)


def validation_folds(dataset: pd.DataFrame, config: dict[str, Any]) -> list[tuple[str, str, str, pd.Index, pd.Index]]:
    """Create deterministic spatial, typology, and cell-group folds."""
    folds: list[tuple[str, str, str, pd.Index, pd.Index]] = []
    families = set(config["validation"]["split_families"])
    if "spatial_holdout" in families:
        cells = dataset.drop_duplicates("cell_id")[["cell_id", "centroid_x", "centroid_y"]].copy()
        x_mid = float(pd.to_numeric(cells["centroid_x"], errors="coerce").median())
        y_mid = float(pd.to_numeric(cells["centroid_y"], errors="coerce").median())
        cells["spatial_block"] = np.where(pd.to_numeric(cells["centroid_x"], errors="coerce") <= x_mid, "west", "east")
        cells["spatial_block"] += "_" + np.where(pd.to_numeric(cells["centroid_y"], errors="coerce") <= y_mid, "south", "north")
        for idx, block in enumerate(sorted(cells["spatial_block"].unique()), start=1):
            test_cells = set(cells.loc[cells["spatial_block"].eq(block), "cell_id"].astype(str))
            mask = dataset["cell_id"].astype(str).isin(test_cells)
            folds.append(("spatial_holdout", f"spatial_{block}", str(idx), dataset.index[~mask], dataset.index[mask]))
    if "typology_holdout" in families:
        min_test = int(config["validation"]["typology_min_test_cells"])
        min_train = int(config["validation"]["typology_min_train_cells"])
        typology_cells = dataset.drop_duplicates("cell_id")[["cell_id", "typology_label"]].dropna()
        fold_id = 1
        for typology in sorted(typology_cells["typology_label"].astype(str).unique()):
            test_cells = set(typology_cells.loc[typology_cells["typology_label"].astype(str).eq(typology), "cell_id"].astype(str))
            mask = dataset["cell_id"].astype(str).isin(test_cells)
            if len(test_cells) >= min_test and int(dataset.loc[~mask, "cell_id"].nunique()) >= min_train:
                folds.append(("typology_holdout", f"typology_{typology}", str(fold_id), dataset.index[~mask], dataset.index[mask]))
            fold_id += 1
    if "cell_group_holdout" in families:
        cells = np.array(sorted(dataset["cell_id"].astype(str).unique()))
        rng = np.random.default_rng(int(config["random_seed"]))
        rng.shuffle(cells)
        for idx, test_cells in enumerate(np.array_split(cells, int(config["validation"]["cell_group_folds"])), start=1):
            mask = dataset["cell_id"].astype(str).isin(set(test_cells.tolist()))
            folds.append(("cell_group_holdout", "cell_group_5fold", str(idx), dataset.index[~mask], dataset.index[mask]))
    return folds


def variant_features(config: dict[str, Any], dataset: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Return feature variants for the diagnostic probe."""
    base = full_safe_compact_columns(config, dataset, include_coordinate=False)
    engineered = read_csv(output_path(config, "safe_engineered_feature_catalog"))
    physical = [
        column
        for column in engineered.loc[engineered["feature_role"].astype(str).eq("safe_physical"), "feature_name"].astype(str)
        if column in dataset.columns
    ]
    distance = [
        column
        for column in engineered.loc[engineered["feature_role"].astype(str).eq("distance_diagnostic"), "feature_name"].astype(str)
        if column in dataset.columns
    ]
    coordinate = [
        column
        for column in engineered.loc[engineered["feature_role"].astype(str).eq("coordinate_diagnostic"), "feature_name"].astype(str)
        if column in dataset.columns
    ]
    variants = {
        "b86e_refit_full_safe_compact": {
            "features": base,
            "feature_variant_status": "BASELINE_REFIT",
            "coordinate_dependent": False,
            "distance_dependent": False,
        },
        "safe_physical_engineered": {
            "features": list(dict.fromkeys(base + physical)),
            "feature_variant_status": "SAFE_PHYSICAL_DIAGNOSTIC",
            "coordinate_dependent": False,
            "distance_dependent": False,
        },
        "safe_physical_plus_distance_diagnostic": {
            "features": list(dict.fromkeys(base + physical + distance)),
            "feature_variant_status": "DIAGNOSTIC_ONLY_DISTANCE_DEPENDENT",
            "coordinate_dependent": False,
            "distance_dependent": True,
        },
        "coordinate_context_diagnostic": {
            "features": list(dict.fromkeys(base + physical + coordinate)),
            "feature_variant_status": "DIAGNOSTIC_ONLY_COORDINATE_DEPENDENT",
            "coordinate_dependent": True,
            "distance_dependent": False,
        },
    }
    for variant in variants.values():
        variant["features"] = [
            column
            for column in variant["features"]
            if column in dataset.columns
            and (column.startswith("b86e__centroid_") or not forbidden_feature_name(column, config, include_coordinate=False))
        ]
    return variants


def run_fold(train: pd.DataFrame, test: pd.DataFrame, features: list[str], config: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    """Fit the selected two-stage diagnostic workflow and return true/pred arrays."""
    threshold = float(config["neutral_threshold_c"])
    target = str(config["primary_target"])
    train_x, numeric, categorical = split_features(train, features)
    test_x, _, _ = split_features(test, features)
    preprocessor = make_preprocessor(numeric, categorical)
    classifier = Pipeline(
        [
            ("prep", preprocessor),
            ("model", LogisticRegression(max_iter=1000, solver="liblinear", multi_class="ovr")),
        ]
    )
    y_class = neutral_class(train[target], threshold)
    if len(set(y_class)) <= 1:
        pred_class = np.full(len(test), y_class[0], dtype=object)
    else:
        classifier.fit(train_x, y_class)
        pred_class = classifier.predict(test_x)
    cooling_train = train.loc[pd.to_numeric(train[target], errors="coerce") < -threshold].copy()
    if len(cooling_train) < 5:
        stage2_pred = np.zeros(len(test), dtype=float)
    else:
        cool_x, cool_num, cool_cat = split_features(cooling_train, features)
        regressor = Pipeline([("prep", make_preprocessor(cool_num, cool_cat)), ("model", Ridge(alpha=1.0))])
        regressor.fit(cool_x, pd.to_numeric(cooling_train[target], errors="coerce"))
        stage2_pred = regressor.predict(test_x)
    combined = np.where(pred_class == "meaningful_cooling", stage2_pred, 0.0)
    y_true = pd.to_numeric(test[target], errors="coerce").to_numpy(dtype=float)
    return y_true, combined


def metric_row(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, config: dict[str, Any]) -> dict[str, Any]:
    """Compute probe metrics for one fold."""
    threshold = float(config["neutral_threshold_c"])
    pred_class = np.where(y_pred < -threshold, "meaningful_cooling", "neutral")
    true_class = neutral_class(pd.Series(y_true), threshold)
    neutral_mask = true_class == "neutral"
    cooling_mask = true_class == "meaningful_cooling"
    anchors = set(config["anchor_cells"])
    anchor_mask = test["cell_id"].astype(str).isin(anchors).to_numpy()
    frame = test[["cell_id"]].copy()
    frame["true"] = y_true
    frame["pred"] = y_pred
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "Spearman": finite_corr(y_true, y_pred, "spearman"),
        "top10pct_overlap": top_fraction_overlap(frame, "true", "pred", 0.10),
        "neutral_accuracy": float(accuracy_score(neutral_mask, pred_class == "neutral")),
        "false_promotion_rate": float(np.mean(pred_class[neutral_mask] == "meaningful_cooling")) if int(neutral_mask.sum()) else float("nan"),
        "false_neutral_rate": float(np.mean(pred_class[cooling_mask] == "neutral")) if int(cooling_mask.sum()) else float("nan"),
        "anchor_MAE": float(np.mean(np.abs(y_pred[anchor_mask] - y_true[anchor_mask]))) if int(anchor_mask.sum()) else float("nan"),
    }


def aggregate_probe_metrics(rows: list[dict[str, Any]], config: dict[str, Any]) -> pd.DataFrame:
    """Aggregate fold rows and add variant decision labels."""
    fold_metrics = pd.DataFrame(rows)
    grouped = (
        fold_metrics.groupby(["feature_variant", "split_family"], dropna=False)
        .agg(
            n_folds=("MAE", "size"),
            MAE=("MAE", "mean"),
            Spearman=("Spearman", "mean"),
            top10pct_overlap=("top10pct_overlap", "mean"),
            neutral_accuracy=("neutral_accuracy", "mean"),
            false_promotion_rate=("false_promotion_rate", "mean"),
            false_neutral_rate=("false_neutral_rate", "mean"),
            anchor_MAE=("anchor_MAE", "mean"),
            feature_count=("feature_count", "max"),
            coordinate_dependent=("coordinate_dependent", "max"),
            distance_dependent=("distance_dependent", "max"),
        )
        .reset_index()
    )
    baseline = read_csv(input_path(config, "b86d_combined_metrics_path"))
    selected = config["selected_workflow"]
    for column, value in [
        ("feature_set", selected["feature_set"]),
        ("classifier", selected["classifier"]),
        ("regressor", selected["regressor"]),
    ]:
        baseline = baseline.loc[baseline[column].astype(str).eq(str(value))]
    baseline = baseline.loc[pd.to_numeric(baseline["neutral_threshold_c"], errors="coerce").eq(float(selected["neutral_threshold_c"]))]
    baseline_rows = (
        baseline.loc[baseline["split_family"].isin(config["validation"]["split_families"])]
        .groupby("split_family", dropna=False)
        .agg(
            n_folds=("MAE", "size"),
            MAE=("MAE", "mean"),
            Spearman=("Spearman_observed_vs_predicted", "mean"),
            top10pct_overlap=("top10pct_overlap", "mean"),
            neutral_accuracy=("accuracy", "mean"),
            false_promotion_rate=("false_promotion_rate", "mean"),
            false_neutral_rate=("false_neutral_rate", "mean"),
            anchor_MAE=("robust_anchor_MAE", "mean"),
        )
        .reset_index()
    )
    baseline_rows.insert(0, "feature_variant", "b86d_selected_existing_oof")
    baseline_rows["feature_count"] = np.nan
    baseline_rows["coordinate_dependent"] = False
    baseline_rows["distance_dependent"] = False
    out = pd.concat([baseline_rows, grouped], ignore_index=True, sort=False)
    baseline_map = baseline_rows.set_index("split_family")
    out["Spearman_delta_vs_b86d"] = out.apply(
        lambda row: row["Spearman"] - baseline_map.loc[row["split_family"], "Spearman"]
        if row["split_family"] in baseline_map.index
        else np.nan,
        axis=1,
    )
    out["top10_delta_vs_b86d"] = out.apply(
        lambda row: row["top10pct_overlap"] - baseline_map.loc[row["split_family"], "top10pct_overlap"]
        if row["split_family"] in baseline_map.index
        else np.nan,
        axis=1,
    )
    out["variant_decision"] = "DIAGNOSTIC_ONLY"
    mask_safe = out["feature_variant"].eq("safe_physical_engineered")
    promising = mask_safe & out["split_family"].isin(["spatial_holdout", "typology_holdout"]) & (
        (out["Spearman_delta_vs_b86d"] >= 0.03) | (out["top10_delta_vs_b86d"] >= 0.03)
    )
    out.loc[promising, "variant_decision"] = "FEATURE_UPGRADE_PROMISING"
    out.loc[out["coordinate_dependent"].astype(bool), "variant_decision"] = "DIAGNOSTIC_ONLY_COORDINATE_DEPENDENT"
    out.loc[out["distance_dependent"].astype(bool), "variant_decision"] = "DIAGNOSTIC_ONLY_DISTANCE_DEPENDENT"
    out.loc[out["feature_variant"].eq("b86d_selected_existing_oof"), "variant_decision"] = "B86D_SELECTED_BASELINE"
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out.sort_values(["split_family", "feature_variant"])


def run(config_path: Path = DEFAULT_CONFIG) -> ClosureProbeResult:
    """Run the diagnostic engineered-feature closure probe."""
    config = load_config(config_path)
    dataset = read_csv(output_path(config, "safe_engineered_feature_dataset"))
    folds = validation_folds(dataset, config)
    variants = variant_features(config, dataset)
    rows: list[dict[str, Any]] = []
    for variant_name, spec in variants.items():
        features = spec["features"]
        if not features:
            continue
        for split_family, split_name, fold_id, train_idx, test_idx in folds:
            train = dataset.loc[train_idx].copy()
            test = dataset.loc[test_idx].copy()
            y_true, y_pred = run_fold(train, test, features, config)
            row = {
                "feature_variant": variant_name,
                "split_family": split_family,
                "split_name": split_name,
                "fold_id": fold_id,
                "feature_count": len(features),
                "coordinate_dependent": bool(spec["coordinate_dependent"]),
                "distance_dependent": bool(spec["distance_dependent"]),
                "feature_variant_status": spec["feature_variant_status"],
            }
            row.update(metric_row(test, y_true, y_pred, config))
            rows.append(row)
    metrics = aggregate_probe_metrics(rows, config)
    write_csv(metrics, output_path(config, "spatial_closure_probe_metrics"))
    best_status = (
        "FEATURE_UPGRADE_PROMISING"
        if metrics["variant_decision"].astype(str).eq("FEATURE_UPGRADE_PROMISING").any()
        else "DIAGNOSTIC_ONLY"
    )
    return ClosureProbeResult(status="B86E_SPATIAL_CLOSURE_PROBE_READY", metric_rows=len(metrics), best_status=best_status)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run the B8.6e diagnostic spatial-closure engineered-feature probe.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
