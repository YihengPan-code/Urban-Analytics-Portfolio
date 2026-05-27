"""Inventory B8.6e compact inputs and provide shared closure helpers.

Inputs:
    configs/v12/systemb_b86e_spatial_feature_closure.yaml plus the compact
    CSV inputs declared there.
Outputs:
    outputs/v12_surrogate/b8_6e_spatial_feature_closure/b86e_input_inventory.csv
Saved metrics:
    Input existence, file size, row count, column count, key cell/hour/split
    counts, and missing required schema columns. This script reads compact CSV
    and Markdown metadata only; it performs no raster, QGIS, SOLWEIG, AOI-wide,
    WBGT, hazard, risk, B9, or System A/B coupling operation.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "v12" / "systemb_b86e_spatial_feature_closure.yaml"
CLAIM_BOUNDARY = (
    "SOLWEIG-derived compact Tmrt-delta surrogate diagnostic only; not WBGT, risk, "
    "observed truth, causal feature importance, B9, AOI-wide prediction, or System A/B coupling."
)
INPUT_KEYS = [
    "b86d_oof_predictions_path",
    "b86d_combined_metrics_path",
    "b86d_spatial_metrics_path",
    "b86d_typology_metrics_path",
    "b86d_anchor_diagnostics_path",
    "b86d_neutral_diagnostics_path",
    "b86d_worst_error_path",
    "b86c_safe_feature_catalog_path",
    "b86c_rejected_feature_catalog_path",
    "b86c_feature_group_registry_path",
    "b86c_feature_set_registry_path",
    "b86c_hardened_dataset_path",
    "f5_pairwise_label_path",
    "n150_feature_matrix_path",
    "candidate_universe_path",
]
REQUIRED_COLUMNS = {
    "b86d_oof_predictions_path": [
        "row_id",
        "cell_id",
        "forcing_day_id",
        "hour_sgt",
        "split_family",
        "split_name",
        "fold_id",
        "pred_combined_delta",
        "true_delta",
    ],
    "b86c_hardened_dataset_path": ["row_id", "cell_id", "forcing_day_id", "hour_sgt", "delta_tmrt_p90_c"],
    "f5_pairwise_label_path": ["cell_id", "forcing_day_id", "hour_sgt", "delta_tmrt_p90_c"],
    "n150_feature_matrix_path": ["cell_id", "centroid_x", "centroid_y", "typology_label"],
    "candidate_universe_path": ["cell_id", "centroid_x", "centroid_y", "typology_label"],
}


@dataclass(frozen=True)
class InventoryResult:
    """Compact input inventory result."""

    status: str
    files_checked: int
    missing_files: int
    schema_errors: int


def repo_path(path: str | Path) -> Path:
    """Resolve a project-relative path against the repository subdirectory."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def load_config(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load the B8.6e YAML config."""
    with repo_path(config_path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("B8.6e config must parse to a mapping.")
    return config


def input_path(config: dict[str, Any], key: str) -> Path:
    """Resolve an input path by config key."""
    if key not in config:
        raise KeyError(f"Missing input config key: {key}")
    return repo_path(config[key])


def output_path(config: dict[str, Any], key: str) -> Path:
    """Resolve an output path by config key."""
    return repo_path(config["outputs"][key])


def ensure_output_dir(config: dict[str, Any]) -> Path:
    """Create and return the B8.6e output directory."""
    out_dir = output_path(config, "out_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def read_csv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read a UTF-8 compact CSV while preserving cell IDs."""
    options = {"dtype": {"cell_id": "string"}, "low_memory": False}
    options.update(kwargs)
    return pd.read_csv(repo_path(path), **options)


def write_csv(frame: pd.DataFrame, path: str | Path) -> None:
    """Write a UTF-8 CSV with stable parent creation."""
    destination = repo_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, encoding="utf-8")


def write_text(text: str, path: str | Path) -> None:
    """Write UTF-8 Markdown/text with LF newlines."""
    destination = repo_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="\n")


