"""Common utilities for B8.6d two-stage surrogate validation.

Inputs:
    configs/v12/systemb_b86d_two_stage_surrogate.yaml
    Compact B8.6c/B8.5 CSV inputs referenced by the config.
Outputs:
    Shared helpers only; this module writes no files directly except through
    helper functions called by lane scripts.
Saved metrics:
    None directly. Metrics are produced by the stage and report scripts.
"""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yaml
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.exceptions import ConvergenceWarning


warnings.filterwarnings("ignore", category=FutureWarning, module="sklearn")
warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", message="y_pred contains classes not in y_true")
warnings.filterwarnings("ignore", message=".*physical cores.*")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "v12" / "systemb_b86d_two_stage_surrogate.yaml"
CLAIM_BOUNDARY = (
    "SOLWEIG-derived compact Tmrt-delta surrogate diagnostic only; not WBGT, risk, "
    "observed truth, causal feature importance, B9, AOI-wide prediction, or System A/B coupling."
)
CLASS_LABELS = ["neutral", "meaningful_cooling", "other_warming_or_weak_positive"]
SUPPORTING_WEAK_SPLITS = ["cell_group_holdout", "spatial_holdout", "typology_holdout"]


@dataclass(frozen=True)
class Fold:
    """Deterministic validation fold metadata."""

    split_family: str
    split_name: str
    fold_id: str
    train_index: pd.Index
    test_index: pd.Index


def repo_path(path: str | Path) -> Path:
    """Resolve a project-relative path."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def load_config(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load the B8.6d YAML config."""
    with repo_path(config_path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def output_path(config: dict[str, Any], key: str) -> Path:
    """Resolve an output path by config key."""
    return repo_path(config["outputs"][key])


def ensure_output_dir(config: dict[str, Any]) -> Path:
    """Create the B8.6d compact output directory."""
    out_dir = output_path(config, "out_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def read_csv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read a UTF-8 CSV from the project tree."""
    return pd.read_csv(repo_path(path), **kwargs)


def write_csv(frame: pd.DataFrame, path: str | Path) -> None:
    """Write a CSV with stable parent creation."""
    destination = repo_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, encoding="utf-8")


def write_text(text: str, path: str | Path) -> None:
    """Write UTF-8 text with stable parent creation."""
    destination = repo_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="\n")


def parse_pipe_list(value: Any) -> list[str]:
    """Parse a B8.6 feature registry pipe-delimited column list."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [part for part in str(value).split("|") if part]


def bool_series(series: pd.Series) -> pd.Series:
    """Coerce common boolean-like values to bool."""
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.lower().isin({"true", "1", "yes", "y"})


def forbidden_predictor(column: str, config: dict[str, Any]) -> bool:
    """Return True if a column violates the B8.6d predictor contract."""
    contract = config["feature_contract"]
    name = column.lower()
    if name in {str(col).lower() for col in contract.get("forbidden_predictor_columns", [])}:
        return True
    allowed_categorical = {str(col).lower() for col in contract.get("allowed_categorical_features", [])}
    if name in allowed_categorical:
        return False
    if name == "hour_sgt":
        return False
    return any(token in name for token in contract.get("forbidden_predictor_tokens", []))


def feature_columns_for_set(registry: pd.DataFrame, dataset: pd.DataFrame, feature_set: str, config: dict[str, Any]) -> list[str]:
    """Return available, non-forbidden feature columns for one feature set."""
    row = registry.loc[registry["feature_set"].astype(str) == feature_set]
    if row.empty:
        return []
    column_field = "feature_columns" if "feature_columns" in registry.columns else "available_feature_columns"
    columns = parse_pipe_list(row.iloc[0][column_field])
    available: list[str] = []
    for column in columns:
        if column in dataset.columns and not forbidden_predictor(column, config):
            available.append(column)
    return list(dict.fromkeys(available))


def coerce_feature_frame(dataset: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Split selected features into numeric and categorical columns."""
    frame = dataset[features].copy()
    numeric: list[str] = []
    categorical: list[str] = []
    for column in features:
        if pd.api.types.is_numeric_dtype(frame[column]):
            numeric.append(column)
        else:
            converted = pd.to_numeric(frame[column], errors="coerce")
            if converted.notna().sum() >= max(1, int(0.95 * frame[column].notna().sum())):
                frame[column] = converted
                numeric.append(column)
            else:
                frame[column] = frame[column].astype("string")
                categorical.append(column)
    return frame, numeric, categorical


