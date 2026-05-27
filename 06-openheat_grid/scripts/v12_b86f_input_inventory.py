"""Inventory B8.6f compact inputs and provide shared closure helpers.

Inputs:
    configs/v12/systemb_b86f_surrogate_closure.yaml plus the compact CSV
    inputs declared there.
Outputs:
    outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_input_inventory.csv.
Saved metrics:
    Input existence, file size, row count, column count, key cell/hour/split
    counts, and missing required schema columns. This script reads compact CSV
    and Markdown metadata only; it performs no raster, QGIS, SOLWEIG,
    AOI-wide, WBGT, hazard, risk, B9, or System A/B coupling operation.
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
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "v12" / "systemb_b86f_surrogate_closure.yaml"
CLAIM_BOUNDARY = (
    "SOLWEIG-derived compact Tmrt-delta surrogate closure diagnostic only; not WBGT, "
    "risk, hazard_score, observed truth, causal feature importance, B9, AOI-wide "
    "prediction, Tmrt-to-WBGT conversion, or System A/B coupling."
)

INPUT_KEYS = [
    "b86d_oof_predictions_path",
    "b86d_combined_metrics_path",
    "b86d_metrics_by_split_path",
    "b86d_spatial_metrics_path",
    "b86d_typology_metrics_path",
    "b86d_anchor_diagnostics_path",
    "b86d_neutral_diagnostics_path",
    "b86d_worst_error_path",
    "b86e_spatial_failure_path",
    "b86e_spatial_bin_inventory_path",
    "b86e_typology_spatial_path",
    "b86e_anchor_context_path",
    "b86e_neutral_context_path",
    "b86e_feature_gap_register_path",
    "b86e_safe_feature_catalog_path",
    "b86e_safe_feature_probe_path",
    "b86e_n300_v1_path",
    "n150_feature_matrix_path",
    "candidate_universe_path",
    "f5_pairwise_label_path",
]

REQUIRED_COLUMNS = {
    "b86d_oof_predictions_path": [
        "cell_id",
        "forcing_day_id",
        "hour_sgt",
        "split_family",
        "true_delta",
        "pred_combined_delta",
        "true_class",
        "pred_stage1_class",
    ],
    "b86d_combined_metrics_path": ["split_family", "MAE", "Spearman_observed_vs_predicted", "top10pct_overlap"],
    "b86d_metrics_by_split_path": ["split_family", "MAE", "Spearman", "top10pct_overlap"],
    "b86d_spatial_metrics_path": ["split_name", "n_rows", "n_cells", "MAE", "Spearman_observed_vs_predicted"],
    "b86d_typology_metrics_path": ["typology_label", "n_rows", "n_cells", "MAE", "Spearman_observed_vs_predicted"],
    "b86d_anchor_diagnostics_path": ["cell_id", "split_family", "MAE", "failure_type"],
    "b86d_neutral_diagnostics_path": ["cell_id", "split_family", "false_promotion_rate", "failure_type"],
    "b86d_worst_error_path": ["cell_id", "split_family", "true_delta", "pred_combined_delta", "combined_abs_error"],
    "b86e_spatial_failure_path": [
        "spatial_bin",
        "n_cells",
        "mean_abs_error",
        "Spearman",
        "top10pct_overlap",
        "false_promotion_rate",
        "suspected_failure_type",
    ],
    "b86e_spatial_bin_inventory_path": [
        "spatial_bin",
        "cell_id",
        "typology",
        "mean_abs_error",
        "false_promotion_rate",
        "suspected_failure_type",
    ],
    "b86e_typology_spatial_path": ["typology", "spatial_bin", "n_cells", "failure_label"],
    "b86e_anchor_context_path": [
        "cell_id",
        "split_family",
        "spatial_bin",
        "typology",
        "mean_abs_error",
        "underprediction_rate_for_cooling",
    ],
    "b86e_neutral_context_path": ["cell_id", "split_family", "false_promotion_rate", "mean_abs_error"],
    "b86e_feature_gap_register_path": ["feature_family", "expected_benefit", "recommended_lane"],
    "b86e_safe_feature_catalog_path": ["feature_name", "predictor_allowed", "diagnostic_only"],
    "b86e_safe_feature_probe_path": ["feature_variant", "split_family", "Spearman", "top10pct_overlap", "variant_decision"],
    "b86e_n300_v1_path": ["cell_id", "expected_role", "spatial_bin", "typology"],
    "n150_feature_matrix_path": ["cell_id", "centroid_x", "centroid_y", "typology_label"],
    "candidate_universe_path": ["cell_id", "centroid_x", "centroid_y", "typology_label"],
    "f5_pairwise_label_path": ["cell_id", "forcing_day_id", "hour_sgt", "delta_tmrt_p90_c"],
}

FORBIDDEN_FEATURE_TOKENS = {
    "tmrt",
    "wbgt",
    "risk",
    "hazard",
    "score",
    "rank",
    "target",
    "output",
    "raster",
    "svfs",
    "tif",
    "tiff",
    "observed",
    "observation",
    "system_a",
    "source",
    "path",
    "status",
    "notes",
    "vulnerability",
    "exposure",
    "elderly",
    "children",
    "demographic",
    "bus_stop",
    "mrt",
    "sport",
    "hawker",
    "eldercare",
    "preschool",
    "node",
    "population",
    "lon",
    "lat",
    "centroid",
}


@dataclass(frozen=True)
class InventoryResult:
    """Compact input inventory result."""

    status: str
    files_checked: int
    missing_files: int
    schema_errors: int


def repo_path(path: str | Path) -> Path:
    """Resolve a project-relative path against the OpenHeat project directory."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def display_path(path: str | Path) -> str:
    """Return a stable project-relative path when possible."""
    resolved = repo_path(path)
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def load_config(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load the B8.6f YAML config."""
    with repo_path(config_path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("B8.6f config must parse to a mapping.")
    return config


def input_path(config: dict[str, Any], key: str) -> Path:
    """Resolve an input path from the config."""
    if key not in config:
        raise KeyError(f"Missing input config key: {key}")
    return repo_path(config[key])


def output_path(config: dict[str, Any], key: str) -> Path:
    """Resolve an output path from the config."""
    return repo_path(config["outputs"][key])


def ensure_output_dir(config: dict[str, Any]) -> Path:
    """Create and return the B8.6f output directory."""
    out_dir = output_path(config, "out_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def read_csv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read a UTF-8 compact CSV while preserving cell IDs."""
    options = {"dtype": {"cell_id": "string"}, "low_memory": False}
    options.update(kwargs)
    return pd.read_csv(repo_path(path), **options)


def write_csv(frame: pd.DataFrame, path: str | Path) -> None:
    """Write a UTF-8 CSV with stable parent directory creation."""
    destination = repo_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, encoding="utf-8")