def parse_pipe_list(value: Any) -> list[str]:
    """Parse a pipe-delimited registry field into a stable list."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [part for part in str(value).split("|") if part]


def bool_value(value: Any) -> bool:
    """Coerce common CSV boolean spellings."""
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def bool_series(series: pd.Series) -> pd.Series:
    """Coerce a pandas Series to booleans."""
    if series.dtype == bool:
        return series.fillna(False)
    return series.map(bool_value)


def numeric_columns(frame: pd.DataFrame, columns: Sequence[str]) -> list[str]:
    """Return selected columns that can be used as numeric diagnostics."""
    out: list[str] = []
    for column in columns:
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.notna().sum() > 0:
            out.append(column)
    return out


def forbidden_feature_name(column: str, config: dict[str, Any], include_coordinate: bool = False) -> bool:
    """Return True when a column violates the B8.6e feature contract."""
    contract = config.get("feature_contract", {})
    name = column.lower()
    allowed_categorical = {str(item).lower() for item in contract.get("allowed_categorical_features", [])}
    coordinate_columns = {str(item).lower() for item in contract.get("coordinate_diagnostic_columns", [])}
    if name in allowed_categorical or name == "hour_sgt":
        return False
    if name in coordinate_columns and not include_coordinate:
        return True
    if name in {str(item).lower() for item in contract.get("forbidden_predictor_columns", [])}:
        return True
    return any(str(token).lower() in name for token in contract.get("forbidden_predictor_tokens", []))


def safe_feature_catalog(config: dict[str, Any]) -> pd.DataFrame:
    """Load the B8.6c safe feature catalog."""
    return read_csv(input_path(config, "b86c_safe_feature_catalog_path"))


def safe_feature_columns(
    config: dict[str, Any],
    dataset: pd.DataFrame,
    include_coordinate: bool = False,
    include_categorical: bool = True,
) -> list[str]:
    """Return available safe feature columns from the B8.6c catalog."""
    catalog = safe_feature_catalog(config)
    if "predictor_allowed" in catalog.columns:
        catalog = catalog.loc[bool_series(catalog["predictor_allowed"])].copy()
    columns: list[str] = []
    for column in catalog.get("dataset_column", pd.Series(dtype=str)).astype(str):
        if column not in dataset.columns:
            continue
        if forbidden_feature_name(column, config, include_coordinate=include_coordinate):
            continue
        if not include_categorical and not pd.api.types.is_numeric_dtype(dataset[column]):
            values = pd.to_numeric(dataset[column], errors="coerce")
            if values.notna().sum() == 0:
                continue
        columns.append(column)
    if "hour_sgt" in dataset.columns and "hour_sgt" not in columns:
        columns.append("hour_sgt")
    return list(dict.fromkeys(columns))


def full_safe_compact_columns(config: dict[str, Any], dataset: pd.DataFrame, include_coordinate: bool = False) -> list[str]:
    """Return B8.6c full_safe_compact columns, falling back to all safe features."""
    registry_path = input_path(config, "b86c_feature_set_registry_path")
    if registry_path.exists():
        registry = read_csv(registry_path)
        row = registry.loc[registry["feature_set"].astype(str) == "full_safe_compact"]
        if not row.empty:
            field = "feature_columns" if "feature_columns" in registry.columns else "available_feature_columns"
            columns = parse_pipe_list(row.iloc[0][field])
            available = [
                column
                for column in columns
                if column in dataset.columns and not forbidden_feature_name(column, config, include_coordinate=include_coordinate)
            ]
            if available:
                return list(dict.fromkeys(available))
    return safe_feature_columns(config, dataset, include_coordinate=include_coordinate)


def selected_oof_predictions(config: dict[str, Any]) -> pd.DataFrame:
    """Load and filter B8.6d OOF predictions for the selected diagnostic workflow."""
    oof = read_csv(input_path(config, "b86d_oof_predictions_path"))
    workflow = config.get("selected_workflow", {})
    selected = oof.copy()
    for column, key in [
        ("feature_set", "feature_set"),
        ("classifier", "classifier"),
        ("regressor", "regressor"),
    ]:
        if column in selected.columns and key in workflow:
            selected = selected.loc[selected[column].astype(str) == str(workflow[key])].copy()
    if "neutral_threshold_c" in selected.columns and "neutral_threshold_c" in workflow:
        selected = selected.loc[
            pd.to_numeric(selected["neutral_threshold_c"], errors="coerce")
            == float(workflow["neutral_threshold_c"])
        ].copy()
    return selected


def cell_feature_frame(config: dict[str, Any]) -> pd.DataFrame:
    """Return one compact safe-feature row per N150 labelled cell."""
    dataset = read_csv(input_path(config, "b86c_hardened_dataset_path"))
    sort_cols = [column for column in ["cell_id", "forcing_day_id", "hour_sgt"] if column in dataset.columns]
    cell_frame = dataset.sort_values(sort_cols).drop_duplicates("cell_id").copy()
    return cell_frame.reset_index(drop=True)


def add_spatial_bin(frame: pd.DataFrame, reference: pd.DataFrame | None = None) -> pd.DataFrame:
    """Attach deterministic east/west and north/south spatial bins."""
    out = frame.copy()
    ref = reference if reference is not None else out
    x_mid = float(pd.to_numeric(ref["centroid_x"], errors="coerce").median())
    y_mid = float(pd.to_numeric(ref["centroid_y"], errors="coerce").median())
    x_values = pd.to_numeric(out["centroid_x"], errors="coerce")
    y_values = pd.to_numeric(out["centroid_y"], errors="coerce")
    out["spatial_bin"] = np.where(x_values <= x_mid, "west", "east") + "_" + np.where(
        y_values <= y_mid,
        "south",
        "north",
    )
    return out


def finite_corr(y_true: Sequence[float], y_pred: Sequence[float], method: str = "spearman") -> float:
    """Compute finite Pearson or Spearman correlation for non-degenerate inputs."""
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


def top_fraction_overlap(frame: pd.DataFrame, true_col: str, pred_col: str, fraction: float = 0.10) -> float:
    """Compute cell-level overlap for the most negative true/predicted deltas."""
    if frame.empty or "cell_id" not in frame.columns:
        return float("nan")
    by_cell = frame.groupby("cell_id", as_index=False)[[true_col, pred_col]].mean(numeric_only=True).dropna()
    if by_cell.empty:
        return float("nan")
    k = max(1, int(math.ceil(float(fraction) * int(by_cell["cell_id"].nunique()))))
    k = min(k, len(by_cell))
    true_top = set(by_cell.nsmallest(k, true_col)["cell_id"].astype(str))
    pred_top = set(by_cell.nsmallest(k, pred_col)["cell_id"].astype(str))
    return float(len(true_top & pred_top) / k)


def summarize_prediction_group(group: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    """Summarize regression/ranking and neutral-boundary failures for a group."""
    threshold = float(config["neutral_threshold_c"])
    true = pd.to_numeric(group["true_delta_tmrt_p90_c"], errors="coerce")
    pred = pd.to_numeric(group["predicted_delta_tmrt_p90_c"], errors="coerce")
    valid = true.notna() & pred.notna()
    sub = group.loc[valid].copy()
    true = true.loc[valid]
    pred = pred.loc[valid]
    true_neutral = true.abs() <= threshold
    true_cooling = true < -threshold
    predicted_neutral = sub["predicted_class"].astype(str).eq("neutral")
    predicted_cooling = sub["predicted_meaningful_cooling_flag"].map(bool_value)
    false_promotion = true_neutral & predicted_cooling.to_numpy()
    false_neutral = true_cooling & predicted_neutral.to_numpy()
    worst_cells = (
        sub.groupby("cell_id", as_index=False)["abs_error"].mean(numeric_only=True)
        .sort_values("abs_error", ascending=False)
        .head(5)
    )
    return {
        "n_rows": int(len(sub)),
        "n_cells": int(sub["cell_id"].nunique()) if "cell_id" in sub.columns else 0,
        "mean_abs_error": float((pred - true).abs().mean()) if len(sub) else float("nan"),
        "Spearman": finite_corr(true.to_numpy(dtype=float), pred.to_numpy(dtype=float), "spearman"),
        "top10pct_overlap": top_fraction_overlap(sub, "true_delta_tmrt_p90_c", "predicted_delta_tmrt_p90_c", 0.10),
        "neutral_accuracy": float((true_neutral.to_numpy() == predicted_neutral.to_numpy()).mean()) if len(sub) else float("nan"),
        "false_promotion_rate": float(false_promotion.mean()) if int(true_neutral.sum()) else float("nan"),
        "false_neutral_rate": float(false_neutral.mean()) if int(true_cooling.sum()) else float("nan"),
        "anchor_count": int(sub.loc[sub["anchor_flag"].map(bool_value), "cell_id"].nunique()) if "anchor_flag" in sub else 0,
        "neutral_count": int(sub.loc[sub["known_neutral_flag"].map(bool_value), "cell_id"].nunique()) if "known_neutral_flag" in sub else 0,
        "worst_cells": "|".join(worst_cells["cell_id"].astype(str).tolist()),
    }


def failure_label(metrics: dict[str, Any], config: dict[str, Any]) -> str:
    """Assign a compact suspected failure label from group metrics."""
    labels: list[str] = []
    if int(metrics.get("n_cells", 0)) < int(config.get("sample_support_low_cell_threshold", 10)):
        labels.append("sample-support-low")
    if float(metrics.get("anchor_count", 0) or 0) > 0 and float(metrics.get("mean_abs_error", 0) or 0) > 0.25:
        labels.append("anchor-underprediction")
    fp = metrics.get("false_promotion_rate")
    if fp == fp and float(fp) >= float(config["neutral_false_promotion_warn_threshold"]):
        labels.append("neutral-false-promotion")
    spearman = metrics.get("Spearman")
    top10 = metrics.get("top10pct_overlap")
    if (spearman == spearman and float(spearman) < float(config["spatial_failure_spearman_threshold"])) or (
        top10 == top10 and float(top10) < float(config["spatial_failure_top10_threshold"])
    ):
        labels.append("spatial-bin-out-of-domain")
    if not labels:
        labels.append("not-flagged")
    return "|".join(dict.fromkeys(labels))


def robust_scaled_values(frame: pd.DataFrame, features: Sequence[str]) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Robust-scale numeric features with median/IQR guards."""
    numeric = frame.loc[:, list(features)].apply(pd.to_numeric, errors="coerce")
    med = numeric.median(axis=0, skipna=True)
    q75 = numeric.quantile(0.75)
    q25 = numeric.quantile(0.25)
    scale = (q75 - q25).replace(0, np.nan)
    fallback = numeric.std(axis=0, skipna=True).replace(0, np.nan)
    scale = scale.fillna(fallback).fillna(1.0)
    scaled = (numeric.fillna(med) - med) / scale
    return scaled, med, scale