def one_hot_encoder() -> OneHotEncoder:
    """Create a version-compatible one-hot encoder."""
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def make_preprocessor(model_name: str, numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    """Build preprocessing for compact numeric/categorical features."""
    transformers: list[tuple[str, Pipeline, list[str]]] = []
    if numeric:
        steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
        if model_name in {"ridge", "elasticnet", "logistic_regression", "balanced_logistic_regression"}:
            steps.append(("scaler", StandardScaler()))
        transformers.append(("num", Pipeline(steps), numeric))
    if categorical:
        transformers.append(
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", one_hot_encoder()),
                    ]
                ),
                categorical,
            )
        )
    return ColumnTransformer(transformers=transformers, remainder="drop", sparse_threshold=0.0)


def make_pipeline(model_name: str, estimator: Any, numeric: list[str], categorical: list[str]) -> Pipeline:
    """Create a preprocessing + estimator pipeline."""
    return Pipeline([("prep", make_preprocessor(model_name, numeric, categorical)), ("model", clone(estimator))])


def classifier_models(config: dict[str, Any], seed: int | None = None) -> dict[str, Any]:
    """Configured stage-1 classifiers."""
    seed_value = int(config["random_seed"] if seed is None else seed)
    specs = config["models"]
    return {
        "logistic_regression": LogisticRegression(
            max_iter=int(specs["logistic_regression"]["max_iter"]),
            solver="liblinear",
            multi_class="ovr",
        ),
        "balanced_logistic_regression": LogisticRegression(
            max_iter=int(specs["balanced_logistic_regression"]["max_iter"]),
            class_weight=specs["balanced_logistic_regression"].get("class_weight", "balanced"),
            solver="liblinear",
            multi_class="ovr",
        ),
        "random_forest_classifier": RandomForestClassifier(
            n_estimators=int(specs["random_forest_classifier"]["n_estimators"]),
            max_depth=int(specs["random_forest_classifier"]["max_depth"]),
            min_samples_leaf=int(specs["random_forest_classifier"]["min_samples_leaf"]),
            random_state=seed_value,
            n_jobs=-1,
            class_weight="balanced_subsample",
        ),
        "hist_gradient_boosting_classifier": HistGradientBoostingClassifier(
            max_iter=int(specs["hist_gradient_boosting_classifier"]["max_iter"]),
            learning_rate=float(specs["hist_gradient_boosting_classifier"]["learning_rate"]),
            max_leaf_nodes=int(specs["hist_gradient_boosting_classifier"]["max_leaf_nodes"]),
            random_state=seed_value,
        ),
    }


def regressor_models(config: dict[str, Any], seed: int | None = None) -> dict[str, Any]:
    """Configured stage-2 regressors."""
    seed_value = int(config["random_seed"] if seed is None else seed)
    specs = config["models"]
    return {
        "ridge": Ridge(alpha=float(specs["ridge"]["alpha"])),
        "elasticnet": ElasticNet(
            alpha=float(specs["elasticnet"]["alpha"]),
            l1_ratio=float(specs["elasticnet"]["l1_ratio"]),
            random_state=seed_value,
            max_iter=10000,
        ),
        "random_forest_regressor": RandomForestRegressor(
            n_estimators=int(specs["random_forest_regressor"]["n_estimators"]),
            max_depth=int(specs["random_forest_regressor"]["max_depth"]),
            min_samples_leaf=int(specs["random_forest_regressor"]["min_samples_leaf"]),
            random_state=seed_value,
            n_jobs=-1,
        ),
        "hist_gradient_boosting_regressor": HistGradientBoostingRegressor(
            max_iter=int(specs["hist_gradient_boosting_regressor"]["max_iter"]),
            learning_rate=float(specs["hist_gradient_boosting_regressor"]["learning_rate"]),
            max_leaf_nodes=int(specs["hist_gradient_boosting_regressor"]["max_leaf_nodes"]),
            random_state=seed_value,
        ),
    }


