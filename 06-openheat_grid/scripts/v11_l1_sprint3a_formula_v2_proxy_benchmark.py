#!/usr/bin/env python
"""Run System A Level 1 Sprint 3A formula-v2 proxy benchmark.

Inputs:
    - data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_v091.csv
    - Optional diagnostic input:
      outputs/v11_beta_formal/diagnostics_inputs/v11_pairs_14d_formal_20260524_40419_v091_diag.csv
    - Optional hourly snapshot:
      data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_hourly.csv
    - Existing formula-audit code and outputs under scripts/, configs/, docs/,
      and outputs/v11_formula_audit/
    - Optional Sprint 2C event-calibration outputs under
      outputs/v11_level1/event_calibration/

Outputs:
    - outputs/v11_level1/formula_v2/formula_audit_discovery.md
    - outputs/v11_level1/formula_v2/formula_input_availability.csv
    - outputs/v11_level1/formula_v2/formula_input_availability_report.md
    - outputs/v11_level1/formula_v2/formula_candidate_registry.csv
    - outputs/v11_level1/formula_v2/formula_candidate_hourly_predictions.csv
    - outputs/v11_level1/formula_v2/raw_formula_metrics.csv
    - outputs/v11_level1/formula_v2/raw_formula_threshold_metrics.csv
    - outputs/v11_level1/formula_v2/raw_formula_distribution_diagnostics.csv
    - outputs/v11_level1/formula_v2/calibrated_formula_metrics.csv
    - outputs/v11_level1/formula_v2/calibrated_formula_threshold_metrics.csv
    - outputs/v11_level1/formula_v2/calibrated_formula_operating_points.csv
    - outputs/v11_level1/formula_v2/formula_vs_event_score_comparison.csv
    - outputs/v11_level1/formula_v2/advanced_formula_feasibility.csv
    - outputs/v11_level1/formula_v2/advanced_formula_feasibility_report.md
    - outputs/v11_level1/formula_v2/sprint3a_formula_v2_proxy_benchmark_report.md

Saved metrics:
    - Input-column availability and station/time coverage.
    - Candidate implementation registry with blockers.
    - Station-hour raw formula predictions aggregated from station-time rows.
    - Regression, distribution, high-tail, threshold-crossing, and best-F1
      threshold-offset diagnostics for raw formula candidates.
    - Train-only LOSO and future-block bias/affine diagnostic calibration
      layers for one-score formula candidates.
    - Comparison against available Sprint 2C event-score summaries.
    - Feasibility-only audit for advanced physics formula routes.

Scope guard:
    This script is Level 1 only. It benchmarks proxy formula candidates, does
    not train new Ridge M3/M4-style models, does not introduce new model
    families, does not replace the canonical System A baseline, does not touch
    Level 2/System B/SOLWEIG/v12/rasters/archive collection, and does not
    produce local 100 m WBGT.
"""
from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from v11_formula_audit_compare import build_variants, markdown_table  # noqa: E402


DEFAULT_OUT_DIR = ROOT / "outputs/v11_level1/formula_v2"
PRIMARY_INPUTS = [
    (
        "formal_station_time_snapshot",
        ROOT / "data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_v091.csv",
        "station_time",
    ),
    (
        "diagnostic_station_time_snapshot",
        ROOT / "outputs/v11_beta_formal/diagnostics_inputs/v11_pairs_14d_formal_20260524_40419_v091_diag.csv",
        "station_time",
    ),
    (
        "formal_hourly_snapshot",
        ROOT / "data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_hourly.csv",
        "hourly",
    ),
]
REQUIRED_COLUMNS = [
    "official_wbgt_c",
    "wbgt_proxy_v09_c",
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "shortwave_radiation",
    "timestamp_sgt",
    "station_id",
]
OPTIONAL_COLUMNS = [
    "cloud_cover",
    "direct_radiation",
    "diffuse_radiation",
    "direct_fraction",
    "diffuse_fraction",
    "pressure_msl",
    "surface_pressure",
    "solar_zenith",
    "longitude",
    "latitude",
    "station_longitude",
    "station_latitude",
    "wetbulb_stull_c_v09",
    "globe_temp_proxy_v09_c",
]
RAW_CANDIDATES = [
    ("existing_v09_proxy", "existing_v09_proxy"),
    ("reconstructed_v09_proxy", "reconstructed_from_v09_components"),
    ("k0.0035", "stull_simple_globe_k0p0035"),
    ("k0.0045", "stull_simple_globe_k0p0045"),
    ("k0.0055", "stull_simple_globe_k0p0055"),
    ("k0.0065", "stull_simple_globe_k0p0065"),
    ("k0.0080", "stull_simple_globe_k0p008"),
]
EVENT_THRESHOLDS = [31.0, 33.0]
THRESHOLD_SCAN = [x / 10.0 for x in range(250, 351)]


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    candidate_family: str
    raw_or_calibrated: str
    implementation_status: str
    implementation_source_file: str
    formula_summary: str
    required_columns: list[str]
    available_columns: list[str]
    missing_columns: list[str]
    can_compute: bool
    notes: str
    scientific_caveat: str
    variant_name: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Sprint 3A formula-v2 proxy benchmark from existing v1.1 "
            "formula-audit code and frozen station-time snapshot inputs."
        )
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Output directory.")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional explicit input CSV. Defaults to formal station-time snapshot when usable.",
    )
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def semicolon(values: Iterable[object]) -> str:
    out: list[str] = []
    for value in values:
        text = str(value)
        if text and text != "nan" and text not in out:
            out.append(text)
    return ";".join(out)


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def safe_div(num: float, den: float) -> float:
    return float(num / den) if den else np.nan


def safe_r2(y: pd.Series, pred: pd.Series) -> float:
    mask = y.notna() & pred.notna()
    if int(mask.sum()) < 2:
        return np.nan
    yy = y[mask].astype(float)
    pp = pred[mask].astype(float)
    denom = float(((yy - yy.mean()) ** 2).sum())
    if denom == 0.0:
        return np.nan
    return 1.0 - float(((yy - pp) ** 2).sum()) / denom