def nearest_reference_rows(
    query: pd.DataFrame,
    reference: pd.DataFrame,
    features: Sequence[str],
    query_id: str = "cell_id",
    reference_id: str = "cell_id",
    top_n: int = 1,
) -> pd.DataFrame:
    """Compute nearest reference rows under robust-scaled Euclidean distance."""
    common = [column for column in features if column in query.columns and column in reference.columns]
    common = numeric_columns(pd.concat([query[common], reference[common]], axis=0, ignore_index=True), common)
    if not common or query.empty or reference.empty:
        return pd.DataFrame()
    combined = pd.concat([reference[common], query[common]], axis=0, ignore_index=True)
    scaled, med, scale = robust_scaled_values(combined, common)
    ref_scaled = ((reference[common].apply(pd.to_numeric, errors="coerce").fillna(med) - med) / scale).to_numpy(dtype=float)
    qry_scaled = ((query[common].apply(pd.to_numeric, errors="coerce").fillna(med) - med) / scale).to_numpy(dtype=float)
    rows: list[dict[str, Any]] = []
    ref_ids = reference[reference_id].astype(str).to_numpy()
    for idx, values in enumerate(qry_scaled):
        distances = np.sqrt(np.sum((ref_scaled - values) ** 2, axis=1))
        order = np.argsort(distances)[:top_n]
        for rank, ref_idx in enumerate(order, start=1):
            rows.append(
                {
                    "cell_id": str(query.iloc[idx][query_id]),
                    "nearest_cell_id": str(ref_ids[ref_idx]),
                    "nearest_rank": rank,
                    "feature_space_distance": float(distances[ref_idx]),
                    "feature_count": len(common),
                }
            )
    return pd.DataFrame(rows)


