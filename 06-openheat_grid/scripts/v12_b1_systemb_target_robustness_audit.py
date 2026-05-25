"""Sprint B1 System B target robustness audit.

Inputs:
    - Existing CSV/MD summary, config, provenance, and grid metadata files under
      outputs/v12_solweig_typology_pilot/, configs/v12/, data/grid/v12/, and
      selected docs. Non-CSV/MD metadata paths may be listed in the inventory by
      existence only, but are not parsed.
    - Core 8 base and overhead CSV summaries:
      tmrt_cell_summary_long.csv and modifier_targets_long.csv.

Outputs:
    - outputs/v12_systemb_target_robustness/systemb_input_inventory.csv
    - outputs/v12_systemb_target_robustness/normalized_tmrt_targets_long.csv
    - outputs/v12_systemb_target_robustness/normalized_modifier_targets_long.csv
    - outputs/v12_systemb_target_robustness/target_availability_matrix.csv
    - outputs/v12_systemb_target_robustness/target_descriptive_stats.csv
    - outputs/v12_systemb_target_robustness/target_rank_correlation.csv
    - outputs/v12_systemb_target_robustness/target_topk_overlap.csv
    - outputs/v12_systemb_target_robustness/base_vs_overhead_target_sensitivity.csv
    - outputs/v12_systemb_target_robustness/base_vs_overhead_sensitivity_summary.csv
    - outputs/v12_systemb_target_robustness/hour_stability_rank_correlation.csv
    - outputs/v12_systemb_target_robustness/hour_stability_topk_overlap.csv
    - outputs/v12_systemb_target_robustness/hour_stability_consistent_cells.csv
    - outputs/v12_systemb_target_robustness/typology_interpretability_audit.csv
    - outputs/v12_systemb_target_robustness/systemb_target_decision_matrix.csv
    - outputs/v12_systemb_target_robustness/systemb_target_robustness_report.md

Saved metrics:
    - Target availability by scenario/hour/metric.
    - Descriptive statistics by scenario/hour/metric.
    - Spearman ranking correlations and top-k overlaps across target metrics.
    - Base-vs-overhead target deltas and summaries.
    - Cross-hour ranking correlations, top-k overlaps, and consistent top/bottom cells.
    - Typology-level interpretability flags where labels are available.
    - Target decision roles and recommended status.

This script does not read rasters or .tif/.tiff files, run SOLWEIG, run QGIS,
train models, create a surrogate, create risk_score, create local_wbgt_c, or
perform System A/B coupling.
"""

from __future__ import annotations

import argparse
import itertools
import math
from pathlib import Path
from typing import Any

import pandas as pd


OUTPUT_SUBDIR = Path("outputs/v12_systemb_target_robustness")
PILOT_ROOT = Path("outputs/v12_solweig_typology_pilot")

SUMMARY_DIRS = [
    PILOT_ROOT / "core8_base_summary",
    PILOT_ROOT / "core8_overhead_summary",
    PILOT_ROOT / "overhead_smoke_summary",
    PILOT_ROOT / "wave1_base_summary",
    PILOT_ROOT / "wave0_summary",
    PILOT_ROOT / "provenance",
]
METADATA_DIRS = [Path("configs/v12"), Path("data/grid/v12")]
OPTIONAL_DOCS = [
    Path("docs/v12/OpenHeat_SystemB_architecture_discussion_record_CN.md"),
    Path("docs/v11/SystemA_AOI_temporal_aggregation_design_CN.md"),
    Path("docs/v11/SystemA_Level1_Interim_Model_Card_CN.md"),
]

KEY_INPUTS = [
    PILOT_ROOT / "core8_base_summary/tmrt_cell_summary_long.csv",
    PILOT_ROOT / "core8_base_summary/modifier_targets_long.csv",
    PILOT_ROOT / "core8_overhead_summary/tmrt_cell_summary_long.csv",
    PILOT_ROOT / "core8_overhead_summary/modifier_targets_long.csv",
]

CORE8_TMRT_FILES = {
    "core8_base": PILOT_ROOT / "core8_base_summary/tmrt_cell_summary_long.csv",
    "core8_overhead": PILOT_ROOT / "core8_overhead_summary/tmrt_cell_summary_long.csv",
}
CORE8_MODIFIER_FILES = {
    "core8_base": PILOT_ROOT / "core8_base_summary/modifier_targets_long.csv",
    "core8_overhead": PILOT_ROOT / "core8_overhead_summary/modifier_targets_long.csv",
}

CANONICAL_COLUMNS = [
    "source_dataset",
    "source_file",
    "run_id",
    "cell_id",
    "typology_label",
    "hour",
    "hour_label",
    "scenario",
    "tmrt_mean_c",
    "tmrt_p50_c",
    "tmrt_p75_c",
    "tmrt_p90_c",
    "tmrt_p95_c",
    "tmrt_max_c",
    "delta_tmrt_p90_c",
    "m_rad_pct",
    "m_rad_robust01",
    "valid_pixel_count",
    "valid_pixel_fraction",
    "qa_status",
    "qa_notes",
]
TARGET_METRICS = [
    "tmrt_mean_c",
    "tmrt_p75_c",
    "tmrt_p90_c",
    "tmrt_p95_c",
    "tmrt_max_c",
    "delta_tmrt_p90_c",
    "m_rad_pct",
]
BASE_SCENARIO = "base"
OVERHEAD_SCENARIO = "overhead_as_canopy"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Audit existing System B SOLWEIG-derived summary targets for "
            "availability, ranking robustness, scenario sensitivity, hour "
            "stability, and typology interpretability."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_SUBDIR,
        help="Output directory for B1 audit artifacts.",
    )
    return parser.parse_args()


def safe_rel(path: Path, root: Path) -> str:
    """Return a stable repository-relative path string when possible."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def ensure_output_dir(output_dir: Path) -> None:
    """Create the audit output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)


def infer_scenario_from_path(path: Path) -> str:
    """Infer scenario from path components or filename."""
    text = path.as_posix().lower()
    if "core8_overhead" in text or "overhead_as_canopy" in text:
        return OVERHEAD_SCENARIO
    if "core8_base" in text or "wave1_base" in text or "wave0" in text:
        return BASE_SCENARIO
    if "overhead_smoke" in text:
        return "overhead_smoke"
    return ""


