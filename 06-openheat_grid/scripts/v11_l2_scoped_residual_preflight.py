#!/usr/bin/env python
"""System A A-L2.1c scoped station-level residual preflight model.

Inputs:
    - configs/v11/systema_l2_scoped_residual_preflight.yaml
    - A-L2.0 station residual, probability-error, and stability CSVs.
    - A-L2.1a-S1 station buffer feature wide CSV.
    - A-L2.1b station feature candidate and association-screen CSVs.

Outputs:
    - l2_scoped_model_input_table.csv
    - l2_scoped_feature_sets.csv
    - l2_scoped_null_baseline_metrics.csv
    - l2_scoped_one_feature_metrics.csv
    - l2_scoped_ridge_metrics.csv
    - l2_scoped_elasticnet_metrics.csv
    - l2_scoped_permutation_null.csv
    - l2_scoped_bootstrap_stability.csv
    - l2_scoped_predictions_loo.csv
    - l2_scoped_station_diagnostics.csv
    - l2_scoped_decision_matrix.csv
    - l2_scoped_residual_preflight_report.md
    - A_L2_1C_STATUS.md
    - docs/v11/OpenHeat_SystemA_L2_scoped_residual_preflight_CN.md

Saved metrics:
    - Station-level n, target attrition, low-support flags, feature
      missingness flags, feature-set definitions, nested leave-one-station-out
      null/one-feature/Ridge/ElasticNet metrics, selected hyperparameter
      summaries, fixed-hyperparameter permutation-null summaries, bootstrap
      coefficient sign/selection stability, S142/S139 diagnostics, and a
      scoped A-L2.2 decision matrix.

Scope guard:
    This preflight never models official WBGT directly, never uses hourly rows
    as independent observations, never uses station_id as a predictive feature,
    never creates station-adjusted WBGT or local 100 m WBGT, never uses System B
    or SOLWEIG/Tmrt features, never touches archive collector paths, and never
    claims station-context causal correction.
"""
from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_OUTPUT_PREFIX = "outputs/v11_systema_l2_residual/scoped_residual_preflight"
CN_DOC_NAME = "docs/v11/OpenHeat_SystemA_L2_scoped_residual_preflight_CN.md"
NULL_FEATURE_SET_ID = "null_baseline"
S142 = "S142"
S139 = "S139"


@dataclass(frozen=True)
class FeatureSet:
    """A station-context feature set used by this preflight."""

    feature_set_id: str
    feature_set_role: str
    features: list[str]
    decision_eligible: bool
    notes: str


@dataclass(frozen=True)
class ScopedPreflightResult:
    """Headline result returned to the runner."""

    decision_status: str
    n_stations_used: str
    best_models_by_target: str
    null_baseline_comparison: str
    permutation_bootstrap_headline: str
    s142_s139_caveats: str
    a_l2_2_recommendation: str
    files_created: list[Path]
    git_status_short: str


@dataclass(frozen=True)
class StandardizedLinearFit:
    """Fitted standardized linear model used for fast station-level resampling."""

    medians: np.ndarray
    means: np.ndarray
    scales: np.ndarray
    y_mean: float
    coef: np.ndarray


def rel(path: Path) -> str:
    """Return a project-relative path when possible."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(raw_path: str) -> Path:
    """Resolve an absolute or project-relative path."""
    path = Path(raw_path)
    return path if path.is_absolute() else ROOT / path


def load_config(path: Path) -> dict[str, Any]:
    """Load the explicit JSON-formatted YAML config."""
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Config is not a mapping: {rel(path)}")
    return loaded


def input_paths(config: dict[str, Any]) -> dict[str, Path]:
    """Resolve configured input paths."""
    return {key: resolve_path(str(value)) for key, value in config["inputs"].items()}


def output_paths(config: dict[str, Any]) -> dict[str, Path]:
    """Resolve configured outputs and enforce this lane's write scope."""
    output_dir = resolve_path(str(config["outputs"]["output_dir"]))
    cn_doc = resolve_path(str(config["outputs"]["cn_doc"]))
    if not rel(output_dir).startswith(EXPECTED_OUTPUT_PREFIX):
        raise ValueError(f"Refusing to write outside {EXPECTED_OUTPUT_PREFIX}: {rel(output_dir)}")
    if rel(cn_doc) != CN_DOC_NAME:
        raise ValueError(f"Refusing to write unexpected CN doc path: {rel(cn_doc)}")
    outputs = {"dir": output_dir, "cn_doc": cn_doc}
    for key, value in config["outputs"].items():
        if key in {"output_dir", "cn_doc"}:
            continue
        outputs[key] = output_dir / str(value)
    return outputs


def read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV while keeping station ids as strings."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input: {rel(path)}")
    return pd.read_csv(path, dtype={"station_id": "string"})