def neutral_class(y: pd.Series | np.ndarray, threshold: float) -> np.ndarray:
    """Map primary deltas to neutral/cooling/other classes."""
    values = np.asarray(y, dtype=float)
    labels = np.full(values.shape, "other_warming_or_weak_positive", dtype=object)
    labels[np.abs(values) <= threshold] = "neutral"
    labels[values < -threshold] = "meaningful_cooling"
    return labels


def finite_corr(y_true: np.ndarray, y_pred: np.ndarray, method: str) -> float:
    """Compute Pearson or Spearman when the inputs are non-degenerate."""
    frame = pd.DataFrame({"true": y_true, "pred": y_pred}).dropna()
    if len(frame) < 2 or frame["true"].nunique() <= 1 or frame["pred"].nunique() <= 1:
        return float("nan")
    left = frame["true"].to_numpy(dtype=float)
    right = frame["pred"].to_numpy(dtype=float)
    if method == "spearman":
        left = pd.Series(left).rank(method="average").to_numpy(dtype=float)
        right = pd.Series(right).rank(method="average").to_numpy(dtype=float)
    left = left - float(np.mean(left))
    right = right - float(np.mean(right))
    denom = math.sqrt(float(np.sum(left * left)) * float(np.sum(right * right)))
    return float(np.sum(left * right) / denom) if denom else float("nan")


def cell_average_frame(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:
    """Return per-cell mean true/predicted delta for ranking diagnostics."""
    frame = test[["cell_id"]].copy()
    frame["y_true"] = y_true
    frame["y_pred"] = y_pred
    return frame.groupby("cell_id", as_index=False)[["y_true", "y_pred"]].mean(numeric_only=True)


def top_overlap(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, k: int) -> float:
    """Compute overlap among the most negative true/predicted cell deltas."""
    by_cell = cell_average_frame(test, y_true, y_pred)
    if by_cell.empty:
        return float("nan")
    k = min(max(1, k), len(by_cell))
    true_top = set(by_cell.nsmallest(k, "y_true")["cell_id"].astype(str))
    pred_top = set(by_cell.nsmallest(k, "y_pred")["cell_id"].astype(str))
    return float(len(true_top & pred_top) / k)


def top_fraction_overlap(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, fraction: float) -> float:
    """Compute top cooling overlap at a cell fraction."""
    return top_overlap(test, y_true, y_pred, max(1, int(math.ceil(fraction * int(test["cell_id"].nunique())))))


def regression_metrics(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, threshold: float) -> dict[str, float]:
    """Compute compact surrogate regression/ranking metrics."""
    if len(y_true) == 0:
        return {
            "MAE": float("nan"),
            "RMSE": float("nan"),
            "R2": float("nan"),
            "Spearman_observed_vs_predicted": float("nan"),
            "Pearson_observed_vs_predicted": float("nan"),
            "bias": float("nan"),
            "p90_abs_error": float("nan"),
            "sign_accuracy": float("nan"),
            "top5_overlap": float("nan"),
            "top10pct_overlap": float("nan"),
            "top20pct_overlap": float("nan"),
        }
    err = np.asarray(y_pred, dtype=float) - np.asarray(y_true, dtype=float)
    sign_true = np.asarray(y_true, dtype=float) < -threshold
    sign_pred = np.asarray(y_pred, dtype=float) < -threshold
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)) if len(np.unique(y_true)) > 1 else float("nan"),
        "Spearman_observed_vs_predicted": finite_corr(y_true, y_pred, "spearman"),
        "Pearson_observed_vs_predicted": finite_corr(y_true, y_pred, "pearson"),
        "bias": float(np.mean(err)),
        "p90_abs_error": float(np.quantile(np.abs(err), 0.90)),
        "sign_accuracy": float(np.mean(sign_true == sign_pred)),
        "top5_overlap": top_overlap(test, y_true, y_pred, 5),
        "top10pct_overlap": top_fraction_overlap(test, y_true, y_pred, 0.10),
        "top20pct_overlap": top_fraction_overlap(test, y_true, y_pred, 0.20),
    }