def write_text(text: str, path: str | Path) -> None:
    """Write UTF-8 text with LF newlines."""
    destination = repo_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="\n")


def bool_value(value: Any) -> bool:
    """Coerce common CSV boolean spellings."""
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def as_float(value: Any, default: float = float("nan")) -> float:
    """Coerce a scalar to float with a stable default."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out


def fmt(value: Any, digits: int = 3) -> str:
    """Format compact report values."""
    numeric = as_float(value)
    if numeric == numeric:
        return f"{numeric:.{digits}f}"
    return str(value)


def md_table(frame: pd.DataFrame, columns: Sequence[str], max_rows: int = 12) -> str:
    """Create a compact Markdown table without external dependencies."""
    if frame.empty:
        return "_No rows._"
    view = frame.loc[:, [column for column in columns if column in frame.columns]].head(max_rows).copy()
    for column in view.columns:
        if pd.api.types.is_numeric_dtype(view[column]):
            view[column] = view[column].map(lambda item: "" if pd.isna(item) else fmt(item, 3))
    header = "| " + " | ".join(view.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    rows = ["| " + " | ".join(str(item) for item in row) + " |" for row in view.to_numpy()]
    return "\n".join([header, sep, *rows])


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
    """Compute cell-level overlap for the most negative true and predicted deltas."""
    if frame.empty or "cell_id" not in frame.columns:
        return float("nan")
    by_cell = frame.groupby("cell_id", as_index=False)[[true_col, pred_col]].mean(numeric_only=True).dropna()
    if by_cell.empty:
        return float("nan")
    k = max(1, int(math.ceil(fraction * int(by_cell["cell_id"].nunique()))))
    k = min(k, len(by_cell))
    true_top = set(by_cell.nsmallest(k, true_col)["cell_id"].astype(str))
    pred_top = set(by_cell.nsmallest(k, pred_col)["cell_id"].astype(str))
    return float(len(true_top & pred_top) / k)


def prediction_metrics(frame: pd.DataFrame, threshold: float) -> dict[str, Any]:
    """Summarize regression, ranking, and neutral-boundary safety metrics."""
    if frame.empty:
        return {
            "n_rows": 0,
            "n_cells": 0,
            "MAE": float("nan"),
            "Spearman": float("nan"),
            "top10pct_overlap": float("nan"),
            "neutral_false_promotion_rate": float("nan"),
            "anchor_underprediction_mae": float("nan"),
        }
    true = pd.to_numeric(frame["true_delta"], errors="coerce")
    pred = pd.to_numeric(frame["pred_combined_delta"], errors="coerce")
    valid = true.notna() & pred.notna()
    sub = frame.loc[valid].copy()
    true = true.loc[valid]
    pred = pred.loc[valid]
    true_neutral = true.abs() <= threshold
    pred_cooling = pred < -threshold
    false_promotion = true_neutral & pred_cooling
    anchor = sub.loc[sub.get("anchor_flag", pd.Series(False, index=sub.index)).map(bool_value)]
    anchor_under = float((pd.to_numeric(anchor["pred_combined_delta"], errors="coerce") - pd.to_numeric(anchor["true_delta"], errors="coerce")).abs().mean()) if not anchor.empty else float("nan")
    return {
        "n_rows": int(len(sub)),
        "n_cells": int(sub["cell_id"].nunique()) if "cell_id" in sub.columns else 0,
        "MAE": float((pred - true).abs().mean()) if len(sub) else float("nan"),
        "Spearman": finite_corr(true.to_numpy(dtype=float), pred.to_numpy(dtype=float), "spearman"),
        "top10pct_overlap": top_fraction_overlap(sub.assign(true_delta=true, pred_combined_delta=pred), "true_delta", "pred_combined_delta", 0.10),
        "neutral_false_promotion_rate": float(false_promotion.mean()) if len(sub) else float("nan"),
        "anchor_underprediction_mae": anchor_under,
    }


def current_label_cells(config: dict[str, Any]) -> set[str]:
    """Return current compact-labelled N150 cells from F5 labels."""
    labels = read_csv(input_path(config, "f5_pairwise_label_path"))
    return set(labels["cell_id"].astype(str).dropna().unique())


def add_spatial_bin(frame: pd.DataFrame, reference: pd.DataFrame | None = None) -> pd.DataFrame:
    """Attach deterministic east/west and north/south spatial bins."""
    out = frame.copy()
    if "spatial_bin" in out.columns:
        return out
    if "centroid_x" not in out.columns or "centroid_y" not in out.columns:
        out["spatial_bin"] = "unknown"
        return out
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


def candidate_universe(config: dict[str, Any]) -> pd.DataFrame:
    """Load one row per candidate-universe cell."""
    frame = read_csv(input_path(config, "candidate_universe_path"))
    return frame.drop_duplicates("cell_id").reset_index(drop=True)


def current_cell_features(config: dict[str, Any]) -> pd.DataFrame:
    """Return one compact feature row per current labelled cell."""
    current_cells = current_label_cells(config)
    universe = candidate_universe(config)
    current = universe.loc[universe["cell_id"].astype(str).isin(current_cells)].copy()
    if current["cell_id"].nunique() == len(current_cells):
        return add_spatial_bin(current).reset_index(drop=True)
    fallback = read_csv(input_path(config, "n150_feature_matrix_path")).drop_duplicates("cell_id")
    fallback = fallback.loc[fallback["cell_id"].astype(str).isin(current_cells)].copy()
    fallback = fallback.rename(columns={"typology_label": "typology_label"})
    return add_spatial_bin(fallback).reset_index(drop=True)


def safe_numeric_feature_columns(frame: pd.DataFrame, min_non_null: int = 10) -> list[str]:
    """Select non-coordinate compact numeric columns for feature-space diagnostics."""
    columns: list[str] = []
    metadata = {
        "cell_id",
        "candidate_id",
        "typology_label",
        "primary_role",
        "secondary_roles",
        "selection_tier",
        "selection_status",
        "eligible",
        "geometry_available",
        "human_qa_exclusion_reason",
    }
    for column in frame.columns:
        lower = column.lower()
        if lower in metadata:
            continue
        if any(token in lower for token in FORBIDDEN_FEATURE_TOKENS):
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        if int(values.notna().sum()) >= min_non_null:
            columns.append(column)
    return list(dict.fromkeys(columns))


def robust_scaled_values(frame: pd.DataFrame, features: Sequence[str]) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Robust-scale numeric features with median/IQR guards."""
    numeric = frame.loc[:, list(features)].apply(pd.to_numeric, errors="coerce").astype(float)
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
    top_n: int = 1,
    exclude_self: bool = False,
) -> pd.DataFrame:
    """Compute nearest reference rows under robust-scaled Euclidean distance."""
    common = [column for column in features if column in query.columns and column in reference.columns]
    common = safe_numeric_feature_columns(pd.concat([query[common], reference[common]], axis=0, ignore_index=True), 1)
    if not common or query.empty or reference.empty:
        return pd.DataFrame()
    combined = pd.concat([reference[common], query[common]], axis=0, ignore_index=True)
    _, med, scale = robust_scaled_values(combined, common)
    ref_values = ((reference[common].apply(pd.to_numeric, errors="coerce").fillna(med) - med) / scale).to_numpy(dtype=float)
    qry_values = ((query[common].apply(pd.to_numeric, errors="coerce").fillna(med) - med) / scale).to_numpy(dtype=float)
    ref_ids = reference["cell_id"].astype(str).to_numpy()
    rows: list[dict[str, Any]] = []
    for idx, values in enumerate(qry_values):
        query_id = str(query.iloc[idx]["cell_id"])
        distances = np.sqrt(np.sum((ref_values - values) ** 2, axis=1))
        order = np.argsort(distances)
        kept = 0
        for ref_idx in order:
            ref_id = str(ref_ids[ref_idx])
            if exclude_self and ref_id == query_id:
                continue
            rows.append(
                {
                    "cell_id": query_id,
                    "nearest_cell_id": ref_id,
                    "nearest_rank": kept + 1,
                    "feature_space_distance": float(distances[ref_idx]),
                    "feature_count": len(common),
                }
            )
            kept += 1
            if kept >= top_n:
                break
    return pd.DataFrame(rows)