def git_branch() -> str:
    """Return the active git branch when available."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def git_status_short() -> str:
    """Return git status for this project subdirectory."""
    result = subprocess.run(
        ["git", "status", "--short", "--", "."],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.rstrip()


def semicolon(values: Iterable[Any]) -> str:
    """Join unique non-empty values in first-seen order."""
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() != "nan" and text not in seen:
            out.append(text)
            seen.add(text)
    return ";".join(out)


def fmt(value: object, digits: int = 6) -> str:
    """Format numeric values for compact CSV/Markdown output."""
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        text = str(value)
        return "" if text.lower() == "nan" else text
    if not math.isfinite(number):
        return ""
    if abs(number) < 0.5 * 10 ** (-digits):
        number = 0.0
    return f"{number:.{digits}f}"


def bool_value(value: object) -> bool:
    """Parse bool-like config/CSV values."""
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y"}


def markdown_table(df: pd.DataFrame, columns: list[str], limit: int = 12) -> str:
    """Render a compact Markdown table."""
    if df.empty:
        return "_No rows._"
    shown = df.loc[:, [col for col in columns if col in df.columns]].head(limit).copy()
    for col in shown.columns:
        if pd.api.types.is_numeric_dtype(shown[col]):
            shown[col] = shown[col].map(lambda value: fmt(value, 6))
        else:
            shown[col] = shown[col].fillna("").astype(str)
    lines = ["| " + " | ".join(shown.columns) + " |", "| " + " | ".join(["---"] * len(shown.columns)) + " |"]
    for _, row in shown.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in shown.columns) + " |")
    if len(df) > limit:
        lines.append("")
        lines.append(f"_Showing {limit} of {len(df)} rows._")
    return "\n".join(lines)


def replace_feature(features: Sequence[str], remove: str, add: str) -> list[str]:
    """Return a feature list with one configured replacement."""
    out = [feature for feature in features if feature != remove]
    if add not in out:
        out.append(add)
    return out


def build_feature_sets(config: dict[str, Any]) -> list[FeatureSet]:
    """Build the explicit scoped feature sets."""
    primary = list(config["features"]["primary_8"])
    water_cfg = config["features"]["water_sensitivity_replace"]
    road_cfg = config["features"]["road_sensitivity_replace"]
    road_len_cfg = config["features"]["road_length_sensitivity_replace"]
    compact = list(config["features"]["compact_water_road"])
    exploratory = list(config["features"]["exploratory_sensitivity_only"])

    feature_sets = [
        FeatureSet(NULL_FEATURE_SET_ID, "null_baseline", [], True, "Intercept-only LOO mean prediction."),
        FeatureSet("primary_8", "primary", primary, True, "A-L2.1b small primary candidate set."),
        FeatureSet(
            "water_sensitivity",
            "sensitivity",
            replace_feature(primary, str(water_cfg["remove"]), str(water_cfg["add"])),
            True,
            "Replace water_fraction_250m with low-variance water_fraction_100m.",
        ),
        FeatureSet(
            "road_sensitivity",
            "sensitivity",
            replace_feature(primary, str(road_cfg["remove"]), str(road_cfg["add"])),
            True,
            "Replace road_density_m_per_ha_250m with road_density_m_per_ha_500m.",
        ),
        FeatureSet(
            "road_length_sensitivity",
            "sensitivity",
            replace_feature(primary, str(road_len_cfg["remove"]), str(road_len_cfg["add"])),
            True,
            "Alternative A-L2.1b road sensitivity using road_length_m_500m.",
        ),
        FeatureSet(
            "compact_water_road",
            "compact",
            compact,
            True,
            "Compact water/road/building context set for n=27 parsimony.",
        ),
        FeatureSet(
            "building_50m_exploratory",
            "exploratory_sensitivity",
            exploratory,
            False,
            "Exploratory 50 m building sensitivity only; not promotion-eligible.",
        ),
    ]
    for feature in primary:
        feature_sets.append(
            FeatureSet(
                f"one_feature:{feature}",
                "one_feature",
                [feature],
                True,
                "Single primary candidate screen with nested Ridge.",
            )
        )
    return feature_sets


def feature_sets_frame(feature_sets: Sequence[FeatureSet]) -> pd.DataFrame:
    """Create the feature-set inventory output table."""
    rows = []
    for feature_set in feature_sets:
        rows.append(
            {
                "feature_set_id": feature_set.feature_set_id,
                "feature_set_role": feature_set.feature_set_role,
                "decision_eligible": feature_set.decision_eligible,
                "feature_count": len(feature_set.features),
                "feature_columns": semicolon(feature_set.features),
                "notes": feature_set.notes,
            }
        )
    return pd.DataFrame(rows)


def all_model_features(feature_sets: Sequence[FeatureSet]) -> list[str]:
    """Return all unique model feature columns."""
    return list(dict.fromkeys(feature for feature_set in feature_sets for feature in feature_set.features))


def validate_feature_columns(features: Sequence[str], available: Sequence[str], forbidden_tokens: Sequence[str]) -> None:
    """Stop on missing or leakage-like model features."""
    available_set = set(available)
    missing = [feature for feature in features if feature not in available_set]
    if missing:
        raise ValueError(f"Missing configured feature columns: {semicolon(missing)}")
    forbidden: list[str] = []
    lowered_tokens = [token.lower() for token in forbidden_tokens]
    for feature in features:
        lowered = feature.lower()
        if any(token in lowered for token in lowered_tokens):
            forbidden.append(feature)
    if forbidden:
        raise ValueError(f"Forbidden leakage feature requested: {semicolon(forbidden)}")


def build_input_table(
    residual_summary: pd.DataFrame,
    feature_wide: pd.DataFrame,
    feature_sets: Sequence[FeatureSet],
    config: dict[str, Any],
) -> pd.DataFrame:
    """Build the one-row-per-station model input table."""
    target_columns = [str(item["target_column"]) for item in config["targets"]]
    base_columns = ["station_id", "n_rows", "n_ge31", "low_support_warning_flag"] + target_columns
    residual_columns = [column for column in base_columns if column in residual_summary.columns]
    features = all_model_features(feature_sets)
    validate_feature_columns(features, feature_wide.columns, config["forbidden_feature_tokens"])

    station_columns = ["station_id", "station_name"] + features
    table = residual_summary.loc[:, residual_columns].merge(
        feature_wide.loc[:, station_columns],
        on="station_id",
        how="left",
        validate="one_to_one",
    )
    front = ["station_id", "station_name", "n_rows", "n_ge31", "low_support_warning_flag"] + target_columns
    table = table.loc[:, front + [feature for feature in features if feature not in front]]

    for column in ["n_rows", "n_ge31"] + target_columns + features:
        if column in table.columns:
            table[column] = pd.to_numeric(table[column], errors="coerce")
    table["low_support_warning_flag"] = table["low_support_warning_flag"].map(bool_value)

    for feature in features:
        table[f"{feature}_missing_flag"] = table[feature].isna().astype(int)

    expected = int(config["expected_station_count"])
    if len(table) != expected:
        raise ValueError(f"Expected {expected} stations, found {len(table)} in scoped input table.")
    if table["station_id"].isna().any() or table["station_id"].duplicated().any():
        raise ValueError("Scoped input table has missing or duplicated station_id values.")
    return table.sort_values("station_id").reset_index(drop=True)


def target_label(config: dict[str, Any], target_column: str) -> str:
    """Return a human-readable target label."""
    for item in config["targets"]:
        if item["target_column"] == target_column:
            return str(item["target_label"])
    return target_column


def target_short_name(target_column: str) -> str:
    """Return a compact target id for station-diagnostic columns."""
    if "high_tail" in target_column:
        return "high_tail"
    if "score" in target_column:
        return "score"
    return target_column.replace("mean_context_adjusted_", "").replace("_residual_c", "")


def clean_target_feature_frame(input_table: pd.DataFrame, target_column: str, features: Sequence[str]) -> pd.DataFrame:
    """Return station rows with an available target for LOO modelling."""
    columns = ["station_id", "station_name", "n_rows", "n_ge31", "low_support_warning_flag", target_column] + list(features)
    df = input_table.loc[:, columns].copy()
    df[target_column] = pd.to_numeric(df[target_column], errors="coerce")
    return df.loc[df[target_column].notna()].reset_index(drop=True)


def gaussian_solve(matrix: list[list[float]], rhs: list[float]) -> np.ndarray:
    """Solve a tiny dense linear system with partial pivoting."""
    n = len(rhs)
    a = [row[:] + [float(rhs[idx])] for idx, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row_idx: abs(a[row_idx][col]))
        if abs(a[pivot][col]) < 1e-12:
            a[pivot][col] = 1e-12
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
        pivot_value = a[col][col]
        for j in range(col, n + 1):
            a[col][j] /= pivot_value
        for row_idx in range(n):
            if row_idx == col:
                continue
            factor = a[row_idx][col]
            if factor == 0.0:
                continue
            for j in range(col, n + 1):
                a[row_idx][j] -= factor * a[col][j]
    return np.asarray([a[row_idx][n] for row_idx in range(n)], dtype=float)


def ridge_coefficients(x_scaled: np.ndarray, y_centered: np.ndarray, alpha: float) -> np.ndarray:
    """Fit Ridge coefficients for tiny station-level design matrices."""
    n_features = int(x_scaled.shape[1])
    matrix: list[list[float]] = []
    rhs: list[float] = []
    for i in range(n_features):
        row: list[float] = []
        xi = x_scaled[:, i]
        for j in range(n_features):
            value = float(np.sum(xi * x_scaled[:, j]))
            if i == j:
                value += alpha
            row.append(value)
        matrix.append(row)
        rhs.append(float(np.sum(xi * y_centered)))
    return gaussian_solve(matrix, rhs)


def soft_threshold(value: float, penalty: float) -> float:
    """Soft-threshold one coordinate for ElasticNet."""
    if value > penalty:
        return value - penalty
    if value < -penalty:
        return value + penalty
    return 0.0


def elasticnet_coefficients(
    x_scaled: np.ndarray,
    y_centered: np.ndarray,
    alpha: float,
    l1_ratio: float,
    max_iter: int,
    tolerance: float = 1e-7,
) -> np.ndarray:
    """Fit a small deterministic ElasticNet by coordinate descent."""
    n_samples, n_features = x_scaled.shape
    coef = np.zeros(n_features, dtype=float)
    prediction = np.zeros(n_samples, dtype=float)
    l1_penalty = alpha * l1_ratio
    l2_penalty = alpha * (1.0 - l1_ratio)
    column_norms = np.asarray([float(np.sum(x_scaled[:, j] * x_scaled[:, j])) / n_samples for j in range(n_features)])
    for _iteration in range(max_iter):
        max_change = 0.0
        for j in range(n_features):
            old = float(coef[j])
            residual_plus = y_centered - prediction + x_scaled[:, j] * old
            rho = float(np.sum(x_scaled[:, j] * residual_plus)) / n_samples
            denom = float(column_norms[j] + l2_penalty)
            new = soft_threshold(rho, l1_penalty) / denom if denom > 0.0 else 0.0
            change = new - old
            if change != 0.0:
                coef[j] = new
                prediction += x_scaled[:, j] * change
                max_change = max(max_change, abs(change))
        if max_change <= tolerance:
            break
    return coef


def fit_standardized_linear(
    x_train: np.ndarray,
    y_train: np.ndarray,
    model_kind: str,
    params: dict[str, float],
    seed: int,
) -> StandardizedLinearFit:
    """Fit a standardized Ridge or ElasticNet model without pipeline overhead."""
    x = np.asarray(x_train, dtype=float)
    y = np.asarray(y_train, dtype=float)
    medians = np.nanmedian(x, axis=0)
    medians = np.where(np.isfinite(medians), medians, 0.0)
    x_imputed = np.where(np.isnan(x), medians, x)
    means = np.mean(x_imputed, axis=0)
    scales = np.std(x_imputed, axis=0)
    scales = np.where(scales > 0.0, scales, 1.0)
    x_scaled = (x_imputed - means) / scales
    y_mean = float(np.mean(y))
    y_centered = y - y_mean
    if model_kind == "ridge":
        coef = ridge_coefficients(x_scaled, y_centered, float(params["alpha"]))
    elif model_kind == "elasticnet":
        coef = elasticnet_coefficients(
            x_scaled,
            y_centered,
            float(params["alpha"]),
            float(params["l1_ratio"]),
            int(params.get("max_iter", 100000)),
        )
    else:
        raise ValueError(f"Unsupported model kind: {model_kind}")
    return StandardizedLinearFit(medians=medians, means=means, scales=scales, y_mean=y_mean, coef=np.asarray(coef, dtype=float))


def predict_standardized_linear(fit: StandardizedLinearFit, x_values: np.ndarray) -> np.ndarray:
    """Predict with a fitted standardized linear model."""
    x = np.asarray(x_values, dtype=float)
    x_imputed = np.where(np.isnan(x), fit.medians, x)
    x_scaled = (x_imputed - fit.means) / fit.scales
    return fit.y_mean + np.sum(x_scaled * fit.coef, axis=1)


def param_grid(config: dict[str, Any], model_kind: str) -> list[dict[str, float]]:
    """Return configured hyperparameter grid."""
    if model_kind == "ridge":
        return [{"alpha": float(alpha)} for alpha in config["models"]["ridge_alphas"]]
    if model_kind == "elasticnet":
        rows = []
        for alpha in config["models"]["elasticnet_alphas"]:
            for l1_ratio in config["models"]["elasticnet_l1_ratios"]:
                rows.append(
                    {
                        "alpha": float(alpha),
                        "l1_ratio": float(l1_ratio),
                        "max_iter": float(config["models"]["elasticnet_max_iter"]),
                    }
                )
        return rows
    raise ValueError(f"Unsupported model kind: {model_kind}")


def params_key(params: dict[str, float]) -> tuple[float, float]:
    """Stable tie-break key for hyperparameter grids."""
    return (float(params.get("alpha", 0.0)), float(params.get("l1_ratio", 0.0)))


def params_label(params: dict[str, float]) -> str:
    """Compact hyperparameter label."""
    if "l1_ratio" in params:
        return f"alpha={fmt(params['alpha'], 4)},l1_ratio={fmt(params['l1_ratio'], 4)}"
    return f"alpha={fmt(params['alpha'], 4)}"


def loo_fixed_predictions(
    df: pd.DataFrame,
    target_column: str,
    features: Sequence[str],
    model_kind: str,
    params: dict[str, float],
    seed: int,
) -> pd.DataFrame:
    """Run outer LOO with fixed hyperparameters."""
    rows = []
    x = df.loc[:, list(features)].to_numpy(dtype=float)
    y = df[target_column].to_numpy(dtype=float)
    station_ids = df["station_id"].astype(str).to_numpy()
    station_names = df["station_name"].fillna("").astype(str).to_numpy()
    low_support = df["low_support_warning_flag"].map(bool_value).to_numpy()
    n_rows = df["n_rows"].to_numpy(dtype=float)
    n_ge31 = df["n_ge31"].to_numpy(dtype=float)
    for holdout in range(len(df)):
        train_mask = np.arange(len(df)) != holdout
        estimator = fit_standardized_linear(x[train_mask], y[train_mask], model_kind, params, seed + holdout)
        prediction = float(predict_standardized_linear(estimator, x[[holdout]])[0])
        rows.append(
            {
                "station_id": station_ids[holdout],
                "station_name": station_names[holdout],
                "fold_index": holdout + 1,
                "n_rows": n_rows[holdout],
                "n_ge31": n_ge31[holdout],
                "low_support_warning_flag": bool(low_support[holdout]),
                "observed": y[holdout],
                "predicted": prediction,
                "error_pred_minus_obs": prediction - y[holdout],
                "abs_error": abs(prediction - y[holdout]),
                "selected_params": params_label(params),
                "hyperparameter_mode": "fixed",
            }
        )
    return pd.DataFrame(rows)


def mean_absolute_error_for_params(
    df: pd.DataFrame,
    target_column: str,
    features: Sequence[str],
    model_kind: str,
    params: dict[str, float],
    seed: int,
) -> float:
    """Return fixed-parameter LOO MAE."""
    predictions = loo_fixed_predictions(df, target_column, features, model_kind, params, seed)
    return float(np.mean(predictions["abs_error"]))


def select_params_by_loo(
    df: pd.DataFrame,
    target_column: str,
    features: Sequence[str],
    model_kind: str,
    grid: Sequence[dict[str, float]],
    seed: int,
) -> dict[str, float]:
    """Select hyperparameters by LOO MAE on the supplied training stations."""
    scored: list[tuple[float, tuple[float, float], dict[str, float]]] = []
    for params in grid:
        mae = mean_absolute_error_for_params(df, target_column, features, model_kind, params, seed)
        scored.append((mae, params_key(params), dict(params)))
    scored.sort(key=lambda item: (item[0], item[1]))
    return scored[0][2]


def loo_nested_predictions(
    df: pd.DataFrame,
    target_column: str,
    features: Sequence[str],
    model_kind: str,
    grid: Sequence[dict[str, float]],
    seed: int,
) -> pd.DataFrame:
    """Run nested inner-LOO hyperparameter selection and outer station LOO."""
    rows = []
    x = df.loc[:, list(features)].to_numpy(dtype=float)
    y = df[target_column].to_numpy(dtype=float)
    station_ids = df["station_id"].astype(str).to_numpy()
    station_names = df["station_name"].fillna("").astype(str).to_numpy()
    low_support = df["low_support_warning_flag"].map(bool_value).to_numpy()
    n_rows = df["n_rows"].to_numpy(dtype=float)
    n_ge31 = df["n_ge31"].to_numpy(dtype=float)
    for holdout in range(len(df)):
        train_mask = np.arange(len(df)) != holdout
        train_df = df.loc[train_mask].reset_index(drop=True)
        selected = select_params_by_loo(train_df, target_column, features, model_kind, grid, seed + holdout * 100)
        estimator = fit_standardized_linear(x[train_mask], y[train_mask], model_kind, selected, seed + holdout)
        prediction = float(predict_standardized_linear(estimator, x[[holdout]])[0])
        rows.append(
            {
                "station_id": station_ids[holdout],
                "station_name": station_names[holdout],
                "fold_index": holdout + 1,
                "n_rows": n_rows[holdout],
                "n_ge31": n_ge31[holdout],
                "low_support_warning_flag": bool(low_support[holdout]),
                "observed": y[holdout],
                "predicted": prediction,
                "error_pred_minus_obs": prediction - y[holdout],
                "abs_error": abs(prediction - y[holdout]),
                "selected_params": params_label(selected),
                "hyperparameter_mode": "nested_inner_loo",
            }
        )
    return pd.DataFrame(rows)


def loo_null_predictions(df: pd.DataFrame, target_column: str) -> pd.DataFrame:
    """Run intercept-only station LOO mean prediction."""
    rows = []
    y = df[target_column].to_numpy(dtype=float)
    for holdout, row in df.iterrows():
        train_mask = np.arange(len(df)) != holdout
        prediction = float(np.mean(y[train_mask]))
        observed = float(row[target_column])
        rows.append(
            {
                "station_id": str(row["station_id"]),
                "station_name": "" if pd.isna(row["station_name"]) else str(row["station_name"]),
                "fold_index": holdout + 1,
                "n_rows": float(row["n_rows"]),
                "n_ge31": float(row["n_ge31"]),
                "low_support_warning_flag": bool_value(row["low_support_warning_flag"]),
                "observed": observed,
                "predicted": prediction,
                "error_pred_minus_obs": prediction - observed,
                "abs_error": abs(prediction - observed),
                "selected_params": "intercept_only_train_mean",
                "hyperparameter_mode": "loo_train_mean",
            }
        )
    return pd.DataFrame(rows)


def corr(values_a: Sequence[float], values_b: Sequence[float], method: str) -> float:
    """Return a robust Pearson or Spearman correlation."""
    series_a = np.asarray(values_a, dtype=float)
    series_b = np.asarray(values_b, dtype=float)
    valid = np.isfinite(series_a) & np.isfinite(series_b)
    if int(np.sum(valid)) < 3:
        return float("nan")
    a = series_a[valid]
    b = series_b[valid]
    if len(set(float(value) for value in a)) < 2 or len(set(float(value) for value in b)) < 2:
        return float("nan")
    if method == "spearman":
        a = average_ranks(a)
        b = average_ranks(b)
    elif method != "pearson":
        raise ValueError(f"Unsupported correlation method: {method}")
    a_centered = a - float(np.mean(a))
    b_centered = b - float(np.mean(b))
    denom = math.sqrt(float(np.sum(a_centered * a_centered)) * float(np.sum(b_centered * b_centered)))
    if denom <= 0.0:
        return float("nan")
    return float(np.sum(a_centered * b_centered) / denom)


def average_ranks(values: np.ndarray) -> np.ndarray:
    """Return average ranks for ties without pandas/scipy correlation paths."""
    order = sorted(range(len(values)), key=lambda idx: (float(values[idx]), idx))
    ranks = np.zeros(len(values), dtype=float)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and float(values[order[end]]) == float(values[order[start]]):
            end += 1
        average_rank = (start + 1 + end) / 2.0
        for pos in range(start, end):
            ranks[order[pos]] = average_rank
        start = end
    return ranks


def r2_score_out_of_fold(observed: Sequence[float], predicted: Sequence[float]) -> float:
    """Return out-of-fold R2 against the observed mean."""
    y = np.asarray(observed, dtype=float)
    p = np.asarray(predicted, dtype=float)
    denom = float(np.sum((y - np.mean(y)) ** 2))
    if denom <= 0.0:
        return float("nan")
    return 1.0 - float(np.sum((y - p) ** 2)) / denom


def subset_metrics(predictions: pd.DataFrame) -> dict[str, float]:
    """Return basic metrics for a prediction subset."""
    if predictions.empty:
        return {"mae": float("nan"), "rmse": float("nan"), "r2": float("nan"), "spearman": float("nan")}
    observed = predictions["observed"].to_numpy(dtype=float)
    predicted = predictions["predicted"].to_numpy(dtype=float)
    return {
        "mae": float(np.mean(np.abs(predicted - observed))),
        "rmse": float(np.sqrt(np.mean((predicted - observed) ** 2))),
        "r2": r2_score_out_of_fold(observed, predicted),
        "spearman": corr(observed, predicted, "spearman"),
    }


def selected_params_summary(predictions: pd.DataFrame) -> str:
    """Summarize selected hyperparameters across outer folds."""
    counts = predictions["selected_params"].value_counts().sort_index()
    return ";".join(f"{key}:{int(value)}" for key, value in counts.items())


def build_metrics_row(
    predictions: pd.DataFrame,
    target_column: str,
    target_name: str,
    model_family: str,
    feature_set: FeatureSet,
    hyperparameter_mode: str,
    feature_count: int,
) -> dict[str, Any]:
    """Build required metric row for one target/model/feature-set."""
    observed = predictions["observed"].to_numpy(dtype=float)
    predicted = predictions["predicted"].to_numpy(dtype=float)
    errors = predicted - observed
    abs_errors = np.abs(errors)
    worst_idx = int(np.argmax(abs_errors))
    no_s142 = predictions.loc[predictions["station_id"] != S142]
    no_s139 = predictions.loc[predictions["station_id"] != S139]
    no_s142_metrics = subset_metrics(no_s142)
    no_s139_metrics = subset_metrics(no_s139)

    def station_value(station_id: str, column: str) -> float:
        station_rows = predictions.loc[predictions["station_id"] == station_id]
        if station_rows.empty:
            return float("nan")
        return float(station_rows.iloc[0][column])

    sign_accuracy = float(np.mean(np.sign(observed) == np.sign(predicted)))
    return {
        "target_column": target_column,
        "target_label": target_name,
        "model_family": model_family,
        "feature_set_id": feature_set.feature_set_id,
        "feature_set_role": feature_set.feature_set_role,
        "decision_eligible": feature_set.decision_eligible,
        "feature_count": feature_count,
        "feature_columns": semicolon(feature_set.features),
        "n_stations": int(len(predictions)),
        "n_folds": int(len(predictions)),
        "mae": float(np.mean(abs_errors)),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "bias_pred_minus_obs": float(np.mean(errors)),
        "r2": r2_score_out_of_fold(observed, predicted),
        "spearman_observed_vs_predicted": corr(observed, predicted, "spearman"),
        "pearson_observed_vs_predicted": corr(observed, predicted, "pearson"),
        "sign_accuracy": sign_accuracy,
        "median_absolute_error": float(np.median(abs_errors)),
        "p90_absolute_error": float(np.percentile(abs_errors, 90)),
        "worst_station_id": str(predictions.iloc[worst_idx]["station_id"]),
        "worst_station_abs_error": float(abs_errors[worst_idx]),
        "s142_error_pred_minus_obs": station_value(S142, "error_pred_minus_obs"),
        "s142_abs_error": station_value(S142, "abs_error"),
        "s139_error_pred_minus_obs": station_value(S139, "error_pred_minus_obs"),
        "s139_abs_error": station_value(S139, "abs_error"),
        "no_s142_mae": no_s142_metrics["mae"],
        "no_s142_rmse": no_s142_metrics["rmse"],
        "no_s142_r2": no_s142_metrics["r2"],
        "no_s142_spearman": no_s142_metrics["spearman"],
        "no_s139_mae": no_s139_metrics["mae"],
        "no_s139_spearman": no_s139_metrics["spearman"],
        "selected_params_summary": selected_params_summary(predictions),
        "hyperparameter_mode": hyperparameter_mode,
        "bias_definition": "predicted_minus_observed",
    }


def add_prediction_metadata(
    predictions: pd.DataFrame,
    target_column: str,
    target_name: str,
    model_family: str,
    feature_set: FeatureSet,
) -> pd.DataFrame:
    """Add model and target metadata to LOO predictions."""
    out = predictions.copy()
    out.insert(0, "target_column", target_column)
    out.insert(1, "target_label", target_name)
    out.insert(2, "model_family", model_family)
    out.insert(3, "feature_set_id", feature_set.feature_set_id)
    out.insert(4, "feature_set_role", feature_set.feature_set_role)
    out.insert(5, "feature_count", len(feature_set.features))
    out.insert(6, "feature_columns", semicolon(feature_set.features))
    return out


def evaluate_models(
    input_table: pd.DataFrame,
    feature_sets: Sequence[FeatureSet],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate null, one-feature Ridge, Ridge, and ElasticNet with station LOO."""
    metric_rows: list[dict[str, Any]] = []
    prediction_frames: list[pd.DataFrame] = []
    null_set = next(feature_set for feature_set in feature_sets if feature_set.feature_set_id == NULL_FEATURE_SET_ID)
    one_feature_sets = [feature_set for feature_set in feature_sets if feature_set.feature_set_role == "one_feature"]
    multi_sets = [
        feature_set
        for feature_set in feature_sets
        if feature_set.feature_set_role in {"primary", "sensitivity", "compact", "exploratory_sensitivity"}
    ]

    for target in config["targets"]:
        target_column = str(target["target_column"])
        target_name = str(target["target_label"])
        null_df = clean_target_feature_frame(input_table, target_column, [])
        null_predictions = loo_null_predictions(null_df, target_column)
        metric_rows.append(
            build_metrics_row(
                null_predictions,
                target_column,
                target_name,
                "null_mean_baseline",
                null_set,
                "loo_train_mean",
                0,
            )
        )
        prediction_frames.append(add_prediction_metadata(null_predictions, target_column, target_name, "null_mean_baseline", null_set))

        for feature_set in one_feature_sets:
            model_df = clean_target_feature_frame(input_table, target_column, feature_set.features)
            predictions = loo_nested_predictions(
                model_df,
                target_column,
                feature_set.features,
                "ridge",
                param_grid(config, "ridge"),
                seed=int(config["resampling"]["bootstrap_seed"]),
            )
            metric_rows.append(
                build_metrics_row(
                    predictions,
                    target_column,
                    target_name,
                    "one_feature_ridge",
                    feature_set,
                    "nested_inner_loo",
                    len(feature_set.features),
                )
            )
            prediction_frames.append(add_prediction_metadata(predictions, target_column, target_name, "one_feature_ridge", feature_set))

        for feature_set in multi_sets:
            model_df = clean_target_feature_frame(input_table, target_column, feature_set.features)
            ridge_predictions = loo_nested_predictions(
                model_df,
                target_column,
                feature_set.features,
                "ridge",
                param_grid(config, "ridge"),
                seed=int(config["resampling"]["bootstrap_seed"]) + 500,
            )
            metric_rows.append(
                build_metrics_row(
                    ridge_predictions,
                    target_column,
                    target_name,
                    "ridge",
                    feature_set,
                    "nested_inner_loo",
                    len(feature_set.features),
                )
            )
            prediction_frames.append(add_prediction_metadata(ridge_predictions, target_column, target_name, "ridge", feature_set))

            elastic_predictions = loo_nested_predictions(
                model_df,
                target_column,
                feature_set.features,
                "elasticnet",
                param_grid(config, "elasticnet"),
                seed=int(config["resampling"]["bootstrap_seed"]) + 1000,
            )
            metric_rows.append(
                build_metrics_row(
                    elastic_predictions,
                    target_column,
                    target_name,
                    "elasticnet",
                    feature_set,
                    "nested_inner_loo",
                    len(feature_set.features),
                )
            )
            prediction_frames.append(add_prediction_metadata(elastic_predictions, target_column, target_name, "elasticnet", feature_set))

    return pd.DataFrame(metric_rows), pd.concat(prediction_frames, ignore_index=True)