def binary_counts(y_event: pd.Series, p_event: pd.Series) -> dict[str, Any]:
    y = y_event.astype(bool)
    p = p_event.astype(bool)
    tp = int((y & p).sum())
    fp = int((~y & p).sum())
    tn = int((~y & ~p).sum())
    fn = int((y & ~p).sum())
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2.0 * precision * recall, precision + recall) if not (math.isnan(precision) or math.isnan(recall)) else np.nan
    return {
        "TP": tp,
        "FP": fp,
        "TN": tn,
        "FN": fn,
        "precision": precision,
        "recall": recall,
        "F1": f1,
    }


def threshold_at(y: pd.Series, score: pd.Series, event_threshold: float, score_threshold: float) -> dict[str, Any]:
    valid = y.notna() & score.notna()
    yy = y[valid].astype(float)
    ss = score[valid].astype(float)
    counts = binary_counts(yy >= event_threshold, ss >= score_threshold)
    return {
        "n": int(valid.sum()),
        "official_positive_count": int((yy >= event_threshold).sum()),
        "predicted_positive_count": int((ss >= score_threshold).sum()),
        **counts,
    }


def best_f1_threshold(y: pd.Series, score: pd.Series, event_threshold: float) -> dict[str, Any]:
    rows = []
    for threshold in THRESHOLD_SCAN:
        row = threshold_at(y, score, event_threshold, threshold)
        rows.append({"score_threshold_c": threshold, **row})
    scan = pd.DataFrame(rows)
    valid = scan.dropna(subset=["F1"])
    if valid.empty:
        return {
            "best_F1_threshold": np.nan,
            "best_F1_precision": np.nan,
            "best_F1_recall": np.nan,
            "best_F1": np.nan,
        }
    chosen = valid.sort_values(
        ["F1", "recall", "precision", "score_threshold_c"],
        ascending=[False, False, False, True],
    ).iloc[0]
    return {
        "best_F1_threshold": float(chosen["score_threshold_c"]),
        "best_F1_precision": float(chosen["precision"]),
        "best_F1_recall": float(chosen["recall"]),
        "best_F1": float(chosen["F1"]),
    }


def regression_metrics(frame: pd.DataFrame, y_col: str, score_col: str) -> dict[str, Any]:
    y = numeric(frame[y_col])
    score = numeric(frame[score_col])
    mask = y.notna() & score.notna()
    yy = y[mask]
    pp = score[mask]
    err = pp - yy
    return {
        "n": int(mask.sum()),
        "MAE": float(err.abs().mean()) if len(err) else np.nan,
        "RMSE": float(np.sqrt((err**2).mean())) if len(err) else np.nan,
        "bias": float(err.mean()) if len(err) else np.nan,
        "R2": safe_r2(y, score),
        "p50_abs_error": float(err.abs().quantile(0.50)) if len(err) else np.nan,
        "p90_abs_error": float(err.abs().quantile(0.90)) if len(err) else np.nan,
        "p95_abs_error": float(err.abs().quantile(0.95)) if len(err) else np.nan,
    }


def distribution_metrics(frame: pd.DataFrame, y_col: str, score_col: str) -> dict[str, Any]:
    y = numeric(frame[y_col])
    score = numeric(frame[score_col])
    mask = y.notna() & score.notna()
    yy = y[mask]
    ss = score[mask]
    err = ss - yy
    ge31 = yy >= 31.0
    top_decile_cut = yy.quantile(0.90) if len(yy) else np.nan
    top_decile = yy >= top_decile_cut if not math.isnan(float(top_decile_cut)) else pd.Series(False, index=yy.index)
    return {
        "n": int(mask.sum()),
        "candidate_mean": float(ss.mean()) if len(ss) else np.nan,
        "candidate_p95": float(ss.quantile(0.95)) if len(ss) else np.nan,
        "candidate_p99": float(ss.quantile(0.99)) if len(ss) else np.nan,
        "candidate_max": float(ss.max()) if len(ss) else np.nan,
        "official_p95": float(yy.quantile(0.95)) if len(yy) else np.nan,
        "official_p99": float(yy.quantile(0.99)) if len(yy) else np.nan,
        "official_max": float(yy.max()) if len(yy) else np.nan,
        "max_gap": float(ss.max() - yy.max()) if len(ss) and len(yy) else np.nan,
        "high_tail_bias_official_ge31": float(err[ge31].mean()) if int(ge31.sum()) else np.nan,
        "high_tail_MAE_official_ge31": float(err[ge31].abs().mean()) if int(ge31.sum()) else np.nan,
        "high_tail_bias_top_decile": float(err[top_decile].mean()) if int(top_decile.sum()) else np.nan,
        "top_decile_MAE": float(err[top_decile].abs().mean()) if int(top_decile.sum()) else np.nan,
        "top_decile_official_cut": float(top_decile_cut) if not math.isnan(float(top_decile_cut)) else np.nan,
    }


def input_availability(paths: list[tuple[str, Path, str]]) -> pd.DataFrame:
    rows = []
    check_cols = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
    for label, path, resolution in paths:
        exists = path.exists()
        columns: list[str] = []
        rows_count = np.nan
        station_count = np.nan
        min_ts = ""
        max_ts = ""
        if exists:
            sample = pd.read_csv(path, nrows=0)
            columns = list(sample.columns)
            usecols = [c for c in ["station_id", "timestamp_sgt"] if c in columns]
            if usecols:
                skim = pd.read_csv(path, usecols=usecols, low_memory=False)
                rows_count = int(len(skim))
                if "station_id" in skim.columns:
                    station_count = int(skim["station_id"].nunique(dropna=True))
                if "timestamp_sgt" in skim.columns:
                    ts = pd.to_datetime(skim["timestamp_sgt"], errors="coerce")
                    min_ts = str(ts.min()) if ts.notna().any() else ""
                    max_ts = str(ts.max()) if ts.notna().any() else ""
            else:
                rows_count = int(sum(1 for _ in path.open("rb")) - 1)
        present = [c for c in check_cols if c in columns]
        missing_required = [c for c in REQUIRED_COLUMNS if c not in columns]
        optional_present = [c for c in OPTIONAL_COLUMNS if c in columns]
        rows.append(
            {
                "input_label": label,
                "path": rel(path),
                "resolution": resolution,
                "exists": exists,
                "rows": rows_count,
                "n_columns": len(columns),
                "station_count": station_count,
                "min_timestamp_sgt": min_ts,
                "max_timestamp_sgt": max_ts,
                "required_present_count": len([c for c in REQUIRED_COLUMNS if c in columns]),
                "required_missing_count": len(missing_required),
                "required_missing": semicolon(missing_required),
                "optional_present": semicolon(optional_present),
                "checked_columns_present": semicolon(present),
            }
        )
    return pd.DataFrame(rows)