def input_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Build a compact input inventory table."""
    rows: list[dict[str, Any]] = []
    for key in INPUT_KEYS:
        path = input_path(config, key)
        row: dict[str, Any] = {
            "input_key": key,
            "path": str(path.relative_to(PROJECT_ROOT) if path.is_relative_to(PROJECT_ROOT) else path),
            "exists": path.exists(),
            "file_size_bytes": path.stat().st_size if path.exists() else 0,
            "row_count": np.nan,
            "column_count": np.nan,
            "unique_cells": np.nan,
            "forcing_day_count": np.nan,
            "hour_count": np.nan,
            "split_family_count": np.nan,
            "missing_required_columns": "",
            "claim_boundary": CLAIM_BOUNDARY,
        }
        if path.exists() and path.suffix.lower() == ".csv":
            frame = read_csv(path)
            row["row_count"] = int(len(frame))
            row["column_count"] = int(len(frame.columns))
            if "cell_id" in frame.columns:
                row["unique_cells"] = int(frame["cell_id"].nunique())
            if "forcing_day_id" in frame.columns:
                row["forcing_day_count"] = int(frame["forcing_day_id"].nunique())
            if "hour_sgt" in frame.columns:
                row["hour_count"] = int(pd.to_numeric(frame["hour_sgt"], errors="coerce").nunique())
            if "split_family" in frame.columns:
                row["split_family_count"] = int(frame["split_family"].nunique())
            missing = [column for column in REQUIRED_COLUMNS.get(key, []) if column not in frame.columns]
            row["missing_required_columns"] = "|".join(missing)
        rows.append(row)
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> InventoryResult:
    """Write the B8.6e input inventory."""
    config = load_config(config_path)
    ensure_output_dir(config)
    inventory = input_inventory(config)
    write_csv(inventory, output_path(config, "input_inventory"))
    missing_files = int((~inventory["exists"].astype(bool)).sum())
    schema_errors = int(inventory["missing_required_columns"].astype(str).ne("").sum())
    status = "B86E_INPUTS_READY" if missing_files == 0 and schema_errors == 0 else "B86E_BLOCKED_INPUT"
    return InventoryResult(status=status, files_checked=len(inventory), missing_files=missing_files, schema_errors=schema_errors)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Inventory B8.6e compact input files and required schema columns. "
            "Outputs a machine-readable CSV inventory under the B8.6e output directory."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