def model_kind_for_family(model_family: str) -> str:
    """Map output model family to estimator kind."""
    if model_family in {"ridge", "one_feature_ridge"}:
        return "ridge"
    if model_family == "elasticnet":
        return "elasticnet"
    raise ValueError(f"No estimator kind for model_family={model_family}")


def best_eligible_models(metrics: pd.DataFrame) -> pd.DataFrame:
    """Return best non-null decision-eligible model per primary target by LOO MAE."""
    candidates = metrics.loc[
        (metrics["model_family"] != "null_mean_baseline") & (metrics["decision_eligible"].map(bool_value))
    ].copy()
    candidates = candidates.sort_values(
        ["target_column", "mae", "feature_count", "model_family", "feature_set_id"],
        ascending=[True, True, True, True, True],
    )
    return candidates.groupby("target_column", as_index=False).head(1).reset_index(drop=True)


def feature_set_by_id(feature_sets: Sequence[FeatureSet]) -> dict[str, FeatureSet]:
    """Return feature-set lookup by id."""
    return {feature_set.feature_set_id: feature_set for feature_set in feature_sets}


def permutation_null(
    input_table: pd.DataFrame,
    best_models: pd.DataFrame,
    feature_sets: Sequence[FeatureSet],
    config: dict[str, Any],
) -> pd.DataFrame:
    """Run fixed-hyperparameter permutation null for each target's best model."""
    rng = np.random.default_rng(int(config["resampling"]["permutation_seed"]))
    iterations = int(config["resampling"]["permutation_iterations"])
    rows: list[dict[str, Any]] = []
    feature_lookup = feature_set_by_id(feature_sets)
    for _, best in best_models.iterrows():
        target_column = str(best["target_column"])
        target_name = str(best["target_label"])
        feature_set = feature_lookup[str(best["feature_set_id"])]
        model_family = str(best["model_family"])
        model_kind = model_kind_for_family(model_family)
        model_df = clean_target_feature_frame(input_table, target_column, feature_set.features)
        fixed_params = select_params_by_loo(
            model_df,
            target_column,
            feature_set.features,
            model_kind,
            param_grid(config, model_kind),
            seed=int(config["resampling"]["permutation_seed"]) + 17,
        )
        observed_predictions = loo_fixed_predictions(
            model_df,
            target_column,
            feature_set.features,
            model_kind,
            fixed_params,
            seed=int(config["resampling"]["permutation_seed"]) + 29,
        )
        observed_metrics = subset_metrics(observed_predictions)
        perm_mae: list[float] = []
        perm_spearman: list[float] = []
        y = model_df[target_column].to_numpy(dtype=float)
        for iteration in range(iterations):
            permuted_df = model_df.copy()
            permuted_df[target_column] = rng.permutation(y)
            perm_predictions = loo_fixed_predictions(
                permuted_df,
                target_column,
                feature_set.features,
                model_kind,
                fixed_params,
                seed=int(config["resampling"]["permutation_seed"]) + 1000 + iteration,
            )
            perm_metrics = subset_metrics(perm_predictions)
            perm_mae.append(perm_metrics["mae"])
            perm_spearman.append(perm_metrics["spearman"])
        perm_mae_arr = np.asarray(perm_mae, dtype=float)
        perm_spear_arr = np.asarray(perm_spearman, dtype=float)
        obs_spear = observed_metrics["spearman"]
        rows.append(
            {
                "target_column": target_column,
                "target_label": target_name,
                "model_family": model_family,
                "feature_set_id": feature_set.feature_set_id,
                "feature_columns": semicolon(feature_set.features),
                "fixed_selected_params": params_label(fixed_params),
                "iterations": iterations,
                "observed_fixed_mae": observed_metrics["mae"],
                "observed_fixed_spearman": obs_spear,
                "permutation_mae_mean": float(np.mean(perm_mae_arr)),
                "permutation_mae_p05": float(np.percentile(perm_mae_arr, 5)),
                "permutation_mae_p50": float(np.percentile(perm_mae_arr, 50)),
                "permutation_mae_p95": float(np.percentile(perm_mae_arr, 95)),
                "permutation_spearman_mean": float(np.nanmean(perm_spear_arr)),
                "permutation_spearman_p05": float(np.nanpercentile(perm_spear_arr, 5)),
                "permutation_spearman_p50": float(np.nanpercentile(perm_spear_arr, 50)),
                "permutation_spearman_p95": float(np.nanpercentile(perm_spear_arr, 95)),
                "permutation_p_value_mae_directional": float((np.sum(perm_mae_arr <= observed_metrics["mae"]) + 1) / (iterations + 1)),
                "permutation_p_value_spearman_directional": float((np.nansum(perm_spear_arr >= obs_spear) + 1) / (iterations + 1)),
                "permutation_note": str(config["resampling"]["permutation_scope"]),
            }
        )
    return pd.DataFrame(rows)