def role_error_and_rank(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, cells: Iterable[str]) -> tuple[float, float]:
    """Compute MAE and mean rank error for a diagnostic cell list."""
    by_cell = cell_average_frame(test, y_true, y_pred)
    if by_cell.empty:
        return float("nan"), float("nan")
    role_cells = set(map(str, cells))
    subset = by_cell.loc[by_cell["cell_id"].astype(str).isin(role_cells)].copy()
    if subset.empty:
        return float("nan"), float("nan")
    by_cell["true_rank"] = by_cell["y_true"].rank(method="min", ascending=True)
    by_cell["pred_rank"] = by_cell["y_pred"].rank(method="min", ascending=True)
    subset = by_cell.loc[by_cell["cell_id"].astype(str).isin(role_cells)].copy()
    mae = float((subset["y_pred"] - subset["y_true"]).abs().mean())
    rank_error = float((subset["pred_rank"] - subset["true_rank"]).abs().mean())
    return mae, rank_error


def h10_metrics(test: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray, config: dict[str, Any], threshold: float) -> dict[str, float]:
    """Compute h10 and core-hour metrics separately."""
    hour = int(config["diagnostic_cells"]["h10_caveat_hour"])
    hour_values = pd.to_numeric(test["hour_sgt"], errors="coerce")
    h10_mask = hour_values == hour
    core_mask = ~h10_mask
    out: dict[str, float] = {}
    for label, mask in [("h10", h10_mask), ("core_hour_excluding_h10", core_mask)]:
        if int(mask.sum()) < 2:
            out[f"{label}_MAE"] = float("nan")
            out[f"{label}_Spearman"] = float("nan")
            out[f"{label}_top10pct_overlap"] = float("nan")
            continue
        subset = test.loc[mask]
        metrics = regression_metrics(subset, np.asarray(y_true)[mask.to_numpy()], np.asarray(y_pred)[mask.to_numpy()], threshold)
        out[f"{label}_MAE"] = metrics["MAE"]
        out[f"{label}_Spearman"] = metrics["Spearman_observed_vs_predicted"]
        out[f"{label}_top10pct_overlap"] = metrics["top10pct_overlap"]
    return out


def classification_metrics(y_true_class: np.ndarray, y_pred_class: np.ndarray) -> dict[str, float | str]:
    """Compute B8.6d neutral-boundary classification metrics."""
    present_labels = [label for label in CLASS_LABELS if label in set(y_true_class) or label in set(y_pred_class)]
    out: dict[str, float | str] = {
        "accuracy": float(accuracy_score(y_true_class, y_pred_class)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true_class, y_pred_class)),
    }
    for label in ["neutral", "meaningful_cooling"]:
        out[f"precision_{label}"] = float(
            precision_score(y_true_class, y_pred_class, labels=[label], average="macro", zero_division=0)
        )
        out[f"recall_{label}"] = float(
            recall_score(y_true_class, y_pred_class, labels=[label], average="macro", zero_division=0)
        )
    true_neutral = y_true_class == "neutral"
    true_cooling = y_true_class == "meaningful_cooling"
    out["false_promotion_rate"] = (
        float(np.mean(y_pred_class[true_neutral] == "meaningful_cooling")) if int(true_neutral.sum()) else float("nan")
    )
    out["false_neutral_rate"] = (
        float(np.mean(y_pred_class[true_cooling] == "neutral")) if int(true_cooling.sum()) else float("nan")
    )
    out["true_neutral_count"] = int(true_neutral.sum())
    out["true_meaningful_cooling_count"] = int(true_cooling.sum())
    out["true_other_warming_or_weak_positive_count"] = int((y_true_class == "other_warming_or_weak_positive").sum())
    confusion = {
        true_label: {
            pred_label: int(((y_true_class == true_label) & (y_pred_class == pred_label)).sum())
            for pred_label in CLASS_LABELS
        }
        for true_label in CLASS_LABELS
    }
    out["confusion_matrix_json"] = json.dumps(confusion, sort_keys=True)
    out["present_labels"] = "|".join(present_labels)
    return out