def n150_distance_context(config: dict[str, Any]) -> pd.DataFrame:
    """Create per-current-cell non-coordinate feature-space distance context."""
    current = current_cell_features(config)
    features = safe_numeric_feature_columns(current, min_non_null=5)
    nearest = nearest_reference_rows(current, current, features, top_n=1, exclude_self=True)
    if nearest.empty:
        current["nearest_n150_cell"] = ""
        current["nearest_n150_distance"] = np.nan
        current["nearest_n150_distance_percentile"] = np.nan
        return current
    out = current.merge(
        nearest[["cell_id", "nearest_cell_id", "feature_space_distance"]].rename(
            columns={"nearest_cell_id": "nearest_n150_cell", "feature_space_distance": "nearest_n150_distance"}
        ),
        on="cell_id",
        how="left",
    )
    out["nearest_n150_distance_percentile"] = pd.to_numeric(out["nearest_n150_distance"], errors="coerce").rank(pct=True)
    return out


def input_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Build a compact input inventory table."""
    rows: list[dict[str, Any]] = []
    for key in INPUT_KEYS:
        path = input_path(config, key)
        row: dict[str, Any] = {
            "input_key": key,
            "path": display_path(path),
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
    """Write the B8.6f input inventory."""
    config = load_config(config_path)
    ensure_output_dir(config)
    inventory = input_inventory(config)
    write_csv(inventory, output_path(config, "input_inventory"))
    missing_files = int((~inventory["exists"].astype(bool)).sum())
    schema_errors = int(inventory["missing_required_columns"].astype(str).ne("").sum())
    status = "B86F_INPUTS_READY" if missing_files == 0 and schema_errors == 0 else "B86F_BLOCKED_INPUT"
    return InventoryResult(status=status, files_checked=len(inventory), missing_files=missing_files, schema_errors=schema_errors)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Inventory B8.6f compact inputs and required schema columns. Outputs "
            "a machine-readable CSV inventory under the B8.6f output directory."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