def fit_full_estimator(
    df: pd.DataFrame,
    target_column: str,
    features: Sequence[str],
    model_kind: str,
    params: dict[str, float],
    seed: int,
) -> StandardizedLinearFit:
    """Fit one full-data standardized estimator."""
    return fit_standardized_linear(
        df.loc[:, list(features)].to_numpy(dtype=float),
        df[target_column].to_numpy(dtype=float),
        model_kind,
        params,
        seed,
    )


def coefficients_from_estimator(estimator: StandardizedLinearFit) -> np.ndarray:
    """Extract model coefficients from the pipeline."""
    return np.asarray(estimator.coef, dtype=float)


def bootstrap_stability(
    input_table: pd.DataFrame,
    best_models: pd.DataFrame,
    feature_sets: Sequence[FeatureSet],
    config: dict[str, Any],
) -> pd.DataFrame:
    """Bootstrap station rows for coefficient sign and selection stability."""
    rng = np.random.default_rng(int(config["resampling"]["bootstrap_seed"]))
    iterations = int(config["resampling"]["bootstrap_iterations"])
    tolerance = float(config["models"]["coefficient_nonzero_tolerance"])
    feature_lookup = feature_set_by_id(feature_sets)
    rows: list[dict[str, Any]] = []
    for _, best in best_models.iterrows():
        target_column = str(best["target_column"])
        target_name = str(best["target_label"])
        feature_set = feature_lookup[str(best["feature_set_id"])]
        model_family = str(best["model_family"])
        model_kind = model_kind_for_family(model_family)
        model_df = clean_target_feature_frame(input_table, target_column, feature_set.features)
        fixed_params = select_params_by_loo(
            model_df,
            target_column,
            feature_set.features,
            model_kind,
            param_grid(config, model_kind),
            seed=int(config["resampling"]["bootstrap_seed"]) + 41,
        )
        full_estimator = fit_full_estimator(
            model_df,
            target_column,
            feature_set.features,
            model_kind,
            fixed_params,
            seed=int(config["resampling"]["bootstrap_seed"]) + 43,
        )
        full_coefs = coefficients_from_estimator(full_estimator)
        boot_coefs: list[np.ndarray] = []
        values = model_df.reset_index(drop=True)
        for iteration in range(iterations):
            sample_idx = rng.integers(0, len(values), size=len(values))
            sample = values.iloc[sample_idx].reset_index(drop=True)
            estimator = fit_full_estimator(
                sample,
                target_column,
                feature_set.features,
                model_kind,
                fixed_params,
                seed=int(config["resampling"]["bootstrap_seed"]) + 1000 + iteration,
            )
            boot_coefs.append(coefficients_from_estimator(estimator))
        coef_matrix = np.vstack(boot_coefs)
        for idx, feature in enumerate(feature_set.features):
            values_for_feature = coef_matrix[:, idx]
            full_coef = float(full_coefs[idx])
            full_sign = float(np.sign(full_coef))
            if full_sign == 0.0:
                same_sign_fraction = float(np.mean(np.abs(values_for_feature) <= tolerance))
            else:
                same_sign_fraction = float(np.mean(np.sign(values_for_feature) == full_sign))
            rows.append(
                {
                    "target_column": target_column,
                    "target_label": target_name,
                    "model_family": model_family,
                    "feature_set_id": feature_set.feature_set_id,
                    "feature_column": feature,
                    "fixed_selected_params": params_label(fixed_params),
                    "iterations": iterations,
                    "full_data_standardized_coef": full_coef,
                    "coef_median": float(np.median(values_for_feature)),
                    "coef_ci_low": float(np.percentile(values_for_feature, 2.5)),
                    "coef_ci_high": float(np.percentile(values_for_feature, 97.5)),
                    "positive_sign_fraction": float(np.mean(values_for_feature > tolerance)),
                    "negative_sign_fraction": float(np.mean(values_for_feature < -tolerance)),
                    "same_sign_as_full_fraction": same_sign_fraction,
                    "selection_fraction_nonzero": float(np.mean(np.abs(values_for_feature) > tolerance)),
                    "stability_note": str(config["resampling"]["bootstrap_scope"]),
                    "interpretation_boundary": "descriptive coefficient stability only; no causal correction",
                }
            )
    return pd.DataFrame(rows)