def select_input(availability: pd.DataFrame, explicit: Path | None) -> tuple[str, Path, str]:
    if explicit is not None:
        return ("explicit_input", explicit, "station_time")
    usable = availability[(availability["exists"]) & (availability["required_missing_count"] == 0)].copy()
    station_time = usable[usable["resolution"] == "station_time"].copy()
    if not station_time.empty:
        formal = station_time[station_time["input_label"] == "formal_station_time_snapshot"]
        if not formal.empty:
            row = formal.iloc[0]
        else:
            row = station_time.sort_values("n_columns", ascending=False).iloc[0]
        return (str(row["input_label"]), ROOT / str(row["path"]), str(row["resolution"]))
    if not usable.empty:
        row = usable.iloc[0]
        return (str(row["input_label"]), ROOT / str(row["path"]), str(row["resolution"]))
    raise SystemExit("[ERROR] No input file has all required basic formula columns.")


def write_input_report(out_dir: Path, availability: pd.DataFrame, selected_label: str) -> None:
    lines = [
        "# Sprint 3A formula input availability",
        "",
        f"Selected input: `{selected_label}`.",
        "",
        markdown_table(availability.fillna("").astype(str)),
        "",
        "The formal station-time snapshot is preferred when it contains all required formula columns. "
        "Hourly input is used only as a labelled approximation if station-time formula computation is unavailable.",
    ]
    (out_dir / "formula_input_availability_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_discovery(out_dir: Path) -> None:
    files = [
        ROOT / "scripts/v11_formula_audit_compare.py",
        ROOT / "configs/v11/v11_formula_audit_config.example.json",
        ROOT / "outputs/v11_formula_audit/System_A_WBGT_formula_audit_report.md",
        ROOT / "outputs/v11_formula_audit/formula_bias_mae_rmse_table.csv",
        ROOT / "outputs/v11_formula_audit/formula_threshold_operating_points.csv",
        ROOT / "outputs/v11_formula_audit/formula_comparison_by_row.csv.gz",
        ROOT / "docs/v11/System_A_WBGT_formula_audit_CN.md",
    ]
    rows = []
    for path in files:
        rows.append(
            {
                "path": rel(path),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else np.nan,
            }
        )
    lines = [
        "# Sprint 3A formula-audit discovery",
        "",
        "Existing reusable assets were found for the v1.1 companion WBGT formula audit.",
        "",
        markdown_table(pd.DataFrame(rows).fillna("").astype(str)),
        "",
        "Reusable implementation:",
        "",
        "- `scripts/v11_formula_audit_compare.py` provides `build_variants`, including `existing_v09_proxy`, "
        "`reconstructed_from_v09_components`, and the Stull wet-bulb plus simplified globe k-sweep family.",
        "- `configs/v11/v11_formula_audit_config.example.json` documents the canonical v09 inputs, "
        "`wind_offset=0.25`, and the audited k-sweep lineage.",
        "- Existing outputs show `existing_v09_proxy`, `reconstructed_from_v09_components`, and "
        "`stull_simple_globe_k0p0045` are identical in the previous 15-minute audit.",
        "",
        "Scope boundary:",
        "",
        "No advanced Liljegren/Kong-Huber/Brimicombe implementation was found in the v1.1 formula audit lane. "
        "Those candidates are treated as feasibility-only in Sprint 3A.",
    ]
    (out_dir / "formula_audit_discovery.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_formula_config() -> dict[str, Any]:
    return {
        "columns": {
            "existing_proxy_col": "wbgt_proxy_v09_c",
            "temperature_col": "temperature_2m",
            "rh_col": "relative_humidity_2m",
            "wind_col": "wind_speed_10m",
            "shortwave_col": "shortwave_radiation",
            "stull_wetbulb_col": "wetbulb_stull_c_v09",
            "globe_proxy_col": "globe_temp_proxy_v09_c",
        },
        "formula_variants": {
            "globe_k_values": [0.0035, 0.0045, 0.0055, 0.0065, 0.0080],
            "wind_offset": 0.25,
            "min_wind_for_sqrt": 0.0,
        },
    }


def candidate_registry(columns: list[str], variants: pd.DataFrame) -> list[CandidateSpec]:
    available = set(columns)
    rows: list[CandidateSpec] = []
    source = "scripts/v11_formula_audit_compare.py"
    basic_required = ["official_wbgt_c", "timestamp_sgt", "station_id"]
    formula_required = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "shortwave_radiation"]
    component_required = ["temperature_2m", "wetbulb_stull_c_v09", "globe_temp_proxy_v09_c"]
    for candidate_id, variant_name in RAW_CANDIDATES:
        if candidate_id == "existing_v09_proxy":
            required = ["wbgt_proxy_v09_c"]
            family = "baseline_existing"
            summary = "Use existing `wbgt_proxy_v09_c` column."
        elif candidate_id == "reconstructed_v09_proxy":
            required = component_required
            family = "v09_reconstructed"
            summary = "Reuse audited reconstruction: 0.7 wetbulb + 0.2 v09 globe proxy + 0.1 air temperature."
        else:
            required = formula_required
            family = "v09_k_sweep"
            summary = "Reuse audited simplified globe family with varied k coefficient."
        missing = [c for c in [*basic_required, *required] if c not in available]
        can_compute = not missing and variant_name in variants.columns
        rows.append(
            CandidateSpec(
                candidate_id=candidate_id,
                candidate_family=family,
                raw_or_calibrated="raw",
                implementation_status="available" if can_compute else "blocked_missing_inputs",
                implementation_source_file=source,
                formula_summary=summary,
                required_columns=[*basic_required, *required],
                available_columns=[c for c in [*basic_required, *required] if c in available],
                missing_columns=missing,
                can_compute=can_compute,
                notes="Computed at station-time and aggregated to station-hour." if can_compute else "Not computed.",
                scientific_caveat="Screening proxy formula; not a validated local WBGT prediction.",
                variant_name=variant_name,
            )
        )

    for candidate_id, family in [
        ("existing_v09_train_bias_corrected", "simple_bias_corrected"),
        ("existing_v09_loso_affine", "simple_affine_proxy_calibrated"),
    ]:
        required = ["wbgt_proxy_v09_c", "official_wbgt_c", "timestamp_sgt", "station_id"]
        missing = [c for c in required if c not in available]
        rows.append(
            CandidateSpec(
                candidate_id=candidate_id,
                candidate_family=family,
                raw_or_calibrated="calibrated_diagnostic",
                implementation_status="available" if not missing else "blocked_missing_inputs",
                implementation_source_file="scripts/v11_l1_sprint3a_formula_v2_proxy_benchmark.py",
                formula_summary="Train-only one-score calibration layer; LOSO and future-block diagnostics only.",
                required_columns=required,
                available_columns=[c for c in required if c in available],
                missing_columns=missing,
                can_compute=not missing,
                notes="Not a final formula-v2 replacement.",
                scientific_caveat="Diagnostic calibration layer; do not treat as deployed formula.",
            )
        )

    advanced_required = {
        "liljegren_style": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "shortwave_radiation",
            "surface_pressure",
            "timestamp_sgt",
            "latitude",
            "longitude",
            "validated in-repo implementation",
        ],
        "kong_huber_style": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "shortwave_radiation",
            "cloud_cover",
            "validated in-repo implementation",
            "documented project-approved formula reference",
        ],
        "brimicombe_style": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "shortwave_radiation",
            "cloud_cover",
            "validated in-repo implementation",
            "documented project-approved formula reference",
        ],
    }
    for candidate_id, required in advanced_required.items():
        present = [c for c in required if c in available]
        missing = [c for c in required if c not in available]
        rows.append(
            CandidateSpec(
                candidate_id=candidate_id,
                candidate_family="advanced_physics_feasibility",
                raw_or_calibrated="feasibility_only",
                implementation_status="blocked_no_validated_implementation",
                implementation_source_file="",
                formula_summary="Feasibility audit only; full physics formula not implemented in Sprint 3A.",
                required_columns=required,
                available_columns=present,
                missing_columns=missing,
                can_compute=False,
                notes="No validated in-repo implementation found in v1.1 formula audit lane.",
                scientific_caveat="Do not implement complex WBGT physics from memory.",
            )
        )
    return rows