def validation_folds(dataset: pd.DataFrame, config: dict[str, Any]) -> list[Fold]:
    """Create deterministic non-random validation folds."""
    folds: list[Fold] = []
    families = set(config["split_families"])
    if "forcing_day_holdout" in families:
        for idx, forcing_day in enumerate(sorted(dataset["forcing_day_id"].astype(str).unique()), start=1):
            mask = dataset["forcing_day_id"].astype(str) == forcing_day
            folds.append(Fold("forcing_day_holdout", f"holdout_{forcing_day}", str(idx), dataset.index[~mask], dataset.index[mask]))

    if "cell_group_holdout" in families:
        cells = np.array(sorted(dataset["cell_id"].astype(str).unique()))
        rng = np.random.default_rng(int(config["random_seed"]))
        rng.shuffle(cells)
        for idx, test_cells in enumerate(np.array_split(cells, int(config["validation"]["cell_group_folds"])), start=1):
            mask = dataset["cell_id"].astype(str).isin(set(test_cells.tolist()))
            folds.append(Fold("cell_group_holdout", "cell_group_5fold", str(idx), dataset.index[~mask], dataset.index[mask]))

    if "spatial_holdout" in families:
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
            folds.append(Fold("spatial_holdout", f"spatial_{block}", str(idx), dataset.index[~mask], dataset.index[mask]))

    if "typology_holdout" in families:
        min_test = int(config["validation"]["typology_min_test_cells"])
        min_train = int(config["validation"]["typology_min_train_cells"])
        typology_cells = dataset.drop_duplicates("cell_id")[["cell_id", "typology_label"]].dropna()
        fold_id = 1
        for typology in sorted(typology_cells["typology_label"].astype(str).unique()):
            test_cells = set(typology_cells.loc[typology_cells["typology_label"].astype(str) == typology, "cell_id"].astype(str))
            mask = dataset["cell_id"].astype(str).isin(test_cells)
            if len(test_cells) >= min_test and int(dataset.loc[~mask, "cell_id"].nunique()) >= min_train:
                folds.append(Fold("typology_holdout", f"typology_{typology}", str(fold_id), dataset.index[~mask], dataset.index[mask]))
            fold_id += 1

    if "hour_holdout" in families:
        hours = sorted(pd.to_numeric(dataset["hour_sgt"], errors="coerce").dropna().astype(int).unique())
        for idx, hour in enumerate(hours, start=1):
            mask = pd.to_numeric(dataset["hour_sgt"], errors="coerce") == hour
            folds.append(Fold("hour_holdout", f"leave_h{hour}_out", str(idx), dataset.index[~mask], dataset.index[mask]))

    if bool(config["validation"].get("random_split_diagnostic", False)):
        rng = np.random.default_rng(int(config["random_seed"]))
        mask = pd.Series(rng.random(len(dataset)) < float(config["validation"]["random_test_fraction"]), index=dataset.index)
        folds.append(Fold("random_split", "random_row_diagnostic", "1", dataset.index[~mask], dataset.index[mask]))
    return folds


def fold_inventory(dataset: pd.DataFrame, folds: list[Fold]) -> pd.DataFrame:
    """Return fold-level inventory rows."""
    rows: list[dict[str, Any]] = []
    for fold in folds:
        train = dataset.loc[fold.train_index]
        test = dataset.loc[fold.test_index]
        rows.append(
            {
                "split_family": fold.split_family,
                "split_name": fold.split_name,
                "fold_id": fold.fold_id,
                "n_train": len(train),
                "n_test": len(test),
                "n_train_cells": int(train["cell_id"].nunique()),
                "n_test_cells": int(test["cell_id"].nunique()),
                "n_train_forcing_days": int(train["forcing_day_id"].nunique()),
                "n_test_forcing_days": int(test["forcing_day_id"].nunique()),
                "n_train_hours": int(train["hour_sgt"].nunique()),
                "n_test_hours": int(test["hour_sgt"].nunique()),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def aggregate_metrics(frame: pd.DataFrame, group_cols: list[str], metric_cols: list[str]) -> pd.DataFrame:
    """Aggregate metric columns by mean with fold counts."""
    if frame.empty:
        return pd.DataFrame(columns=group_cols + ["n_folds"] + metric_cols)
    grouped = frame.groupby(group_cols, dropna=False)
    out = grouped[metric_cols].mean(numeric_only=True).reset_index()
    out.insert(len(group_cols), "n_folds", grouped.size().to_numpy())
    return out


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 12) -> str:
    """Format a compact Markdown table."""
    if frame.empty:
        return "_No rows._"
    view = frame.loc[:, [col for col in columns if col in frame.columns]].head(max_rows).copy()
    for column in view.select_dtypes(include=[float]).columns:
        view[column] = view[column].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    return view.to_markdown(index=False)


def now_stamp() -> str:
    """Return a stable local timestamp string."""
    return pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