def probability_diagnostics(probability_summary: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create station-level companion probability diagnostic columns."""
    rows = []
    for case in config["probability_error_cases"]:
        case_id = str(case["probability_case_id"])
        case_df = probability_summary.loc[probability_summary["probability_case_id"].astype(str) == case_id].copy()
        for _, row in case_df.iterrows():
            rows.append(
                {
                    "station_id": str(row["station_id"]),
                    f"{case_id}_probability_error": pd.to_numeric(row.get("mean_context_adjusted_probability_error_obs_minus_p"), errors="coerce"),
                    f"{case_id}_miss_rate": pd.to_numeric(row.get("miss_rate_at_policy"), errors="coerce"),
                    f"{case_id}_false_alarm_ratio": pd.to_numeric(row.get("false_alarm_ratio_at_policy"), errors="coerce"),
                    f"{case_id}_brier": pd.to_numeric(row.get("p_ge31_Brier"), errors="coerce"),
                    f"{case_id}_precision": pd.to_numeric(row.get("precision_at_policy"), errors="coerce"),
                    f"{case_id}_recall": pd.to_numeric(row.get("recall_at_policy"), errors="coerce"),
                }
            )
    if not rows:
        return pd.DataFrame(columns=["station_id"])
    wide = pd.DataFrame(rows).groupby("station_id", as_index=False).first()
    return wide


def stability_diagnostics(stability: pd.DataFrame) -> pd.DataFrame:
    """Create compact station residual stability labels."""
    rows = []
    wanted = {
        "mean_context_adjusted_score_residual_c": "score_stability_label",
        "mean_context_adjusted_high_tail_residual_c": "high_tail_stability_label",
    }
    for metric_name, output_column in wanted.items():
        subset = stability.loc[stability["metric_name"].astype(str) == metric_name, ["station_id", "stability_label"]].copy()
        subset = subset.rename(columns={"stability_label": output_column})
        rows.append(subset)
    if not rows:
        return pd.DataFrame(columns=["station_id"])
    out = rows[0]
    for frame in rows[1:]:
        out = out.merge(frame, on="station_id", how="outer")
    return out


def station_diagnostics(
    input_table: pd.DataFrame,
    probability_summary: pd.DataFrame,
    stability: pd.DataFrame,
    predictions: pd.DataFrame,
    best_models: pd.DataFrame,
) -> pd.DataFrame:
    """Create station-level diagnostics with probability summaries and best-model errors."""
    base_cols = [
        "station_id",
        "station_name",
        "n_rows",
        "n_ge31",
        "low_support_warning_flag",
        "mean_context_adjusted_score_residual_c",
        "mean_context_adjusted_high_tail_residual_c",
    ]
    out = input_table.loc[:, [col for col in base_cols if col in input_table.columns]].copy()
    out = out.merge(probability_diagnostics(probability_summary, {"probability_error_cases": [
        {"probability_case_id": "current_companion_best_f1"},
        {"probability_case_id": "current_companion_recall90"},
        {"probability_case_id": "recall_first_challenger_selected_policy"},
    ]}), on="station_id", how="left")
    out = out.merge(stability_diagnostics(stability), on="station_id", how="left")
    for _, best in best_models.iterrows():
        target_column = str(best["target_column"])
        short = target_short_name(target_column)
        subset = predictions.loc[
            (predictions["target_column"] == target_column)
            & (predictions["model_family"] == str(best["model_family"]))
            & (predictions["feature_set_id"] == str(best["feature_set_id"])),
            ["station_id", "predicted", "error_pred_minus_obs", "abs_error"],
        ].copy()
        subset = subset.rename(
            columns={
                "predicted": f"best_{short}_predicted_residual_c",
                "error_pred_minus_obs": f"best_{short}_error_pred_minus_obs_c",
                "abs_error": f"best_{short}_abs_error_c",
            }
        )
        subset[f"best_{short}_model"] = f"{best['model_family']}:{best['feature_set_id']}"
        out = out.merge(subset, on="station_id", how="left")
    out["key_station_caveat"] = np.where(
        out["station_id"].astype(str).isin([S142, S139]),
        "S142/S139 key caveat station",
        "",
    )
    return out.sort_values("station_id").reset_index(drop=True)


def enrich_metrics_with_permutation(metrics: pd.DataFrame, permutation: pd.DataFrame) -> pd.DataFrame:
    """Attach permutation p values to matching metric rows."""
    if permutation.empty:
        return metrics.copy()
    cols = [
        "target_column",
        "model_family",
        "feature_set_id",
        "permutation_p_value_mae_directional",
        "permutation_p_value_spearman_directional",
        "observed_fixed_mae",
        "observed_fixed_spearman",
    ]
    return metrics.merge(permutation.loc[:, cols], on=["target_column", "model_family", "feature_set_id"], how="left")


def decide_target(
    best: pd.Series,
    null: pd.Series,
    permutation_row: pd.Series | None,
    config: dict[str, Any],
) -> tuple[str, str]:
    """Apply the scoped promotion/decision rules for one target."""
    thresholds = config["decision_thresholds"]
    improvement_abs = float(null["mae"]) - float(best["mae"])
    improvement_fraction = improvement_abs / float(null["mae"]) if float(null["mae"]) > 0 else float("nan")
    no_s142_improvement = float(null["no_s142_mae"]) - float(best["no_s142_mae"])
    spearman = float(best["spearman_observed_vs_predicted"])
    no_s142_spearman = float(best["no_s142_spearman"])
    p_mae = float("nan")
    p_spear = float("nan")
    if permutation_row is not None and not permutation_row.empty:
        p_mae = float(permutation_row["permutation_p_value_mae_directional"])
        p_spear = float(permutation_row["permutation_p_value_spearman_directional"])

    meaningful = (
        improvement_abs >= float(thresholds["meaningful_mae_improvement_abs_c"])
        and improvement_fraction >= float(thresholds["meaningful_mae_improvement_fraction"])
    )
    permutation_ok = (
        math.isfinite(p_mae)
        and math.isfinite(p_spear)
        and p_mae <= float(thresholds["permutation_p_threshold"])
        and p_spear <= float(thresholds["permutation_p_threshold"])
    )
    ranking_ok = spearman > float(thresholds["stable_positive_spearman_min"])
    not_s142_only = no_s142_improvement > 0 and no_s142_spearman > 0
    if meaningful and ranking_ok and permutation_ok and not_s142_only:
        return (
            "A_L2_SCOPED_SIGNAL_PROMISING",
            "LOO improves over null, ranking is positive, permutation supports structure, and no-S142 metrics remain favorable.",
        )
    if improvement_abs > 0 and ranking_ok:
        return (
            "A_L2_DATA_LIMITED_WEAK_SIGNAL",
            "Some LOO improvement/ranking signal is present, but permutation, uncertainty, or S142 sensitivity is not strong enough.",
        )
    return (
        "A_L2_NOT_IDENTIFIABLE",
        "No robust LOO improvement over the station mean null baseline under the scoped n=27 design.",
    )


def decision_matrix(
    metrics: pd.DataFrame,
    permutation: pd.DataFrame,
    best_models: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Create target-level decision matrix."""
    rows: list[dict[str, Any]] = []
    for _, best in best_models.iterrows():
        target_column = str(best["target_column"])
        null = metrics.loc[
            (metrics["target_column"] == target_column) & (metrics["model_family"] == "null_mean_baseline")
        ].iloc[0]
        perm_match = permutation.loc[
            (permutation["target_column"] == target_column)
            & (permutation["model_family"] == str(best["model_family"]))
            & (permutation["feature_set_id"] == str(best["feature_set_id"]))
        ]
        perm_row = perm_match.iloc[0] if not perm_match.empty else None
        target_decision, rationale = decide_target(best, null, perm_row, config)
        improvement_abs = float(null["mae"]) - float(best["mae"])
        improvement_fraction = improvement_abs / float(null["mae"]) if float(null["mae"]) > 0 else float("nan")
        no_s142_improvement_abs = float(null["no_s142_mae"]) - float(best["no_s142_mae"])
        no_s142_improvement_fraction = (
            no_s142_improvement_abs / float(null["no_s142_mae"]) if float(null["no_s142_mae"]) > 0 else float("nan")
        )
        rows.append(
            {
                "target_column": target_column,
                "target_label": str(best["target_label"]),
                "n_stations": int(best["n_stations"]),
                "null_mae": float(null["mae"]),
                "best_model_family": str(best["model_family"]),
                "best_feature_set_id": str(best["feature_set_id"]),
                "best_feature_columns": str(best["feature_columns"]),
                "best_mae": float(best["mae"]),
                "mae_improvement_abs_c": improvement_abs,
                "mae_improvement_fraction": improvement_fraction,
                "best_rmse": float(best["rmse"]),
                "best_r2": float(best["r2"]),
                "best_spearman": float(best["spearman_observed_vs_predicted"]),
                "best_pearson": float(best["pearson_observed_vs_predicted"]),
                "best_sign_accuracy": float(best["sign_accuracy"]),
                "best_no_s142_mae": float(best["no_s142_mae"]),
                "null_no_s142_mae": float(null["no_s142_mae"]),
                "no_s142_mae_improvement_abs_c": no_s142_improvement_abs,
                "no_s142_mae_improvement_fraction": no_s142_improvement_fraction,
                "best_no_s142_spearman": float(best["no_s142_spearman"]),
                "s142_abs_error": float(best["s142_abs_error"]),
                "s139_abs_error": float(best["s139_abs_error"]),
                "permutation_p_value_mae_directional": float(perm_row["permutation_p_value_mae_directional"]) if perm_row is not None else float("nan"),
                "permutation_p_value_spearman_directional": float(perm_row["permutation_p_value_spearman_directional"]) if perm_row is not None else float("nan"),
                "target_decision": target_decision,
                "decision_rationale": rationale,
            }
        )
    return pd.DataFrame(rows)


def overall_decision(decisions: pd.DataFrame) -> str:
    """Collapse target decisions to the lane headline."""
    labels = set(decisions["target_decision"].astype(str))
    if "A_L2_SCOPED_SIGNAL_PROMISING" in labels:
        return "A_L2_SCOPED_SIGNAL_PROMISING"
    if "A_L2_DATA_LIMITED_WEAK_SIGNAL" in labels:
        return "A_L2_DATA_LIMITED_WEAK_SIGNAL"
    if "A_L2_NOT_IDENTIFIABLE" in labels:
        return "A_L2_NOT_IDENTIFIABLE"
    return "FAILED"


def a_l2_2_recommendation(decision_status: str) -> str:
    """Return scoped recommendation text."""
    if decision_status == "A_L2_SCOPED_SIGNAL_PROMISING":
        return (
            "Proceed to A-L2.2 only as a protocol review for station-level residual explanation; "
            "do not promote to station correction, station-adjusted WBGT, or local 100 m WBGT."
        )
    if decision_status == "A_L2_DATA_LIMITED_WEAK_SIGNAL":
        return (
            "Do not promote a Level 2 correction model. A-L2.2 may proceed only as a data-limited "
            "design review or additional evidence plan."
        )
    if decision_status == "A_L2_NOT_IDENTIFIABLE":
        return "Do not proceed to A-L2.2 modelling; close or expand station-context evidence before revisiting."
    return "Review failed or blocked inputs before considering A-L2.2."


def format_metric_outputs(metrics: pd.DataFrame) -> pd.DataFrame:
    """Return metrics with stable column order."""
    ordered = [
        "target_column",
        "target_label",
        "model_family",
        "feature_set_id",
        "feature_set_role",
        "decision_eligible",
        "feature_count",
        "feature_columns",
        "n_stations",
        "n_folds",
        "mae",
        "rmse",
        "bias_pred_minus_obs",
        "r2",
        "spearman_observed_vs_predicted",
        "pearson_observed_vs_predicted",
        "sign_accuracy",
        "median_absolute_error",
        "p90_absolute_error",
        "worst_station_id",
        "worst_station_abs_error",
        "s142_error_pred_minus_obs",
        "s142_abs_error",
        "s139_error_pred_minus_obs",
        "s139_abs_error",
        "no_s142_mae",
        "no_s142_rmse",
        "no_s142_r2",
        "no_s142_spearman",
        "no_s139_mae",
        "no_s139_spearman",
        "selected_params_summary",
        "hyperparameter_mode",
        "bias_definition",
    ]
    return metrics.loc[:, [col for col in ordered if col in metrics.columns]]


def target_count_summary(input_table: pd.DataFrame, config: dict[str, Any]) -> str:
    """Return target-specific station counts."""
    parts = []
    for target in config["targets"]:
        column = str(target["target_column"])
        count = int(pd.to_numeric(input_table[column], errors="coerce").notna().sum())
        parts.append(f"{column}={count}")
    return ";".join(parts)


def best_models_summary(decisions: pd.DataFrame) -> str:
    """Return compact best-model summary."""
    parts = []
    for _, row in decisions.iterrows():
        parts.append(
            f"{row['target_label']}:{row['best_model_family']}/{row['best_feature_set_id']} "
            f"MAE={fmt(row['best_mae'], 4)} null={fmt(row['null_mae'], 4)} "
            f"Spearman={fmt(row['best_spearman'], 4)}"
        )
    return "; ".join(parts)


def null_comparison_summary(decisions: pd.DataFrame) -> str:
    """Return compact null baseline comparison."""
    parts = []
    for _, row in decisions.iterrows():
        parts.append(
            f"{row['target_label']}: improvement={fmt(row['mae_improvement_abs_c'], 4)}C "
            f"({fmt(100 * row['mae_improvement_fraction'], 2)}%)"
        )
    return "; ".join(parts)


def permutation_bootstrap_summary(permutation: pd.DataFrame, bootstrap: pd.DataFrame) -> str:
    """Return compact resampling headline."""
    perm_parts = []
    for _, row in permutation.iterrows():
        perm_parts.append(
            f"{row['target_label']}:p_mae={fmt(row['permutation_p_value_mae_directional'], 4)},"
            f"p_spearman={fmt(row['permutation_p_value_spearman_directional'], 4)}"
        )
    stable_features = []
    if not bootstrap.empty:
        stable = bootstrap.loc[
            (bootstrap["same_sign_as_full_fraction"] >= 0.75) & (bootstrap["selection_fraction_nonzero"] >= 0.75)
        ]
        for target, group in stable.groupby("target_label"):
            stable_features.append(f"{target}:{len(group)} stable-sign coefficients")
    return "; ".join(perm_parts + stable_features)


def s142_s139_summary(station_diag: pd.DataFrame) -> str:
    """Return compact S142/S139 caveat text."""
    parts = []
    for station in [S142, S139]:
        row = station_diag.loc[station_diag["station_id"] == station]
        if row.empty:
            parts.append(f"{station}:missing")
            continue
        item = row.iloc[0]
        parts.append(
            f"{station}:n_ge31={fmt(item.get('n_ge31'), 0)},"
            f"score_resid={fmt(item.get('mean_context_adjusted_score_residual_c'), 4)},"
            f"high_tail={fmt(item.get('mean_context_adjusted_high_tail_residual_c'), 4)},"
            f"low_support={item.get('low_support_warning_flag')}"
        )
    return "; ".join(parts)


def report_markdown(
    config: dict[str, Any],
    input_table: pd.DataFrame,
    feature_sets: pd.DataFrame,
    null_metrics: pd.DataFrame,
    one_feature_metrics: pd.DataFrame,
    ridge_metrics: pd.DataFrame,
    elastic_metrics: pd.DataFrame,
    permutation: pd.DataFrame,
    bootstrap: pd.DataFrame,
    station_diag: pd.DataFrame,
    decisions: pd.DataFrame,
    decision_status: str,
) -> str:
    """Build the English Markdown report."""
    low_support_count = int(input_table["low_support_warning_flag"].map(bool_value).sum())
    high_tail_n = int(pd.to_numeric(input_table["mean_context_adjusted_high_tail_residual_c"], errors="coerce").notna().sum())
    one_feature_top = one_feature_metrics.sort_values(["target_column", "mae"]).groupby("target_column", as_index=False).head(4)
    ridge_top = ridge_metrics.sort_values(["target_column", "mae"]).groupby("target_column", as_index=False).head(4)
    elastic_top = elastic_metrics.sort_values(["target_column", "mae"]).groupby("target_column", as_index=False).head(4)
    s_caveat = station_diag.loc[station_diag["station_id"].isin([S142, S139])]
    return f"""# System A A-L2.1c Scoped Station-Level Residual Preflight

Generated: {date.today().isoformat()}
Decision status: `{decision_status}`
Branch: `{git_branch()}`
Config: `configs/v11/systema_l2_scoped_residual_preflight.yaml`

## 1. Why this follows A-L2.1b

A-L2.0 found stable station-level residual structure after Level 1 controls, especially for the score residual and high-tail residual. A-L2.1a-S1 then built all-27 station-local OSM buffer features, and A-L2.1b narrowed them to a small non-redundant primary set. This A-L2.1c lane only asks whether those station-local context features explain station-level residual ranking or magnitude better than null station mean baselines under n=27 constraints.

This is not a promoted Level 2 correction model.

## 2. Input table and station unit

The model input table has one row per station, not hourly rows. `station_id` is retained only as an identifier and is never passed to a model. The score-residual target has {len(input_table)} station rows. The high-tail target has {high_tail_n} usable rows because stations with no high-tail support can have missing high-tail residuals. Low-support flags are retained for interpretation; {low_support_count} stations are flagged.

{markdown_table(input_table, ["station_id", "station_name", "n_rows", "n_ge31", "low_support_warning_flag", "mean_context_adjusted_score_residual_c", "mean_context_adjusted_high_tail_residual_c"], limit=10)}

## 3. Feature sets and target definitions

Primary targets are `mean_context_adjusted_score_residual_c` and `mean_context_adjusted_high_tail_residual_c`. Probability-error and miss/false-alarm station summaries remain diagnostic only and are not modelled as primary targets.

{markdown_table(feature_sets, ["feature_set_id", "feature_set_role", "decision_eligible", "feature_count", "feature_columns"], limit=20)}

## 4. Validation design

All reported model metrics use leave-one-station-out validation. Ridge and ElasticNet use standardized features with inner leave-one-station-out hyperparameter selection inside each outer training fold. The null baseline predicts the mean of the outer training stations. There is no random train/test split and no same-row fitting/evaluation claim.

The permutation null and bootstrap stability are run only for the best eligible non-null model per primary target, using fixed full-data-selected hyperparameters for computationally bounded preflight resampling. This is disclosed as a preflight approximation and is not causal evidence.

## 5. Null baseline results

{markdown_table(null_metrics, ["target_label", "n_stations", "mae", "rmse", "bias_pred_minus_obs", "r2", "spearman_observed_vs_predicted", "s142_abs_error", "s139_abs_error", "no_s142_mae"], limit=8)}

## 6. One-feature screen

{markdown_table(one_feature_top, ["target_label", "model_family", "feature_set_id", "n_stations", "mae", "spearman_observed_vs_predicted", "selected_params_summary", "no_s142_mae"], limit=12)}

## 7. Ridge and ElasticNet scoped results

Ridge top rows:

{markdown_table(ridge_top, ["target_label", "feature_set_id", "n_stations", "mae", "rmse", "spearman_observed_vs_predicted", "selected_params_summary", "no_s142_mae"], limit=12)}

ElasticNet top rows:

{markdown_table(elastic_top, ["target_label", "feature_set_id", "n_stations", "mae", "rmse", "spearman_observed_vs_predicted", "selected_params_summary", "no_s142_mae"], limit=12)}

ElasticNet is included only as a cautious sparse linear sensitivity model. It is not a promotion signal by itself under n=27.

## 8. Permutation null and bootstrap stability

{markdown_table(permutation, ["target_label", "model_family", "feature_set_id", "iterations", "observed_fixed_mae", "permutation_mae_p50", "observed_fixed_spearman", "permutation_spearman_p50", "permutation_p_value_mae_directional", "permutation_p_value_spearman_directional"], limit=8)}

Bootstrap coefficient stability is descriptive only:

{markdown_table(bootstrap.sort_values(["target_label", "same_sign_as_full_fraction"], ascending=[True, False]), ["target_label", "model_family", "feature_set_id", "feature_column", "full_data_standardized_coef", "same_sign_as_full_fraction", "selection_fraction_nonzero", "coef_ci_low", "coef_ci_high"], limit=16)}

## 9. S142 / S139 caveats

{markdown_table(s_caveat, ["station_id", "n_ge31", "low_support_warning_flag", "mean_context_adjusted_score_residual_c", "mean_context_adjusted_high_tail_residual_c", "score_stability_label", "high_tail_stability_label", "best_score_abs_error_c", "best_high_tail_abs_error_c"], limit=4)}

S142 remains the main high-tail underprediction caveat station. S139 remains low-support for station-specific conclusions, especially probability and threshold behavior. Any apparent station-context explanation must survive no-S142 checks before it can be considered promising.

## 10. A-L2.2 decision matrix

{markdown_table(decisions, ["target_label", "n_stations", "null_mae", "best_model_family", "best_feature_set_id", "best_mae", "mae_improvement_fraction", "best_spearman", "no_s142_mae_improvement_fraction", "permutation_p_value_mae_directional", "permutation_p_value_spearman_directional", "target_decision"], limit=8)}

Recommendation: {a_l2_2_recommendation(decision_status)}

## 11. Claim boundaries

- No station-adjusted WBGT is created.
- No station-context causal correction is claimed.
- No local 100 m WBGT is created.
- No operational forecast or public health warning claim is made.
- Station context is used only as residual explanation under station-level n=27 constraints.
"""


def chinese_doc(
    decision_status: str,
    input_table: pd.DataFrame,
    decisions: pd.DataFrame,
    permutation: pd.DataFrame,
    station_diag: pd.DataFrame,
) -> str:
    """Build the UTF-8 Chinese summary document."""
    s142 = station_diag.loc[station_diag["station_id"] == S142].iloc[0]
    s139 = station_diag.loc[station_diag["station_id"] == S139].iloc[0]
    return f"""# OpenHeat System A L2 站点残差范围化预检说明

生成日期：{date.today().isoformat()}
决策状态：`{decision_status}`

## 定位

本文件对应 A-L2.1c。它只检验 27 个站点层面的站点周边特征，是否能在留一站验证下解释 Level 1 之后仍存在的站点残差排序或幅度。它不是 Level 2 修正模型，不生成站点修正 WBGT，也不生成 100 m 本地 WBGT。

## 数据单位

输入表是一站一行，共 {len(input_table)} 行。`station_id` 只作为标识符，不作为预测变量。主要目标为：

- `mean_context_adjusted_score_residual_c`
- `mean_context_adjusted_high_tail_residual_c`

概率误差、漏报率和误报比例只作为诊断列，不作为主要建模目标。

## 验证方式

所有模型使用留一站验证。Ridge 和 ElasticNet 在每个外层训练折内再做内层留一站选择超参数。空模型为训练站点均值。没有使用小时行作为独立样本，也没有随机拆分。

## 结果摘要

{markdown_table(decisions, ["target_label", "n_stations", "null_mae", "best_model_family", "best_feature_set_id", "best_mae", "mae_improvement_fraction", "best_spearman", "target_decision"], limit=8)}

## 置换与稳定性

置换检验只针对每个主要目标的最佳合格非空模型，使用全数据留一站选出的固定超参数，作为预检级别的随机结构对照。

{markdown_table(permutation, ["target_label", "model_family", "feature_set_id", "iterations", "permutation_p_value_mae_directional", "permutation_p_value_spearman_directional"], limit=8)}

## S142 / S139 限制

S142：n_ge31={fmt(s142.get("n_ge31"), 0)}，score residual={fmt(s142.get("mean_context_adjusted_score_residual_c"), 4)}，high-tail residual={fmt(s142.get("mean_context_adjusted_high_tail_residual_c"), 4)}。

S139：n_ge31={fmt(s139.get("n_ge31"), 0)}，score residual={fmt(s139.get("mean_context_adjusted_score_residual_c"), 4)}，high-tail residual={fmt(s139.get("mean_context_adjusted_high_tail_residual_c"), 4)}。

S142 仍是高尾低估的主要警示站点。S139 的事件支持很低，不能用于推广站点级可靠性结论。

## 是否进入 A-L2.2

{a_l2_2_recommendation(decision_status)}

## 边界声明

- 不创建站点修正 WBGT。
- 不声称站点环境是因果修正项。
- 不创建本地 100 m WBGT。
- 不提出业务化或实时预报声明。
- 站点周边特征只用于站点层面的残差解释预检。
"""


def status_markdown(
    decision_status: str,
    result: ScopedPreflightResult,
    files_created: Sequence[Path],
) -> str:
    """Build lane status Markdown."""
    return f"""# A-L2.1c Status

Status: {decision_status}
Branch: {git_branch()}
Scope: station-level n=27 scoped residual preflight only; no station-adjusted WBGT, no local 100 m WBGT, no causal correction.

Commands run:
- python scripts/v11_l2_run_scoped_residual_preflight.py --config configs/v11/systema_l2_scoped_residual_preflight.yaml

Key results:
- n_stations used: {result.n_stations_used}
- best model / feature set by target: {result.best_models_by_target}
- null baseline comparison: {result.null_baseline_comparison}
- permutation / bootstrap headline: {result.permutation_bootstrap_headline}
- S142/S139 caveats: {result.s142_s139_caveats}
- A-L2.2 recommendation: {result.a_l2_2_recommendation}

Caveats:
- This is a station-level preflight model, not a promoted Level 2 correction model.
- Coefficients are descriptive and not causal.
- Probability-error summaries are diagnostic only.
- High-tail interpretation must respect low-support station flags.

Files created / modified:
{chr(10).join(f"- {rel(path)}" for path in files_created)}

Safe to commit: controlled config/script/docs and compact CSV/Markdown outputs after review.
Not safe to commit: raw spatial layers, rasters, archives, SOLWEIG/System B outputs, or large forecast/live CSVs.
"""


def write_outputs(
    paths: dict[str, Path],
    input_table: pd.DataFrame,
    feature_sets_df: pd.DataFrame,
    metrics: pd.DataFrame,
    predictions: pd.DataFrame,
    permutation: pd.DataFrame,
    bootstrap: pd.DataFrame,
    station_diag: pd.DataFrame,
    decisions: pd.DataFrame,
    report: str,
    cn_doc: str,
    status: str,
) -> list[Path]:
    """Write all configured compact outputs."""
    paths["dir"].mkdir(parents=True, exist_ok=True)
    paths["cn_doc"].parent.mkdir(parents=True, exist_ok=True)
    null_metrics = metrics.loc[metrics["model_family"] == "null_mean_baseline"]
    one_feature = metrics.loc[metrics["model_family"] == "one_feature_ridge"]
    ridge = metrics.loc[metrics["model_family"] == "ridge"]
    elastic = metrics.loc[metrics["model_family"] == "elasticnet"]

    outputs = [
        paths["input_table"],
        paths["feature_sets"],
        paths["null_baseline_metrics"],
        paths["one_feature_metrics"],
        paths["ridge_metrics"],
        paths["elasticnet_metrics"],
        paths["permutation_null"],
        paths["bootstrap_stability"],
        paths["predictions_loo"],
        paths["station_diagnostics"],
        paths["decision_matrix"],
        paths["report"],
        paths["status"],
        paths["cn_doc"],
    ]
    input_table.to_csv(paths["input_table"], index=False)
    feature_sets_df.to_csv(paths["feature_sets"], index=False)
    format_metric_outputs(null_metrics).to_csv(paths["null_baseline_metrics"], index=False)
    format_metric_outputs(one_feature).to_csv(paths["one_feature_metrics"], index=False)
    format_metric_outputs(ridge).to_csv(paths["ridge_metrics"], index=False)
    format_metric_outputs(elastic).to_csv(paths["elasticnet_metrics"], index=False)
    permutation.to_csv(paths["permutation_null"], index=False)
    bootstrap.to_csv(paths["bootstrap_stability"], index=False)
    predictions.to_csv(paths["predictions_loo"], index=False)
    station_diag.to_csv(paths["station_diagnostics"], index=False)
    decisions.to_csv(paths["decision_matrix"], index=False)
    paths["report"].write_text(report, encoding="utf-8")
    paths["status"].write_text(status, encoding="utf-8")
    paths["cn_doc"].write_text(cn_doc, encoding="utf-8")
    return outputs


def run_scoped_preflight(config_path: Path) -> ScopedPreflightResult:
    """Run the full A-L2.1c scoped residual preflight."""
    config = load_config(config_path)
    inputs = input_paths(config)
    paths = output_paths(config)
    residual_summary = read_csv(inputs["residual_summary"])
    probability_summary = read_csv(inputs["probability_summary"])
    stability = read_csv(inputs["residual_stability_bootstrap"])
    feature_wide = read_csv(inputs["feature_wide"])
    _candidate_set = read_csv(inputs["feature_candidate_set"])
    _association_screen = read_csv(inputs["residual_association_screen"])

    feature_sets = build_feature_sets(config)
    input_table = build_input_table(residual_summary, feature_wide, feature_sets, config)
    feature_sets_df = feature_sets_frame(feature_sets)
    metrics, predictions = evaluate_models(input_table, feature_sets, config)
    best_models = best_eligible_models(metrics)
    permutation = permutation_null(input_table, best_models, feature_sets, config)
    bootstrap = bootstrap_stability(input_table, best_models, feature_sets, config)
    metrics_with_perm = enrich_metrics_with_permutation(metrics, permutation)
    best_models_with_perm = best_eligible_models(metrics_with_perm)
    station_diag = station_diagnostics(input_table, probability_summary, stability, predictions, best_models_with_perm)
    decisions = decision_matrix(metrics_with_perm, permutation, best_models_with_perm, config)
    decision_status = overall_decision(decisions)
    recommendation = a_l2_2_recommendation(decision_status)

    null_metrics = metrics.loc[metrics["model_family"] == "null_mean_baseline"]
    one_feature = metrics.loc[metrics["model_family"] == "one_feature_ridge"]
    ridge = metrics.loc[metrics["model_family"] == "ridge"]
    elastic = metrics.loc[metrics["model_family"] == "elasticnet"]
    report = report_markdown(
        config,
        input_table,
        feature_sets_df,
        null_metrics,
        one_feature,
        ridge,
        elastic,
        permutation,
        bootstrap,
        station_diag,
        decisions,
        decision_status,
    )
    cn_text = chinese_doc(decision_status, input_table, decisions, permutation, station_diag)

    provisional = ScopedPreflightResult(
        decision_status=decision_status,
        n_stations_used=target_count_summary(input_table, config),
        best_models_by_target=best_models_summary(decisions),
        null_baseline_comparison=null_comparison_summary(decisions),
        permutation_bootstrap_headline=permutation_bootstrap_summary(permutation, bootstrap),
        s142_s139_caveats=s142_s139_summary(station_diag),
        a_l2_2_recommendation=recommendation,
        files_created=[],
        git_status_short="",
    )
    files_created = [
        paths["input_table"],
        paths["feature_sets"],
        paths["null_baseline_metrics"],
        paths["one_feature_metrics"],
        paths["ridge_metrics"],
        paths["elasticnet_metrics"],
        paths["permutation_null"],
        paths["bootstrap_stability"],
        paths["predictions_loo"],
        paths["station_diagnostics"],
        paths["decision_matrix"],
        paths["report"],
        paths["status"],
        paths["cn_doc"],
    ]
    status_text = status_markdown(decision_status, provisional, files_created)
    actual_files = write_outputs(
        paths,
        input_table,
        feature_sets_df,
        metrics,
        predictions,
        permutation,
        bootstrap,
        station_diag,
        decisions,
        report,
        cn_text,
        status_text,
    )
    return ScopedPreflightResult(
        decision_status=decision_status,
        n_stations_used=target_count_summary(input_table, config),
        best_models_by_target=best_models_summary(decisions),
        null_baseline_comparison=null_comparison_summary(decisions),
        permutation_bootstrap_headline=permutation_bootstrap_summary(permutation, bootstrap),
        s142_s139_caveats=s142_s139_summary(station_diag),
        a_l2_2_recommendation=recommendation,
        files_created=actual_files,
        git_status_short=git_status_short(),
    )