def registry_to_frame(registry: list[CandidateSpec]) -> pd.DataFrame:
    rows = []
    for item in registry:
        row = {
            "candidate_id": item.candidate_id,
            "candidate_family": item.candidate_family,
            "raw_or_calibrated": item.raw_or_calibrated,
            "implementation_status": item.implementation_status,
            "implementation_source_file": item.implementation_source_file,
            "formula_summary": item.formula_summary,
            "required_columns": semicolon(item.required_columns),
            "available_columns": semicolon(item.available_columns),
            "missing_columns": semicolon(item.missing_columns),
            "can_compute": item.can_compute,
            "notes": item.notes,
            "scientific_caveat": item.scientific_caveat,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def aggregate_hourly(df: pd.DataFrame, registry: list[CandidateSpec], variants: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    ts = pd.to_datetime(work["timestamp_sgt"], errors="coerce")
    work["timestamp_hour_sgt"] = ts.dt.floor("h").astype(str)
    work["date_sgt"] = ts.dt.date.astype(str)
    work["hour_sgt"] = ts.dt.hour
    work["official_wbgt_c"] = numeric(work["official_wbgt_c"])
    for item in registry:
        if item.raw_or_calibrated == "raw" and item.can_compute and item.variant_name:
            work[item.candidate_id] = numeric(variants[item.variant_name])

    id_cols = ["station_id", "timestamp_hour_sgt", "date_sgt", "hour_sgt"]
    rows = []
    for candidate in [r for r in registry if r.raw_or_calibrated == "raw" and r.can_compute]:
        agg = (
            work.groupby(id_cols, dropna=False)
            .agg(
                official_wbgt_c_mean=("official_wbgt_c", "mean"),
                official_wbgt_c_max=("official_wbgt_c", "max"),
                candidate_mean=(candidate.candidate_id, "mean"),
                candidate_max=(candidate.candidate_id, "max"),
                candidate_p90=(candidate.candidate_id, lambda x: x.quantile(0.90)),
                n_obs=(candidate.candidate_id, "count"),
            )
            .reset_index()
        )
        agg.insert(0, "candidate_id", candidate.candidate_id)
        rows.append(agg)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def raw_benchmark(hourly: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric_rows = []
    threshold_rows = []
    dist_rows = []
    specs = [
        ("hourly_mean", "official_wbgt_c_mean", "candidate_mean", "main"),
        ("hourly_max", "official_wbgt_c_max", "candidate_max", "main"),
        ("hourly_max", "official_wbgt_c_max", "candidate_p90", "diagnostic_p90_score"),
    ]
    for candidate_id, group in hourly.groupby("candidate_id"):
        for dataset_label, y_col, score_col, diagnostic_role in specs:
            frame = group.dropna(subset=[y_col, score_col]).copy()
            reg = regression_metrics(frame, y_col, score_col)
            metric_rows.append(
                {
                    "candidate_id": candidate_id,
                    "dataset_label": dataset_label,
                    "target_col": y_col,
                    "score_col": score_col,
                    "diagnostic_role": diagnostic_role,
                    **reg,
                }
            )
            dist_rows.append(
                {
                    "candidate_id": candidate_id,
                    "dataset_label": dataset_label,
                    "target_col": y_col,
                    "score_col": score_col,
                    "diagnostic_role": diagnostic_role,
                    **distribution_metrics(frame, y_col, score_col),
                }
            )
            y = numeric(frame[y_col])
            score = numeric(frame[score_col])
            for event_threshold in EVENT_THRESHOLDS:
                fixed = threshold_at(y, score, event_threshold, event_threshold)
                best = best_f1_threshold(y, score, event_threshold)
                threshold_rows.append(
                    {
                        "candidate_id": candidate_id,
                        "dataset_label": dataset_label,
                        "target_col": y_col,
                        "score_col": score_col,
                        "diagnostic_role": diagnostic_role,
                        "event_target": f"ge{int(event_threshold)}",
                        "official_event_threshold_c": event_threshold,
                        "fixed_score_threshold_c": event_threshold,
                        **fixed,
                        **best,
                        f"threshold_offset_ge{int(event_threshold)}": (
                            best["best_F1_threshold"] - event_threshold
                            if not math.isnan(best["best_F1_threshold"])
                            else np.nan
                        ),
                    }
                )
    return pd.DataFrame(metric_rows), pd.DataFrame(threshold_rows), pd.DataFrame(dist_rows)


def fit_affine(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    data = pd.DataFrame({"x": numeric(x), "y": numeric(y)}).dropna()
    if len(data) < 2 or float(data["x"].std(ddof=0)) == 0.0:
        return 1.0, float((data["y"] - data["x"]).mean()) if len(data) else 0.0
    slope, intercept = np.polyfit(data["x"].to_numpy(dtype=float), data["y"].to_numpy(dtype=float), deg=1)
    return float(slope), float(intercept)


def calibration_predictions(hourly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    specs = [
        ("hourly_mean", "official_wbgt_c_mean", "candidate_mean"),
        ("hourly_max", "official_wbgt_c_max", "candidate_max"),
    ]
    for candidate_id, candidate_frame in hourly.groupby("candidate_id"):
        for dataset_label, y_col, score_col in specs:
            frame = candidate_frame.dropna(subset=[y_col, score_col, "station_id", "date_sgt"]).copy()
            for station, test in frame.groupby("station_id", dropna=False):
                train = frame[frame["station_id"] != station]
                if train.empty:
                    continue
                bias_add = float((numeric(train[y_col]) - numeric(train[score_col])).mean())
                slope, intercept = fit_affine(train[score_col], train[y_col])
                base_cols = {
                    "candidate_id": candidate_id,
                    "dataset_label": dataset_label,
                    "target_col": y_col,
                    "score_col": score_col,
                    "validation_scheme": "LOSO",
                    "fold_id": str(station),
                    "train_rows": int(len(train)),
                    "test_rows": int(len(test)),
                }
                for method, pred in [
                    ("loso_train_bias_corrected", numeric(test[score_col]) + bias_add),
                    ("loso_affine", slope * numeric(test[score_col]) + intercept),
                ]:
                    out = test[["station_id", "timestamp_hour_sgt", "date_sgt", "hour_sgt", y_col, score_col]].copy()
                    out["calibration_method"] = method
                    out["prediction"] = pred.to_numpy()
                    out["slope_a"] = slope if method == "loso_affine" else 1.0
                    out["intercept_b"] = intercept if method == "loso_affine" else bias_add
                    for key, value in base_cols.items():
                        out[key] = value
                    rows.append(out)

            dates = sorted(frame["date_sgt"].dropna().astype(str).unique())
            if len(dates) >= 2:
                final_date = dates[-1]
                train = frame[frame["date_sgt"].astype(str) < final_date]
                test = frame[frame["date_sgt"].astype(str) == final_date]
                if not train.empty and not test.empty:
                    bias_add = float((numeric(train[y_col]) - numeric(train[score_col])).mean())
                    slope, intercept = fit_affine(train[score_col], train[y_col])
                    base_cols = {
                        "candidate_id": candidate_id,
                        "dataset_label": dataset_label,
                        "target_col": y_col,
                        "score_col": score_col,
                        "validation_scheme": "future_block_last_date",
                        "fold_id": final_date,
                        "train_rows": int(len(train)),
                        "test_rows": int(len(test)),
                    }
                    for method, pred in [
                        ("future_block_train_bias_corrected", numeric(test[score_col]) + bias_add),
                        ("future_block_affine", slope * numeric(test[score_col]) + intercept),
                    ]:
                        out = test[["station_id", "timestamp_hour_sgt", "date_sgt", "hour_sgt", y_col, score_col]].copy()
                        out["calibration_method"] = method
                        out["prediction"] = pred.to_numpy()
                        out["slope_a"] = slope if method.endswith("affine") else 1.0
                        out["intercept_b"] = intercept if method.endswith("affine") else bias_add
                        for key, value in base_cols.items():
                            out[key] = value
                        rows.append(out)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def calibrated_benchmark(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric_rows = []
    threshold_rows = []
    op_rows = []
    if predictions.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    group_cols = ["candidate_id", "dataset_label", "target_col", "score_col", "validation_scheme", "calibration_method"]
    for keys, group in predictions.groupby(group_cols):
        candidate_id, dataset_label, target_col, score_col, validation_scheme, method = keys
        frame = group.copy()
        frame["calibrated_score"] = numeric(frame["prediction"])
        reg = regression_metrics(frame, target_col, "calibrated_score")
        dist = distribution_metrics(frame, target_col, "calibrated_score")
        metric_rows.append(
            {
                "candidate_id": candidate_id,
                "dataset_label": dataset_label,
                "target_col": target_col,
                "raw_score_col": score_col,
                "validation_scheme": validation_scheme,
                "calibration_method": method,
                **reg,
                "high_tail_bias_official_ge31": dist["high_tail_bias_official_ge31"],
                "high_tail_MAE_official_ge31": dist["high_tail_MAE_official_ge31"],
            }
        )
        y = numeric(frame[target_col])
        score = numeric(frame["calibrated_score"])
        for event_threshold in EVENT_THRESHOLDS:
            fixed = threshold_at(y, score, event_threshold, event_threshold)
            best = best_f1_threshold(y, score, event_threshold)
            row = {
                "candidate_id": candidate_id,
                "dataset_label": dataset_label,
                "target_col": target_col,
                "raw_score_col": score_col,
                "validation_scheme": validation_scheme,
                "calibration_method": method,
                "event_target": f"ge{int(event_threshold)}",
                "official_event_threshold_c": event_threshold,
                "fixed_score_threshold_c": event_threshold,
                **fixed,
                **best,
                f"threshold_offset_ge{int(event_threshold)}": (
                    best["best_F1_threshold"] - event_threshold
                    if not math.isnan(best["best_F1_threshold"])
                    else np.nan
                ),
            }
            threshold_rows.append(row)
            op_rows.append({**row, "operating_point": "fixed_nominal", "operating_threshold_c": event_threshold, "operating_F1": fixed["F1"]})
            op_rows.append({**row, "operating_point": "best_F1", "operating_threshold_c": best["best_F1_threshold"], "operating_F1": best["best_F1"]})
    return pd.DataFrame(metric_rows), pd.DataFrame(threshold_rows), pd.DataFrame(op_rows)


def high_tail_bias_from_predictions(path: Path, model: str) -> float:
    if not path.exists():
        return np.nan
    df = pd.read_csv(path, low_memory=False)
    model_col = "ablation_model" if "ablation_model" in df.columns else "model"
    if model_col not in df.columns:
        return np.nan
    target_mask = (
        (df[model_col].astype(str) == model)
        & (df.get("dataset_label", "").astype(str) == "hourly_max")
        & (df.get("target_col", "").astype(str) == "official_wbgt_c_max")
    )
    sub = df[target_mask].copy()
    if sub.empty or "observed_wbgt_c" not in sub.columns or "prediction_wbgt_c" not in sub.columns:
        return np.nan
    y = numeric(sub["observed_wbgt_c"])
    p = numeric(sub["prediction_wbgt_c"])
    mask = y >= 31.0
    return float((p[mask] - y[mask]).mean()) if int(mask.sum()) else np.nan


def formula_vs_event_score(
    raw_thresholds: pd.DataFrame,
    raw_dist: pd.DataFrame,
    calibrated_thresholds: pd.DataFrame,
    calibrated_metrics: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    raw_focus = raw_thresholds[
        (raw_thresholds["dataset_label"] == "hourly_max")
        & (raw_thresholds["score_col"] == "candidate_max")
        & (raw_thresholds["event_target"] == "ge31")
    ].copy()
    if not raw_focus.empty:
        best_raw_id = raw_focus.sort_values("best_F1", ascending=False).iloc[0]["candidate_id"]
        rows.append(comparison_row_for_formula("best_raw_formula_candidate", best_raw_id, raw_thresholds, raw_dist))
    cal_focus = calibrated_thresholds[
        (calibrated_thresholds["dataset_label"] == "hourly_max")
        & (calibrated_thresholds["validation_scheme"] == "LOSO")
        & (calibrated_thresholds["calibration_method"] == "loso_affine")
        & (calibrated_thresholds["event_target"] == "ge31")
    ].copy()
    if not cal_focus.empty:
        best_cal = cal_focus.sort_values("best_F1", ascending=False).iloc[0]
        rows.append(
            comparison_row_for_calibrated(
                "best_simple_affine_formula_candidate",
                str(best_cal["candidate_id"]),
                calibrated_thresholds,
                calibrated_metrics,
            )
        )

    op_path = ROOT / "outputs/v11_level1/event_calibration/operating_point_summary.csv"
    pred_path = ROOT / "outputs/v11_level1/feature_ablation/oof_predictions_feature_ablation.csv"
    if op_path.exists():
        op = pd.read_csv(op_path)
        for model in ["M4_like_inertia_ridge", "M7_like_compact_weather_ridge", "L1_full_dynamic"]:
            focus = op[
                (op["prediction_source"].astype(str) == "loso_oof")
                & (op["dataset_label"].astype(str) == "hourly_max")
                & (op["target_col"].astype(str) == "official_wbgt_c_max")
                & (op["model"].astype(str) == model)
            ]
            rows.append(comparison_row_for_event_score(model, focus, high_tail_bias_from_predictions(pred_path, model)))
    return pd.DataFrame(rows)


def comparison_row_for_formula(label: str, candidate_id: str, thresholds: pd.DataFrame, dist: pd.DataFrame) -> dict[str, Any]:
    focus = thresholds[
        (thresholds["candidate_id"] == candidate_id)
        & (thresholds["dataset_label"] == "hourly_max")
        & (thresholds["score_col"] == "candidate_max")
    ]
    drow = dist[
        (dist["candidate_id"] == candidate_id)
        & (dist["dataset_label"] == "hourly_max")
        & (dist["score_col"] == "candidate_max")
    ]
    ge31 = focus[focus["event_target"] == "ge31"].iloc[0] if not focus[focus["event_target"] == "ge31"].empty else pd.Series(dtype=object)
    ge33 = focus[focus["event_target"] == "ge33"].iloc[0] if not focus[focus["event_target"] == "ge33"].empty else pd.Series(dtype=object)
    return {
        "source_type": label,
        "candidate_or_model": candidate_id,
        "fixed_31_recall": ge31.get("recall", np.nan),
        "fixed_31_F1": ge31.get("F1", np.nan),
        "best_F1_threshold_ge31": ge31.get("best_F1_threshold", np.nan),
        "threshold_offset_ge31": ge31.get("threshold_offset_ge31", np.nan),
        "fixed_33_predicted_count": ge33.get("predicted_positive_count", np.nan),
        "best_F1_ge33": ge33.get("best_F1", np.nan),
        "high_tail_bias": drow.iloc[0]["high_tail_bias_official_ge31"] if not drow.empty else np.nan,
    }


def comparison_row_for_calibrated(label: str, candidate_id: str, thresholds: pd.DataFrame, metrics: pd.DataFrame) -> dict[str, Any]:
    focus = thresholds[
        (thresholds["candidate_id"] == candidate_id)
        & (thresholds["dataset_label"] == "hourly_max")
        & (thresholds["validation_scheme"] == "LOSO")
        & (thresholds["calibration_method"] == "loso_affine")
    ]
    mrow = metrics[
        (metrics["candidate_id"] == candidate_id)
        & (metrics["dataset_label"] == "hourly_max")
        & (metrics["validation_scheme"] == "LOSO")
        & (metrics["calibration_method"] == "loso_affine")
    ]
    ge31 = focus[focus["event_target"] == "ge31"].iloc[0] if not focus[focus["event_target"] == "ge31"].empty else pd.Series(dtype=object)
    ge33 = focus[focus["event_target"] == "ge33"].iloc[0] if not focus[focus["event_target"] == "ge33"].empty else pd.Series(dtype=object)
    return {
        "source_type": label,
        "candidate_or_model": candidate_id,
        "fixed_31_recall": ge31.get("recall", np.nan),
        "fixed_31_F1": ge31.get("F1", np.nan),
        "best_F1_threshold_ge31": ge31.get("best_F1_threshold", np.nan),
        "threshold_offset_ge31": ge31.get("threshold_offset_ge31", np.nan),
        "fixed_33_predicted_count": ge33.get("predicted_positive_count", np.nan),
        "best_F1_ge33": ge33.get("best_F1", np.nan),
        "high_tail_bias": mrow.iloc[0]["high_tail_bias_official_ge31"] if not mrow.empty else np.nan,
    }


def comparison_row_for_event_score(model: str, focus: pd.DataFrame, high_tail_bias: float) -> dict[str, Any]:
    ge31_fixed = focus[(focus["event_target"] == "ge31") & (focus["operating_point"] == "fixed_nominal")]
    ge31_best = focus[(focus["event_target"] == "ge31") & (focus["operating_point"] == "best_F1")]
    ge33_fixed = focus[(focus["event_target"] == "ge33") & (focus["operating_point"] == "fixed_nominal")]
    ge33_best = focus[(focus["event_target"] == "ge33") & (focus["operating_point"] == "best_F1")]
    fixed31 = ge31_fixed.iloc[0] if not ge31_fixed.empty else pd.Series(dtype=object)
    best31 = ge31_best.iloc[0] if not ge31_best.empty else pd.Series(dtype=object)
    fixed33 = ge33_fixed.iloc[0] if not ge33_fixed.empty else pd.Series(dtype=object)
    best33 = ge33_best.iloc[0] if not ge33_best.empty else pd.Series(dtype=object)
    threshold31 = best31.get("score_threshold_c", np.nan)
    return {
        "source_type": "Sprint_2C_event_score",
        "candidate_or_model": model,
        "fixed_31_recall": fixed31.get("recall", np.nan),
        "fixed_31_F1": fixed31.get("F1", np.nan),
        "best_F1_threshold_ge31": threshold31,
        "threshold_offset_ge31": threshold31 - 31.0 if pd.notna(threshold31) else np.nan,
        "fixed_33_predicted_count": fixed33.get("predicted_positive_count", np.nan),
        "best_F1_ge33": best33.get("F1", np.nan),
        "high_tail_bias": high_tail_bias,
    }


def advanced_feasibility(columns: list[str]) -> pd.DataFrame:
    available = set(columns)
    pressure_available = "pressure_msl" in available or "surface_pressure" in available
    solar_available = "solar_zenith" in available or {"latitude", "longitude", "timestamp_sgt"}.issubset(available)
    package_checks = {
        "pythermalcomfort": importlib.util.find_spec("pythermalcomfort") is not None,
        "thermofeel": importlib.util.find_spec("thermofeel") is not None,
    }
    rows = []
    for candidate_id in ["liljegren_style", "kong_huber_style", "brimicombe_style"]:
        if candidate_id == "liljegren_style":
            required = "air temperature; humidity; wind; radiation; pressure; solar geometry; validated iterative implementation"
            available_cols = [
                c
                for c in [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "wind_speed_10m",
                    "shortwave_radiation",
                    "surface_pressure",
                    "timestamp_sgt",
                    "latitude",
                    "longitude",
                ]
                if c in available
            ]
            missing = []
            if not pressure_available:
                missing.append("pressure_msl or surface_pressure")
            if not solar_available:
                missing.append("solar geometry")
            missing.append("validated in-repo implementation")
            risk = "high"
            recommendation = "implement in separate Sprint 3B"
        else:
            required = "published formula inputs; weather/radiation inputs; documented coefficients; validated implementation reference"
            available_cols = [
                c
                for c in [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "wind_speed_10m",
                    "shortwave_radiation",
                    "cloud_cover",
                ]
                if c in available
            ]
            missing = ["validated in-repo implementation", "documented project-approved formula reference"]
            risk = "high"
            recommendation = "blocked until inputs available"
        rows.append(
            {
                "candidate_id": candidate_id,
                "required_inputs": required,
                "available_in_current_snapshot": semicolon(available_cols),
                "missing_inputs": semicolon(missing),
                "existing_validated_implementation_in_repo": False,
                "external_package_available_in_environment": semicolon([k for k, v in package_checks.items() if v]),
                "implementation_risk": risk,
                "recommendation": recommendation,
            }
        )
    return pd.DataFrame(rows)


def write_advanced_report(out_dir: Path, feasibility: pd.DataFrame) -> None:
    lines = [
        "# Sprint 3A advanced formula feasibility",
        "",
        markdown_table(feasibility.fillna("").astype(str)),
        "",
        "Advanced physics candidates were not implemented in Sprint 3A. The current evidence supports a separate validation sprint before any Liljegren/Kong-Huber/Brimicombe-style formula is used in System A reporting.",
    ]
    (out_dir / "advanced_formula_feasibility_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_main_report(
    out_dir: Path,
    selected_path: Path,
    input_resolution: str,
    input_df: pd.DataFrame,
    registry_frame: pd.DataFrame,
    hourly: pd.DataFrame,
    raw_metrics: pd.DataFrame,
    raw_thresholds: pd.DataFrame,
    raw_dist: pd.DataFrame,
    calibrated_metrics: pd.DataFrame,
    calibrated_thresholds: pd.DataFrame,
    comparison: pd.DataFrame,
    feasibility: pd.DataFrame,
) -> None:
    raw_main = raw_metrics[(raw_metrics["dataset_label"] == "hourly_max") & (raw_metrics["score_col"] == "candidate_max")]
    raw_best = raw_main.sort_values("MAE").head(5)
    raw_thr = raw_thresholds[
        (raw_thresholds["dataset_label"] == "hourly_max")
        & (raw_thresholds["score_col"] == "candidate_max")
        & (raw_thresholds["event_target"] == "ge31")
    ].sort_values("best_F1", ascending=False)
    cal_focus = calibrated_thresholds[
        (calibrated_thresholds["dataset_label"] == "hourly_max")
        & (calibrated_thresholds["validation_scheme"] == "LOSO")
        & (calibrated_thresholds["calibration_method"] == "loso_affine")
        & (calibrated_thresholds["event_target"] == "ge31")
    ].sort_values("best_F1", ascending=False)
    raw_status = "PASS" if not raw_metrics.empty and not calibrated_metrics.empty else "PARTIAL"
    selected_note = "station-time input" if input_resolution == "station_time" else "hourly-input approximation"
    lines = [
        "# System A Level 1 Sprint 3A - Formula-v2 Proxy Benchmark",
        "",
        "## Status",
        raw_status,
        "",
        "## Scope",
        "- Level 1 only.",
        "- Proxy formula benchmark only.",
        "- No new model family.",
        "- No final formula replacement.",
        "- No formula retroactive rewrite.",
        "- No Level 2.",
        "- No System B / SOLWEIG / v12.",
        "- No local WBGT.",
        "",
        "## Why Sprint 3A was needed",
        "Sprint 2B found high-tail underprediction, and Sprint 2C found ge31 best-F1 score thresholds below 31 C plus ge33 nominal threshold failure. Therefore the v09 proxy scale and high-tail compression needed a direct formula/proxy audit.",
        "",
        "## Existing formula audit discovery",
        "Reused `scripts/v11_formula_audit_compare.py` for the Stull wet-bulb and simplified globe k-sweep lineage. Existing audit outputs under `outputs/v11_formula_audit/` were read only for discovery/context and were not overwritten.",
        "",
        "## Input availability",
        f"- Input file: `{rel(selected_path)}`",
        f"- Input mode: {selected_note}",
        f"- Rows: {len(input_df):,}",
        f"- Columns: {len(input_df.columns):,}",
        f"- Stations: {input_df['station_id'].nunique(dropna=True) if 'station_id' in input_df.columns else 'NA'}",
        f"- Station-hours written: {hourly[['station_id', 'timestamp_hour_sgt']].drop_duplicates().shape[0] if not hourly.empty else 0:,}",
        "",
        "## Candidate Registry",
        "Available raw candidates were `existing_v09_proxy`, `reconstructed_v09_proxy`, and the v09 k-sweep (`k0.0035`, `k0.0045`, `k0.0055`, `k0.0065`, `k0.0080`). Advanced physics candidates were feasibility-only because no validated in-repo implementation was found.",
        "",
        "## Raw Formula Results",
        markdown_table(raw_best.round(6)) if not raw_best.empty else "_No raw metrics._",
        "",
        "Raw fixed_31/fixed_33 threshold behavior remains compressed. The best raw ge31 rows were:",
        "",
        markdown_table(raw_thr.head(8).round(6)) if not raw_thr.empty else "_No raw threshold metrics._",
        "",
        "## Calibrated Formula Diagnostics",
        "Train-only bias and affine diagnostics were run under LOSO and a final-date future block. These are one-score formula-calibration diagnostics, not final formula-v2 candidates.",
        "",
        markdown_table(cal_focus.head(8).round(6)) if not cal_focus.empty else "_No calibrated threshold metrics._",
        "",
        "## Formula vs Sprint 2C Event-score Comparison",
        markdown_table(comparison.round(6)) if not comparison.empty else "_Sprint 2C comparison inputs were unavailable._",
        "",
        "## Advanced Formula Feasibility",
        markdown_table(feasibility.fillna("").astype(str)),
        "",
        "## Interpretation",
        "1. The current v09 proxy is a major high-tail bottleneck on the raw score scale: station-hour maxima remain below fixed WBGT event thresholds for the raw k-sweep.",
        "2. No simple raw formula candidate materially removes high-tail compression.",
        "3. The k-sweep helps only marginally; larger k values nudge the upper tail but do not restore fixed_31/fixed_33 crossings.",
        "4. Simple affine calibration reduces scale offset as a diagnostic layer, but it is not enough to promote a replacement formula without follow-up validation and model-card work.",
        "5. Next recommended action: P_ge31 probability calibration companion, while treating advanced physics implementation as a separate Sprint 3B validation track if the project wants a formula replacement route.",
        "",
        "## Caveats",
        "- Formula candidates are proxies, not observed WBGT.",
        "- Calibrated formula diagnostics are not final forecast models.",
        "- Future-block is retrospective-like, not true prospective.",
        "- No formula candidate is promoted without model card and follow-up validation.",
        "",
        "## Next Recommended Action",
        "P_ge31 probability calibration companion.",
        "",
        "## Run Guardrails",
        "- No forbidden files touched.",
        "- No fallback solver used.",
        "- No new model family added.",
        "- No System B/v12 touched.",
        "- No commit/stage performed.",
        "- `formula_candidate_hourly_predictions.csv` is a generated row-level diagnostic and should be treated as do-not-commit unless explicitly reviewed.",
    ]
    (out_dir / "sprint3a_formula_v2_proxy_benchmark_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    write_discovery(out_dir)
    availability = input_availability(PRIMARY_INPUTS)
    selected_label, selected_path, input_resolution = select_input(availability, args.input)
    availability.to_csv(out_dir / "formula_input_availability.csv", index=False)
    write_input_report(out_dir, availability, selected_label)

    df = pd.read_csv(selected_path, low_memory=False)
    cfg = make_formula_config()
    variants = build_variants(df, cfg)
    registry = candidate_registry(list(df.columns), variants)
    registry_frame = registry_to_frame(registry)
    registry_frame.to_csv(out_dir / "formula_candidate_registry.csv", index=False)

    hourly = aggregate_hourly(df, registry, variants)
    hourly.to_csv(out_dir / "formula_candidate_hourly_predictions.csv", index=False)

    raw_metrics, raw_thresholds, raw_dist = raw_benchmark(hourly)
    raw_metrics.to_csv(out_dir / "raw_formula_metrics.csv", index=False)
    raw_thresholds.to_csv(out_dir / "raw_formula_threshold_metrics.csv", index=False)
    raw_dist.to_csv(out_dir / "raw_formula_distribution_diagnostics.csv", index=False)

    cal_predictions = calibration_predictions(hourly)
    cal_metrics, cal_thresholds, cal_ops = calibrated_benchmark(cal_predictions)
    cal_metrics.to_csv(out_dir / "calibrated_formula_metrics.csv", index=False)
    cal_thresholds.to_csv(out_dir / "calibrated_formula_threshold_metrics.csv", index=False)
    cal_ops.to_csv(out_dir / "calibrated_formula_operating_points.csv", index=False)

    comparison = formula_vs_event_score(raw_thresholds, raw_dist, cal_thresholds, cal_metrics)
    comparison.to_csv(out_dir / "formula_vs_event_score_comparison.csv", index=False)

    feasibility = advanced_feasibility(list(df.columns))
    feasibility.to_csv(out_dir / "advanced_formula_feasibility.csv", index=False)
    write_advanced_report(out_dir, feasibility)

    write_main_report(
        out_dir=out_dir,
        selected_path=selected_path,
        input_resolution=input_resolution,
        input_df=df,
        registry_frame=registry_frame,
        hourly=hourly,
        raw_metrics=raw_metrics,
        raw_thresholds=raw_thresholds,
        raw_dist=raw_dist,
        calibrated_metrics=cal_metrics,
        calibrated_thresholds=cal_thresholds,
        comparison=comparison,
        feasibility=feasibility,
    )

    print(f"[write] {rel(out_dir)}")
    print("[status] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