def threshold_columns(columns: list[str]) -> list[str]:
    """Find threshold-area or threshold-pixel columns."""
    hits: list[str] = []
    for column in columns:
        c = column.lower()
        if (
            c.startswith("pct_pixels_ge_")
            or c.startswith("pct_area_above")
            or c.startswith("area_above")
            or ("threshold" in c and ("pct" in c or "area" in c or "pixel" in c))
        ):
            hits.append(column)
    return hits


def typology_columns(columns: list[str]) -> list[str]:
    """Find typology or label columns."""
    hits: list[str] = []
    for column in columns:
        c = column.lower()
        if "typology" in c or "label" in c or "pilot_tier" in c:
            hits.append(column)
    return hits


def inspect_file(path: Path, root: Path) -> dict[str, Any]:
    """Inspect one CSV/MD/JSON/TXT file without reading raster content."""
    exists = path.exists()
    row: dict[str, Any] = {
        "path": safe_rel(path, root),
        "exists": exists,
        "row_count": "",
        "columns": "",
        "scenario_inferred": infer_scenario_from_path(path),
        "contains_cell_id": False,
        "contains_hour": False,
        "contains_tmrt_mean": False,
        "contains_tmrt_p50": False,
        "contains_tmrt_p75": False,
        "contains_tmrt_p90": False,
        "contains_tmrt_p95": False,
        "contains_tmrt_max": False,
        "contains_delta_tmrt_p90": False,
        "contains_m_rad_pct": False,
        "contains_threshold_area_fields": False,
        "contains_typology_label_fields": False,
        "notes": "",
    }
    if not exists:
        row["notes"] = "missing"
        return row

    suffix = path.suffix.lower()
    if suffix == ".csv":
        try:
            df = pd.read_csv(path)
            columns = list(df.columns)
            lower = {c.lower(): c for c in columns}
            row.update(
                {
                    "row_count": len(df),
                    "columns": "|".join(columns),
                    "contains_cell_id": "cell_id" in lower,
                    "contains_hour": bool({"hour", "hour_sgt", "hour_label"} & set(lower)),
                    "contains_tmrt_mean": "tmrt_mean_c" in lower or "tmrt_mean" in lower,
                    "contains_tmrt_p50": "tmrt_p50_c" in lower or "tmrt_p50" in lower,
                    "contains_tmrt_p75": "tmrt_p75_c" in lower or "tmrt_p75" in lower,
                    "contains_tmrt_p90": "tmrt_p90_c" in lower or "tmrt_p90" in lower,
                    "contains_tmrt_p95": "tmrt_p95_c" in lower or "tmrt_p95" in lower,
                    "contains_tmrt_max": "tmrt_max_c" in lower or "tmrt_max" in lower,
                    "contains_delta_tmrt_p90": "delta_tmrt_p90_c" in lower
                    or "delta_tmrt_p90" in lower,
                    "contains_m_rad_pct": "m_rad_pct" in lower,
                    "contains_threshold_area_fields": bool(threshold_columns(columns)),
                    "contains_typology_label_fields": bool(typology_columns(columns)),
                }
            )
        except Exception as exc:  # pragma: no cover - defensive inventory path.
            row["notes"] = f"csv_read_error: {exc}"
    elif suffix == ".md":
        text = path.read_text(encoding="utf-8", errors="replace")
        row["row_count"] = text.count("\n") + (1 if text else 0)
        row["notes"] = "text file; row_count is line_count"
    elif suffix in {".json", ".txt", ".xlsx"}:
        row["notes"] = "exists; non-CSV/MD metadata not parsed"
    else:
        row["notes"] = f"not inspected suffix {suffix}"
    return row


def inventory_paths(root: Path) -> list[Path]:
    """Build the explicit inventory path list."""
    paths: list[Path] = []
    for rel_dir in [*SUMMARY_DIRS, *METADATA_DIRS]:
        full_dir = root / rel_dir
        if full_dir.exists():
            for path in sorted(full_dir.iterdir()):
                if path.is_file() and path.suffix.lower() in {".csv", ".md", ".json", ".txt", ".xlsx"}:
                    paths.append(path)
        else:
            paths.append(full_dir)
    paths.extend(root / p for p in OPTIONAL_DOCS)
    for key in KEY_INPUTS:
        key_path = root / key
        if key_path not in paths:
            paths.append(key_path)
    return sorted(set(paths))


def write_inventory(root: Path, output_dir: Path) -> pd.DataFrame:
    """Write the input inventory CSV."""
    rows = [inspect_file(path, root) for path in inventory_paths(root)]
    inventory = pd.DataFrame(rows)
    inventory.to_csv(output_dir / "systemb_input_inventory.csv", index=False)
    return inventory


def missing_key_inputs(root: Path) -> list[Path]:
    """Return missing required Core 8 summary inputs."""
    return [root / path for path in KEY_INPUTS if not (root / path).exists()]


def coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Convert available columns to numeric values."""
    out = df.copy()
    for column in columns:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def standardize_summary(df: pd.DataFrame, source_file: Path, source_dataset: str, root: Path) -> pd.DataFrame:
    """Standardize target summary columns while preserving only audit-safe fields."""
    out = pd.DataFrame(index=df.index)
    out["source_dataset"] = source_dataset
    out["source_file"] = safe_rel(source_file, root)
    out["run_id"] = df["run_id"] if "run_id" in df.columns else ""
    out["cell_id"] = df["cell_id"] if "cell_id" in df.columns else ""
    out["typology_label"] = df["typology_label"] if "typology_label" in df.columns else ""
    if "hour" in df.columns:
        out["hour"] = df["hour"]
    elif "hour_sgt" in df.columns:
        out["hour"] = df["hour_sgt"]
    elif "hour_label" in df.columns:
        out["hour"] = df["hour_label"].astype(str).str.extract(r"(\d+)", expand=False)
    else:
        out["hour"] = pd.NA
    out["hour_label"] = out["hour"].apply(lambda x: f"h{int(x):02d}" if pd.notna(x) else "")
    out["scenario"] = df["scenario_id"] if "scenario_id" in df.columns else infer_scenario_from_path(source_file)

    alias_map = {
        "tmrt_mean_c": ["tmrt_mean_c", "tmrt_mean"],
        "tmrt_p50_c": ["tmrt_p50_c", "tmrt_p50"],
        "tmrt_p75_c": ["tmrt_p75_c", "tmrt_p75"],
        "tmrt_p90_c": ["tmrt_p90_c", "tmrt_p90"],
        "tmrt_p95_c": ["tmrt_p95_c", "tmrt_p95"],
        "tmrt_max_c": ["tmrt_max_c", "tmrt_max"],
        "delta_tmrt_p90_c": ["delta_tmrt_p90_c", "delta_tmrt_p90"],
        "m_rad_pct": ["m_rad_pct"],
        "m_rad_robust01": ["m_rad_robust01"],
        "valid_pixel_count": ["valid_pixel_count", "n_valid_pixels"],
        "valid_pixel_fraction": ["valid_pixel_fraction"],
        "qa_status": ["qa_status"],
        "qa_notes": ["qa_notes"],
    }
    for canonical, aliases in alias_map.items():
        source = next((name for name in aliases if name in df.columns), None)
        out[canonical] = df[source] if source else pd.NA

    for column in threshold_columns(list(df.columns)):
        out[column] = df[column]

    numeric_cols = [
        "hour",
        "tmrt_mean_c",
        "tmrt_p50_c",
        "tmrt_p75_c",
        "tmrt_p90_c",
        "tmrt_p95_c",
        "tmrt_max_c",
        "delta_tmrt_p90_c",
        "m_rad_pct",
        "m_rad_robust01",
        "valid_pixel_count",
        "valid_pixel_fraction",
        *threshold_columns(list(df.columns)),
    ]
    out = coerce_numeric(out, numeric_cols)
    ordered = [c for c in CANONICAL_COLUMNS if c in out.columns]
    extras = [c for c in out.columns if c not in ordered]
    return out[ordered + extras]


def load_core8_tables(root: Path, output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and normalize Core 8 base and overhead target tables."""
    tmrt_frames: list[pd.DataFrame] = []
    modifier_frames: list[pd.DataFrame] = []
    for dataset, rel_path in CORE8_TMRT_FILES.items():
        path = root / rel_path
        if path.exists():
            tmrt_frames.append(standardize_summary(pd.read_csv(path), path, dataset, root))
    for dataset, rel_path in CORE8_MODIFIER_FILES.items():
        path = root / rel_path
        if path.exists():
            modifier_frames.append(standardize_summary(pd.read_csv(path), path, dataset, root))

    tmrt = pd.concat(tmrt_frames, ignore_index=True) if tmrt_frames else pd.DataFrame(columns=CANONICAL_COLUMNS)
    modifier = (
        pd.concat(modifier_frames, ignore_index=True)
        if modifier_frames
        else pd.DataFrame(columns=CANONICAL_COLUMNS)
    )
    tmrt.to_csv(output_dir / "normalized_tmrt_targets_long.csv", index=False)
    modifier.to_csv(output_dir / "normalized_modifier_targets_long.csv", index=False)
    return tmrt, modifier


def available_metric_columns(df: pd.DataFrame) -> list[str]:
    """Return target metrics that have at least one non-null value."""
    metrics = [m for m in TARGET_METRICS if m in df.columns and df[m].notna().any()]
    metrics.extend(c for c in threshold_columns(list(df.columns)) if c not in metrics and df[c].notna().any())
    return metrics


def target_availability(df: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    """Write target availability by scenario/hour/metric."""
    metrics = [m for m in TARGET_METRICS if m in df.columns] + threshold_columns(list(df.columns))
    rows: list[dict[str, Any]] = []
    for (scenario, hour), group in df.groupby(["scenario", "hour"], dropna=False):
        for metric in metrics:
            series = group[metric] if metric in group.columns else pd.Series(dtype="float64")
            rows.append(
                {
                    "scenario": scenario,
                    "hour": hour,
                    "metric": metric,
                    "available": metric in group.columns and series.notna().any(),
                    "n_rows": len(group),
                    "n_cells": group["cell_id"].nunique() if "cell_id" in group.columns else 0,
                    "non_missing_count": int(series.notna().sum()) if metric in group.columns else 0,
                    "missing_count": int(series.isna().sum()) if metric in group.columns else len(group),
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(output_dir / "target_availability_matrix.csv", index=False)
    return out


def describe_targets(df: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    """Write descriptive target statistics by scenario/hour/metric."""
    rows: list[dict[str, Any]] = []
    for (scenario, hour), group in df.groupby(["scenario", "hour"], dropna=False):
        for metric in available_metric_columns(group):
            series = pd.to_numeric(group[metric], errors="coerce")
            valid_pixel = (
                pd.to_numeric(group["valid_pixel_count"], errors="coerce")
                if "valid_pixel_count" in group.columns
                else pd.Series(dtype="float64")
            )
            rows.append(
                {
                    "scenario": scenario,
                    "hour": hour,
                    "metric": metric,
                    "n_cells": group.loc[series.notna(), "cell_id"].nunique(),
                    "mean": series.mean(),
                    "median": series.median(),
                    "std": series.std(),
                    "min": series.min(),
                    "p25": series.quantile(0.25),
                    "p75": series.quantile(0.75),
                    "max": series.max(),
                    "missing_count": int(series.isna().sum()),
                    "valid_pixel_count_mean": valid_pixel.mean() if not valid_pixel.empty else pd.NA,
                    "valid_pixel_count_min": valid_pixel.min() if not valid_pixel.empty else pd.NA,
                    "valid_pixel_count_max": valid_pixel.max() if not valid_pixel.empty else pd.NA,
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(output_dir / "target_descriptive_stats.csv", index=False)
    return out


def spearman_rank_corr(frame: pd.DataFrame, metric_a: str, metric_b: str) -> tuple[float | None, int]:
    """Compute Spearman rank correlation with pandas ranks."""
    sub = frame[["cell_id", metric_a, metric_b]].dropna()
    sub = sub.drop_duplicates(subset=["cell_id"])
    n_cells = sub["cell_id"].nunique()
    if n_cells < 2:
        return None, n_cells
    ranks = sub[[metric_a, metric_b]].rank(method="average")
    value = ranks[metric_a].corr(ranks[metric_b], method="pearson")
    if pd.isna(value):
        return None, n_cells
    return float(value), n_cells


def rank_correlation(df: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    """Write target ranking correlations within scenario/hour."""
    rows: list[dict[str, Any]] = []
    for (scenario, hour), group in df.groupby(["scenario", "hour"], dropna=False):
        metrics = available_metric_columns(group)
        for metric_a, metric_b in itertools.combinations(metrics, 2):
            corr, n_cells = spearman_rank_corr(group, metric_a, metric_b)
            rows.append(
                {
                    "scenario": scenario,
                    "hour": hour,
                    "metric_a": metric_a,
                    "metric_b": metric_b,
                    "spearman_r": corr,
                    "n_cells": n_cells,
                    "caveat": "n_cells < 8; small-sample diagnostic" if n_cells < 8 else (
                        "Core 8 diagnostic sample" if n_cells == 8 else ""
                    ),
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(output_dir / "target_rank_correlation.csv", index=False)
    return out


def top_k_size(n_cells: int) -> int:
    """Return top-k size for Core 8 or larger samples."""
    if n_cells <= 8:
        return min(3, n_cells)
    return int(math.ceil(0.25 * n_cells))


def top_cells(frame: pd.DataFrame, metric: str, k: int, ascending: bool = False) -> list[str]:
    """Return top or bottom cell ids for a metric."""
    sub = frame[["cell_id", metric]].dropna().drop_duplicates(subset=["cell_id"])
    sub = sub.sort_values([metric, "cell_id"], ascending=[ascending, True])
    return [str(x) for x in sub.head(k)["cell_id"].tolist()]


def topk_overlap(df: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    """Write top-k overlap across target metrics within scenario/hour."""
    rows: list[dict[str, Any]] = []
    for (scenario, hour), group in df.groupby(["scenario", "hour"], dropna=False):
        metrics = available_metric_columns(group)
        n_cells_total = group["cell_id"].nunique()
        k = top_k_size(n_cells_total)
        for metric_a, metric_b in itertools.combinations(metrics, 2):
            cells_a = set(top_cells(group, metric_a, k))
            cells_b = set(top_cells(group, metric_b, k))
            union = cells_a | cells_b
            rows.append(
                {
                    "scenario": scenario,
                    "hour": hour,
                    "metric_a": metric_a,
                    "metric_b": metric_b,
                    "top_k": k,
                    "top_k_cells_metric_a": "|".join(sorted(cells_a)),
                    "top_k_cells_metric_b": "|".join(sorted(cells_b)),
                    "overlap_count": len(cells_a & cells_b),
                    "jaccard_overlap": len(cells_a & cells_b) / len(union) if union else pd.NA,
                    "n_cells": n_cells_total,
                    "caveat": "Core 8 small-sample diagnostic only" if n_cells_total <= 8 else "",
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(output_dir / "target_topk_overlap.csv", index=False)
    return out


def scenario_sensitivity(df: pd.DataFrame, output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write base vs overhead target deltas and summaries."""
    base = df[df["scenario"] == BASE_SCENARIO].copy()
    overhead = df[df["scenario"] == OVERHEAD_SCENARIO].copy()
    metrics = available_metric_columns(df)
    rows: list[dict[str, Any]] = []
    if not base.empty and not overhead.empty:
        keep = ["cell_id", "hour", "typology_label", *metrics]
        merged = base[keep].merge(
            overhead[keep],
            on=["cell_id", "hour"],
            suffixes=("_base", "_overhead"),
            how="inner",
        )
        for _, item in merged.iterrows():
            row: dict[str, Any] = {
                "cell_id": item["cell_id"],
                "hour": item["hour"],
                "typology_label_base": item.get("typology_label_base", ""),
                "typology_label_overhead": item.get("typology_label_overhead", ""),
            }
            for metric in metrics:
                base_col = f"{metric}_base"
                overhead_col = f"{metric}_overhead"
                row[f"base_{metric}"] = item.get(base_col, pd.NA)
                row[f"overhead_{metric}"] = item.get(overhead_col, pd.NA)
                row[f"delta_overhead_minus_base_{metric}"] = (
                    item.get(overhead_col, pd.NA) - item.get(base_col, pd.NA)
                    if pd.notna(item.get(overhead_col, pd.NA)) and pd.notna(item.get(base_col, pd.NA))
                    else pd.NA
                )
            rows.append(row)
    detail = pd.DataFrame(rows)

    rename_map = {
        "base_tmrt_p90_c": "base_tmrt_p90_c",
        "overhead_tmrt_p90_c": "overhead_tmrt_p90_c",
        "delta_overhead_minus_base_tmrt_p90_c": "delta_overhead_minus_base_p90",
        "base_m_rad_pct": "base_m_rad_pct",
        "overhead_m_rad_pct": "overhead_m_rad_pct",
        "delta_overhead_minus_base_m_rad_pct": "delta_m_rad_pct",
    }
    for old, new in rename_map.items():
        if old in detail.columns and old != new:
            detail[new] = detail[old]
    detail.to_csv(output_dir / "base_vs_overhead_target_sensitivity.csv", index=False)

    summary_rows: list[dict[str, Any]] = []
    if not detail.empty:
        for metric in metrics:
            delta_col = f"delta_overhead_minus_base_{metric}"
            if delta_col not in detail.columns:
                continue
            for hour_value, group in itertools.chain([("all", detail)], detail.groupby("hour", dropna=False)):
                delta = pd.to_numeric(group[delta_col], errors="coerce")
                cooling = group.loc[delta < 0].sort_values(delta_col).head(3)
                warming = group.loc[delta > 0].sort_values(delta_col, ascending=False).head(3)
                summary_rows.append(
                    {
                        "metric": metric,
                        "hour": hour_value,
                        "n_pairs": int(delta.notna().sum()),
                        "mean_delta": delta.mean(),
                        "median_delta": delta.median(),
                        "min_delta": delta.min(),
                        "max_delta": delta.max(),
                        "count_cells_cooled": int((delta < 0).sum()),
                        "count_cells_warmed": int((delta > 0).sum()),
                        "largest_cooling_cells": "|".join(cooling["cell_id"].astype(str).tolist()),
                        "largest_warming_cells": "|".join(warming["cell_id"].astype(str).tolist()),
                    }
                )
    else:
        summary_rows.append(
            {
                "metric": "all",
                "hour": "all",
                "n_pairs": 0,
                "mean_delta": pd.NA,
                "median_delta": pd.NA,
                "min_delta": pd.NA,
                "max_delta": pd.NA,
                "count_cells_cooled": 0,
                "count_cells_warmed": 0,
                "largest_cooling_cells": "",
                "largest_warming_cells": "",
                "notes": "base and overhead could not be matched by cell_id/hour",
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(output_dir / "base_vs_overhead_sensitivity_summary.csv", index=False)
    return detail, summary


def hour_stability(df: pd.DataFrame, output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Write cross-hour rank correlation, top-k overlap, and consistent cells."""
    corr_rows: list[dict[str, Any]] = []
    overlap_rows: list[dict[str, Any]] = []
    consistent_rows: list[dict[str, Any]] = []
    for scenario, scenario_group in df.groupby("scenario", dropna=False):
        metrics = available_metric_columns(scenario_group)
        hours = sorted(h for h in scenario_group["hour"].dropna().unique())
        for metric in metrics:
            hour_top_sets: dict[Any, set[str]] = {}
            hour_bottom_sets: dict[Any, set[str]] = {}
            for hour in hours:
                hour_group = scenario_group[scenario_group["hour"] == hour]
                n_cells = hour_group["cell_id"].nunique()
                k = top_k_size(n_cells)
                hour_top_sets[hour] = set(top_cells(hour_group, metric, k))
                hour_bottom_sets[hour] = set(top_cells(hour_group, metric, k, ascending=True))
            for hour_a, hour_b in itertools.combinations(hours, 2):
                group_a = scenario_group[scenario_group["hour"] == hour_a][["cell_id", metric]].rename(
                    columns={metric: f"{metric}_a"}
                )
                group_b = scenario_group[scenario_group["hour"] == hour_b][["cell_id", metric]].rename(
                    columns={metric: f"{metric}_b"}
                )
                merged = group_a.merge(group_b, on="cell_id", how="inner")
                corr, n_cells = spearman_rank_corr(
                    merged.rename(columns={f"{metric}_a": "metric_a", f"{metric}_b": "metric_b"}),
                    "metric_a",
                    "metric_b",
                )
                corr_rows.append(
                    {
                        "scenario": scenario,
                        "metric": metric,
                        "hour_a": hour_a,
                        "hour_b": hour_b,
                        "spearman_r": corr,
                        "n_cells": n_cells,
                        "caveat": "n_cells < 8; small-sample diagnostic" if n_cells < 8 else (
                            "Core 8 diagnostic sample" if n_cells == 8 else ""
                        ),
                    }
                )
                top_a = hour_top_sets[hour_a]
                top_b = hour_top_sets[hour_b]
                union = top_a | top_b
                overlap_rows.append(
                    {
                        "scenario": scenario,
                        "metric": metric,
                        "hour_a": hour_a,
                        "hour_b": hour_b,
                        "top_k": top_k_size(n_cells),
                        "top_k_cells_hour_a": "|".join(sorted(top_a)),
                        "top_k_cells_hour_b": "|".join(sorted(top_b)),
                        "overlap_count": len(top_a & top_b),
                        "jaccard_overlap": len(top_a & top_b) / len(union) if union else pd.NA,
                        "n_cells": n_cells,
                        "caveat": "Core 8 small-sample diagnostic only" if n_cells <= 8 else "",
                    }
                )
            if hours:
                consistent_top = set.intersection(*hour_top_sets.values()) if hour_top_sets else set()
                consistent_bottom = set.intersection(*hour_bottom_sets.values()) if hour_bottom_sets else set()
                consistent_rows.append(
                    {
                        "scenario": scenario,
                        "metric": metric,
                        "hours_compared": "|".join(str(h) for h in hours),
                        "consistent_top_cells": "|".join(sorted(consistent_top)),
                        "consistent_bottom_cells": "|".join(sorted(consistent_bottom)),
                        "n_consistent_top": len(consistent_top),
                        "n_consistent_bottom": len(consistent_bottom),
                    }
                )
    corr = pd.DataFrame(corr_rows)
    overlap = pd.DataFrame(overlap_rows)
    consistent = pd.DataFrame(consistent_rows)
    corr.to_csv(output_dir / "hour_stability_rank_correlation.csv", index=False)
    overlap.to_csv(output_dir / "hour_stability_topk_overlap.csv", index=False)
    consistent.to_csv(output_dir / "hour_stability_consistent_cells.csv", index=False)
    return corr, overlap, consistent


def label_flag(label: str, tokens: list[str]) -> bool:
    """Return whether a label contains any token."""
    low = str(label).lower()
    return any(token in low for token in tokens)


def typology_audit(df: pd.DataFrame, consistent: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    """Write typology interpretability rows."""
    rows: list[dict[str, Any]] = []
    label_available = "typology_label" in df.columns and df["typology_label"].astype(str).str.len().gt(0).any()
    for (scenario, cell_id), group in df.groupby(["scenario", "cell_id"], dropna=False):
        label = ""
        if label_available:
            labels = group["typology_label"].dropna().astype(str)
            label = labels.iloc[0] if not labels.empty else ""
        p90_rank = (
            group.assign(rank=group.groupby("hour")["tmrt_p90_c"].rank(ascending=False, method="average"))
            if "tmrt_p90_c" in group.columns
            else group.assign(rank=pd.NA)
        )
        m_rad_mean = group["m_rad_pct"].mean() if "m_rad_pct" in group.columns else pd.NA
        top_cells = set()
        bottom_cells = set()
        subset = consistent[(consistent["scenario"] == scenario) & (consistent["metric"] == "tmrt_p90_c")]
        if not subset.empty:
            top_cells = set(str(subset.iloc[0].get("consistent_top_cells", "")).split("|")) - {""}
            bottom_cells = set(str(subset.iloc[0].get("consistent_bottom_cells", "")).split("|")) - {""}
        notes: list[str] = []
        if not label_available:
            notes.append("typology labels unavailable")
        if label_flag(label, ["walkway", "bus_stop", "bus stop", "school_gate", "school gate"]):
            notes.append("pedestrian relevance cue in label")
        rows.append(
            {
                "scenario": scenario,
                "cell_id": cell_id,
                "typology_label": label if label_available else "",
                "shade_label": label_flag(label, ["shade", "shaded"]),
                "overhead_label": label_flag(label, ["overhead", "canopy"]),
                "hardscape_label": label_flag(label, ["hardscape", "paved", "parking"]),
                "wooded_label": label_flag(label, ["wooded", "tree", "park"]),
                "road_edge_label": label_flag(label, ["road_edge", "road edge", "road"]),
                "water_adjacent_label": label_flag(label, ["river", "water", "canal"]),
                "average_tmrt_p90_rank": p90_rank["rank"].mean(),
                "average_m_rad_pct": m_rad_mean,
                "is_consistent_hot_anchor": str(cell_id) in top_cells,
                "is_consistent_cool_anchor": str(cell_id) in bottom_cells,
                "notes": "; ".join(notes),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(output_dir / "typology_interpretability_audit.csv", index=False)
    return out


def summarize_metric_evidence(
    metric: str,
    availability: pd.DataFrame,
    corr: pd.DataFrame,
    topk: pd.DataFrame,
) -> dict[str, Any]:
    """Summarize availability and p90-relative evidence for one metric."""
    metric_avail = availability[availability["metric"] == metric]
    available = bool(metric_avail["available"].any()) if not metric_avail.empty else False
    p90_corr = corr[
        ((corr["metric_a"] == "tmrt_p90_c") & (corr["metric_b"] == metric))
        | ((corr["metric_b"] == "tmrt_p90_c") & (corr["metric_a"] == metric))
    ]
    p90_topk = topk[
        ((topk["metric_a"] == "tmrt_p90_c") & (topk["metric_b"] == metric))
        | ((topk["metric_b"] == "tmrt_p90_c") & (topk["metric_a"] == metric))
    ]
    return {
        "available": available,
        "non_missing_total": int(metric_avail["non_missing_count"].sum()) if not metric_avail.empty else 0,
        "mean_p90_spearman": p90_corr["spearman_r"].mean() if not p90_corr.empty else pd.NA,
        "mean_p90_topk_jaccard": p90_topk["jaccard_overlap"].mean() if not p90_topk.empty else pd.NA,
    }


def decision_matrix(
    df: pd.DataFrame,
    availability: pd.DataFrame,
    corr: pd.DataFrame,
    topk: pd.DataFrame,
    output_dir: Path,
) -> pd.DataFrame:
    """Write candidate target decision matrix."""
    metrics = [
        "tmrt_mean_c",
        "tmrt_p75_c",
        "tmrt_p90_c",
        "tmrt_p95_c",
        "tmrt_max_c",
        *threshold_columns(list(df.columns)),
        "delta_tmrt_p90_c",
        "m_rad_pct",
    ]
    metrics = list(dict.fromkeys(metrics))
    rows: list[dict[str, Any]] = []
    p90_summary = summarize_metric_evidence("tmrt_p90_c", availability, corr, topk)
    p90_available = p90_summary["available"]
    p90_corr_with_core = corr[
        ((corr["metric_a"] == "tmrt_p90_c") | (corr["metric_b"] == "tmrt_p90_c"))
        & corr["spearman_r"].notna()
        & ~corr[["metric_a", "metric_b"]].isin(["delta_tmrt_p90_c", "m_rad_pct"]).any(axis=1)
    ]
    p90_min_corr = p90_corr_with_core["spearman_r"].min() if not p90_corr_with_core.empty else pd.NA
    p90_robust = p90_available and (pd.isna(p90_min_corr) or p90_min_corr >= 0.75)

    for metric in metrics:
        evidence = summarize_metric_evidence(metric, availability, corr, topk)
        if not evidence["available"]:
            role = "unavailable"
            status = "unavailable"
            summary = "Metric absent from Core 8 audit tables."
        elif metric == "tmrt_p90_c":
            role = "primary" if p90_robust else "sensitivity"
            status = "keep primary with Core 8 caveat" if p90_robust else "downgrade pending more samples"
            summary = f"Available across Core 8 summaries; minimum core-target Spearman vs p90 companions = {p90_min_corr}."
        elif metric == "delta_tmrt_p90_c":
            role = "companion"
            status = "keep as scenario-normalized companion"
            summary = "Available in modifier targets and directly expresses p90 departure from the same-hour reference."
        elif metric == "m_rad_pct":
            role = "companion"
            status = "keep as normalized ranking modifier"
            summary = "Available in modifier targets as percentile-like radiant modifier."
        elif metric == "tmrt_mean_c":
            role = "companion"
            status = "keep as background companion"
            summary = "Available as central tendency companion for p90 interpretation."
        elif metric == "tmrt_max_c":
            role = "sensitivity"
            status = "upper-bound sensitivity only"
            summary = "Available, but max is more sensitive to extreme cells than p90."
        elif metric == "tmrt_p95_c":
            role = "companion" if evidence["mean_p90_spearman"] is not pd.NA else "sensitivity"
            status = "keep as high-tail companion"
            summary = "Available as a higher-tail check on p90 stability."
        elif metric == "tmrt_p75_c":
            role = "companion"
            status = "keep as lower-tail companion"
            summary = "Available as a shoulder-of-distribution check on p90."
        else:
            role = "companion"
            status = "use if stable and available"
            summary = "Threshold-area companion metric detected in source tables."

        rows.append(
            {
                "metric": metric,
                "candidate_role": role,
                "robustness_summary": summary,
                "advantages": target_advantages(metric),
                "risks": target_risks(metric),
                "interpretation": target_interpretation(metric),
                "downstream_use": target_downstream_use(metric),
                "caveat": "Core 8 is a small diagnostic sample; p90 is operational, not an external standard.",
                "recommended_status": status,
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(output_dir / "systemb_target_decision_matrix.csv", index=False)
    return out


def target_advantages(metric: str) -> str:
    """Short target-specific advantage text."""
    return {
        "tmrt_p90_c": "Retains high radiant exposure signal without relying on a single maximum pixel.",
        "delta_tmrt_p90_c": "Controls for same-hour reference level and improves scenario-normalized comparison.",
        "m_rad_pct": "Compact percentile-like modifier for ranking and communication.",
        "tmrt_mean_c": "Summarizes broad background radiant exposure.",
        "tmrt_p75_c": "Checks whether p90 signal is also visible below the tail.",
        "tmrt_p95_c": "Checks sensitivity to the upper tail beyond p90.",
        "tmrt_max_c": "Useful stress test for extreme upper-bound behavior.",
    }.get(metric, "Can summarize threshold exceedance area if present.")


def target_risks(metric: str) -> str:
    """Short target-specific risk text."""
    return {
        "tmrt_p90_c": "Operational choice; can be unstable if the high-tail pixel distribution shifts.",
        "delta_tmrt_p90_c": "Depends on reference-domain definition and can hide absolute high values.",
        "m_rad_pct": "Relative scale can obscure absolute magnitude differences.",
        "tmrt_mean_c": "Can understate localized high-exposure pockets.",
        "tmrt_p75_c": "May be too mild for high-tail prioritisation.",
        "tmrt_p95_c": "More tail-sensitive and potentially less stable than p90.",
        "tmrt_max_c": "Most vulnerable to single-pixel artifacts or edge effects.",
    }.get(metric, "Requires explicit threshold definition and pedestrian relevance review.")


def target_interpretation(metric: str) -> str:
    """Short target interpretation."""
    if metric.startswith("pct") or "threshold" in metric or "area_above" in metric:
        return "Share or area of summarized cells above a radiant threshold."
    return {
        "tmrt_p90_c": "High-tail SOLWEIG-derived Tmrt summary.",
        "delta_tmrt_p90_c": "Difference from same-hour reference p90.",
        "m_rad_pct": "Relative radiant modifier percentile.",
        "tmrt_mean_c": "Mean SOLWEIG-derived Tmrt summary.",
        "tmrt_p75_c": "Upper-shoulder SOLWEIG-derived Tmrt summary.",
        "tmrt_p95_c": "Higher-tail SOLWEIG-derived Tmrt summary.",
        "tmrt_max_c": "Maximum summarized Tmrt value.",
    }.get(metric, "Companion System B target.")


def target_downstream_use(metric: str) -> str:
    """Short downstream use recommendation."""
    return {
        "tmrt_p90_c": "Primary Product B ranking target if kept robust.",
        "delta_tmrt_p90_c": "Companion for normalized scenario and hour comparison.",
        "m_rad_pct": "Companion modifier for compact ranking.",
        "tmrt_mean_c": "Background companion and plausibility check.",
        "tmrt_p75_c": "Sensitivity companion.",
        "tmrt_p95_c": "High-tail companion if stable.",
        "tmrt_max_c": "Sensitivity only, not primary.",
    }.get(metric, "Use as companion only after stability review.")


def concise_float(value: Any, digits: int = 3) -> str:
    """Format a number or missing value for Markdown."""
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def write_blocked_report(output_dir: Path, missing: list[Path], inventory: pd.DataFrame, root: Path) -> None:
    """Write a blocked report when required summaries are missing."""
    missing_list = "\n".join(f"- {safe_rel(path, root)}" for path in missing)
    loaded = inventory[inventory["exists"] == True]  # noqa: E712
    report = f"""# Sprint B1 - System B Target Robustness Audit

## Status
BLOCKED

## Scope
- existing SOLWEIG summaries only
- no rasters
- no SOLWEIG rerun
- no QGIS
- no surrogate
- no System A/B coupling
- no risk map
- no local WBGT

## Inputs
Required Core 8 summary inputs are missing:

{missing_list}

Loaded/inspected metadata rows: {len(loaded)}

## Decision
4. Blocked due to missing summaries.

## Caveats
- No attempt was made to recompute from rasters.
- No .tif or .tiff files were searched or loaded.
- No model training, surrogate, risk product, or System A/B coupling was performed.
"""
    report_path = output_dir / "systemb_target_robustness_report.md"
    report_path.write_text(report, encoding="utf-8")


def write_report(
    output_dir: Path,
    inventory: pd.DataFrame,
    normalized: pd.DataFrame,
    availability: pd.DataFrame,
    corr: pd.DataFrame,
    topk: pd.DataFrame,
    sensitivity: pd.DataFrame,
    sensitivity_summary: pd.DataFrame,
    hour_corr: pd.DataFrame,
    hour_topk: pd.DataFrame,
    typology: pd.DataFrame,
    decisions: pd.DataFrame,
) -> None:
    """Write the main Markdown report."""
    loaded = inventory[(inventory["exists"] == True) & (inventory["row_count"] != "")]  # noqa: E712
    scenario_hours = (
        normalized.groupby("scenario")["hour"].apply(lambda s: ",".join(str(int(x)) for x in sorted(s.dropna().unique())))
        if not normalized.empty
        else pd.Series(dtype="object")
    )
    scenario_cells = (
        normalized.groupby("scenario")["cell_id"].nunique() if not normalized.empty else pd.Series(dtype="int64")
    )
    metrics_available = sorted(availability.loc[availability["available"] == True, "metric"].unique())  # noqa: E712
    metrics_unavailable = sorted(availability.loc[availability["available"] == False, "metric"].unique())  # noqa: E712

    p90_corr = corr[
        ((corr["metric_a"] == "tmrt_p90_c") | (corr["metric_b"] == "tmrt_p90_c"))
        & corr["spearman_r"].notna()
    ]
    p90_topk = topk[
        ((topk["metric_a"] == "tmrt_p90_c") | (topk["metric_b"] == "tmrt_p90_c"))
        & topk["jaccard_overlap"].notna()
    ]
    p90_summary = (
        f"Mean p90-paired Spearman = {concise_float(p90_corr['spearman_r'].mean())}; "
        f"mean p90-paired top-k Jaccard = {concise_float(p90_topk['jaccard_overlap'].mean())}."
        if not p90_corr.empty
        else "p90 paired robustness could not be computed."
    )

    p90_delta = sensitivity_summary[sensitivity_summary["metric"] == "tmrt_p90_c"]
    mrad_delta = sensitivity_summary[sensitivity_summary["metric"] == "m_rad_pct"]
    p90_all = p90_delta[p90_delta["hour"].astype(str) == "all"]
    mrad_all = mrad_delta[mrad_delta["hour"].astype(str) == "all"]
    scenario_text = "Base and overhead scenarios were matched by cell_id/hour."
    if sensitivity.empty:
        scenario_text = "Base and overhead scenarios could not be matched by cell_id/hour."
    elif not p90_all.empty:
        scenario_text += (
            f" Overall p90 mean delta overhead-minus-base = "
            f"{concise_float(p90_all.iloc[0]['mean_delta'])} C; cooled cells = "
            f"{int(p90_all.iloc[0]['count_cells_cooled'])}, warmed cells = "
            f"{int(p90_all.iloc[0]['count_cells_warmed'])}."
        )
    if not mrad_all.empty:
        scenario_text += (
            f" Overall m_rad_pct mean delta = {concise_float(mrad_all.iloc[0]['mean_delta'])}."
        )

    hour_summary = (
        f"Mean cross-hour Spearman = {concise_float(hour_corr['spearman_r'].mean())}; "
        f"mean cross-hour top-k Jaccard = {concise_float(hour_topk['jaccard_overlap'].mean())}."
        if not hour_corr.empty
        else "Hour stability could not be computed."
    )

    hot_cells = typology.loc[typology["is_consistent_hot_anchor"] == True, "cell_id"].astype(str).unique()  # noqa: E712
    cool_cells = typology.loc[typology["is_consistent_cool_anchor"] == True, "cell_id"].astype(str).unique()  # noqa: E712
    labels_available = typology["typology_label"].astype(str).str.len().gt(0).any() if not typology.empty else False
    typology_text = (
        f"Typology labels are available. Consistent p90 hot anchors: {', '.join(hot_cells) or 'none'}; "
        f"consistent cool anchors: {', '.join(cool_cells) or 'none'}."
        if labels_available
        else "Typology labels are unavailable; the audit reports cell ranks only."
    )

    p90_decision = decisions[decisions["metric"] == "tmrt_p90_c"]
    if p90_decision.empty or p90_decision.iloc[0]["candidate_role"] == "unavailable":
        decision = "4. Blocked due to missing summaries."
        next_action = "B3 N=24 scaled sample design"
        status = "BLOCKED"
    else:
        role = p90_decision.iloc[0]["candidate_role"]
        if role == "primary":
            decision = "1. Keep tmrt_p90_c / delta_tmrt_p90_c / m_rad_pct as primary target family."
            next_action = "B3 N=24 scaled sample design"
            status = "PASS"
        else:
            decision = "3. Downgrade p90 pending more samples."
            next_action = "B3 N=24 scaled sample design"
            status = "PARTIAL"

    input_lines = []
    for scenario, hours in scenario_hours.items():
        input_lines.append(
            f"- {scenario}: cells={int(scenario_cells.get(scenario, 0))}, hours={hours}"
        )
    loaded_key = loaded[loaded["path"].astype(str).str.contains("core8_.*summary", regex=True)]
    loaded_lines = [
        f"- {row.path}: rows={row.row_count}, scenario={row.scenario_inferred or 'metadata'}"
        for row in loaded_key.itertuples()
    ]

    report = f"""# Sprint B1 - System B Target Robustness Audit

## Status
{status}

## Scope
- existing SOLWEIG summaries only
- no rasters
- no SOLWEIG rerun
- no QGIS
- no surrogate
- no System A/B coupling
- no risk map
- no local WBGT

## Inputs
Loaded/inspected files: {len(loaded)}.

Core 8 loaded summaries:
{chr(10).join(loaded_lines) if loaded_lines else '- none'}

Scenario/hour/cell coverage:
{chr(10).join(input_lines) if input_lines else '- none'}

## Product taxonomy
Product A is the System A WBGT heat-stress state and answers when it is hot; it is not implemented here. Product B is the System B SOLWEIG-derived radiative heat-hazard potential and answers where structure is more radiant under the same forcing. Product B2 is a future UTCI/PET sensitivity layer. Product C is a future WBGT-conditioned radiative priority. Product D is a future planning heat-risk priority requiring explicit exposure and vulnerability.

## Target availability
Available metrics: {', '.join(metrics_available) if metrics_available else 'none'}.

Unavailable or empty metrics in at least one scenario/hour: {', '.join(metrics_unavailable) if metrics_unavailable else 'none'}.

## Ranking robustness
{p90_summary}

Core 8 top-k statistics are small-sample diagnostics only. p90 is evaluated here against mean, p75, p95, max, delta p90, and m_rad_pct where available.

## Scenario sensitivity
{scenario_text}

Largest cooling/warming cells and hour-wise summaries are written to `base_vs_overhead_sensitivity_summary.csv`.

## Hour stability
{hour_summary}

Consistently top-ranked and cool-ranked cells across hours are written to `hour_stability_consistent_cells.csv`.

## Typology interpretability
{typology_text}

If pedestrian relevance is needed downstream, a future pedestrian-accessible mask remains required.

## Decision
{decision}

## Caveats
- Core 8 is small sample.
- p90 is operational target, not external standard.
- no pedestrian-accessible mask yet.
- no exposure/vulnerability.
- no risk claim.
- no local WBGT claim.

## Next recommended action
{next_action}

## Run boundary confirmation
- no rasters touched
- no .tif touched
- no SOLWEIG rerun
- no QGIS
- no model training
- no risk map
- no local WBGT
- no System A/B coupling performed
- no commit/stage performed
"""
    (output_dir / "systemb_target_robustness_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    """Run the audit."""
    args = parse_args()
    root = args.repo_root.resolve()
    output_dir = (root / args.output_dir).resolve() if not args.output_dir.is_absolute() else args.output_dir
    ensure_output_dir(output_dir)

    inventory = write_inventory(root, output_dir)
    missing = missing_key_inputs(root)
    if missing:
        write_blocked_report(output_dir, missing, inventory, root)
        return

    tmrt, modifier = load_core8_tables(root, output_dir)
    normalized = modifier.copy() if not modifier.empty else tmrt.copy()
    availability = target_availability(normalized, output_dir)
    describe_targets(normalized, output_dir)
    corr = rank_correlation(normalized, output_dir)
    topk = topk_overlap(normalized, output_dir)
    sensitivity, sensitivity_summary = scenario_sensitivity(normalized, output_dir)
    hour_corr, hour_topk, consistent = hour_stability(normalized, output_dir)
    typology = typology_audit(normalized, consistent, output_dir)
    decisions = decision_matrix(normalized, availability, corr, topk, output_dir)
    write_report(
        output_dir,
        inventory,
        normalized,
        availability,
        corr,
        topk,
        sensitivity,
        sensitivity_summary,
        hour_corr,
        hour_topk,
        typology,
        decisions,
    )


if __name__ == "__main__":
    main()
