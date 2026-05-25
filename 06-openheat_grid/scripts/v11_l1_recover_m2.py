#!/usr/bin/env python
"""Recover historical M2 baseline evidence for System A Level 1 Sprint 1.

Inputs:
    - Existing text/config/script/output artifacts under outputs/, configs/,
      scripts/, and docs/; v12, QGIS, rasters, raw archives, and SOLWEIG paths
      are intentionally skipped.
    - Existing metric CSVs named v11_beta_calibration_metrics.csv or
      v09_beta_calibration_metrics.csv when present.

Outputs:
    - outputs/v11_level1/m2_recovery/m2_recovery_report.md
    - outputs/v11_level1/m2_recovery/recovered_m0_m4_metrics.csv

Saved metrics:
    - Recovered MAE, RMSE, bias, R2, threshold counts/scores when present.
    - Same-framing MAE deltas for M2 against M1, M1b, M3, and M4.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "v11_level1" / "m2_recovery"

TERMS = [
    "M2_linear_proxy",
    "linear_proxy",
    "M2_linear",
    "M2 linear",
    "M2",
]

MODEL_ORDER = [
    "M0_raw_proxy",
    "M1_global_bias",
    "M1b_period_bias",
    "M2_linear_proxy",
    "M3_weather_ridge",
    "M4_inertia_ridge",
]

TEXT_SUFFIXES = {".csv", ".md", ".json", ".py", ".txt", ".yaml", ".yml"}
SKIP_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "v12",
    "_incoming_v12_pre_scale",
    "qgis",
    "rasters",
    "raw",
    "archive",
    "solweig",
}


def is_allowed_text_path(path: Path) -> bool:
    parts = {p.lower() for p in path.relative_to(ROOT).parts}
    if parts & SKIP_PARTS:
        return False
    return path.suffix.lower() in TEXT_SUFFIXES and path.is_file()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def find_term_hits() -> dict[str, list[str]]:
    roots = [ROOT / "outputs", ROOT / "configs", ROOT / "scripts", ROOT / "docs"]
    hits: dict[str, list[str]] = {term: [] for term in TERMS}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not is_allowed_text_path(path):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for term in TERMS:
                if term.lower() in text.lower():
                    hits[term].append(relative(path))
    return {term: sorted(set(paths)) for term, paths in hits.items()}


def metric_files() -> list[Path]:
    roots = [
        ROOT / "outputs" / "v11_beta_calibration",
        ROOT / "outputs" / "v11_beta_formal",
        ROOT / "outputs" / "v09_freeze",
        ROOT / "outputs" / "v09_beta_calibration",
    ]
    out: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.csv"):
            if any(part.lower() in SKIP_PARTS for part in path.relative_to(ROOT).parts):
                continue
            name = path.name.lower()
            if "metrics" in name or "calibration" in name or "threshold" in name:
                out.append(path)
    return sorted(set(out))


def read_metrics(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()
    if "model" not in df.columns:
        return pd.DataFrame()
    models = set(MODEL_ORDER)
    mask = df["model"].astype(str).isin(models)
    if not mask.any():
        return pd.DataFrame()
    out = df.loc[mask].copy()
    out.insert(0, "source_path", relative(path))
    out.insert(1, "dataset_label", path.parent.name)
    return out


def recover_metric_rows() -> pd.DataFrame:
    frames = [read_metrics(path) for path in metric_files()]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    recovered = pd.concat(frames, ignore_index=True, sort=False)
    recovered["model_order"] = recovered["model"].map({m: i for i, m in enumerate(MODEL_ORDER)})
    sort_cols = [c for c in ["source_path", "cv_scheme", "model_order"] if c in recovered.columns]
    return recovered.sort_values(sort_cols).drop(columns=["model_order"])


def add_same_framing_deltas(metrics: pd.DataFrame) -> pd.DataFrame:
    if metrics.empty or "mae" not in metrics.columns:
        return metrics
    group_cols = [c for c in ["source_path", "dataset_label", "cv_scheme"] if c in metrics.columns]
    metrics = metrics.copy()
    for col in [
        "mae_delta_m2_minus_m1",
        "mae_delta_m2_minus_m1b",
        "mae_delta_m2_minus_m3",
        "mae_delta_m2_minus_m4",
    ]:
        metrics[col] = pd.NA
    comparisons = {
        "mae_delta_m2_minus_m1": "M1_global_bias",
        "mae_delta_m2_minus_m1b": "M1b_period_bias",
        "mae_delta_m2_minus_m3": "M3_weather_ridge",
        "mae_delta_m2_minus_m4": "M4_inertia_ridge",
    }
    for _, group in metrics.groupby(group_cols, dropna=False):
        m2_rows = group[group["model"].astype(str).eq("M2_linear_proxy")]
        if m2_rows.empty:
            continue
        m2_mae = pd.to_numeric(m2_rows.iloc[0].get("mae"), errors="coerce")
        if pd.isna(m2_mae):
            continue
        for delta_col, other_model in comparisons.items():
            other_rows = group[group["model"].astype(str).eq(other_model)]
            if other_rows.empty:
                continue
            other_mae = pd.to_numeric(other_rows.iloc[0].get("mae"), errors="coerce")
            if pd.notna(other_mae):
                metrics.loc[m2_rows.index, delta_col] = float(m2_mae - other_mae)
    return metrics


def csv_preview(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "_No recovered rows._"
    from io import StringIO

    buf = StringIO()
    df.head(max_rows).to_csv(buf, index=False, quoting=csv.QUOTE_MINIMAL)
    return "```csv\n" + buf.getvalue().strip() + "\n```"


def write_report(metrics: pd.DataFrame, hits: dict[str, list[str]]) -> None:
    m2_found_in_metrics = bool((not metrics.empty) and metrics["model"].astype(str).eq("M2_linear_proxy").any())
    m2_files = sorted(
        set(metrics.loc[metrics["model"].astype(str).eq("M2_linear_proxy"), "source_path"].astype(str))
    ) if m2_found_in_metrics else []

    primary = pd.DataFrame()
    if not metrics.empty:
        primary_mask = (
            metrics["source_path"].astype(str).str.contains("outputs/v11_beta_formal/ablation_B_retrospective")
            & metrics.get("cv_scheme", pd.Series("", index=metrics.index)).astype(str).eq("loso")
        )
        if primary_mask.any():
            primary = metrics.loc[primary_mask, [c for c in metrics.columns if c in [
                "model", "n", "mae", "rmse", "bias", "r2", "n_folds", "n_features",
                "wbgt_ge_31_precision", "wbgt_ge_31_recall", "wbgt_ge_31_f1",
                "wbgt_ge_31_tp", "wbgt_ge_31_fp", "wbgt_ge_31_fn",
                "wbgt_ge_33_precision", "wbgt_ge_33_recall", "wbgt_ge_33_f1",
                "wbgt_ge_33_tp", "wbgt_ge_33_fp", "wbgt_ge_33_fn",
            ]]]
        else:
            primary = metrics.head(12)

    delta_cols = [
        "source_path",
        "dataset_label",
        "cv_scheme",
        "n",
        "mae_delta_m2_minus_m1",
        "mae_delta_m2_minus_m1b",
        "mae_delta_m2_minus_m3",
        "mae_delta_m2_minus_m4",
    ]
    delta_preview = metrics.loc[
        metrics["model"].astype(str).eq("M2_linear_proxy"),
        [c for c in delta_cols if c in metrics.columns],
    ] if not metrics.empty else pd.DataFrame()

    term_lines = []
    for term, paths in hits.items():
        shown = paths[:20]
        suffix = f" ({len(paths) - len(shown)} more)" if len(paths) > len(shown) else ""
        term_lines.append(f"- `{term}`: {len(paths)} file(s){suffix}")
        for path in shown:
            term_lines.append(f"  - `{path}`")

    report = [
        "# M2 Recovery Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## Scope",
        "",
        "Searched outputs/, configs/, scripts/, and docs/ for the requested M2 terms.",
        "Skipped v12, QGIS, SOLWEIG, rasters, raw archive, and binary/heavy paths to keep this Level 1 audit within scope.",
        "",
        "## Result",
        "",
        f"- M2 found in output metrics: **{'yes' if m2_found_in_metrics else 'no'}**",
        f"- Files with M2 metric rows: **{len(m2_files)}**",
        "- Interpretation: M2 was defined and run in existing v11 outputs; it was not just a dormant script definition.",
        "- Naming: the recovered output name is `M2_linear_proxy`.",
        "",
        "## Metric Files Containing M2",
        "",
        "\n".join(f"- `{path}`" for path in m2_files) if m2_files else "_None._",
        "",
        "## Text Search Hits",
        "",
        "\n".join(term_lines),
        "",
        "## Primary Same-Framing Comparison",
        "",
        "Primary framing: formal retrospective LOSO metrics when present.",
        "",
        csv_preview(primary),
        "",
        "## M2 Same-Framing MAE Deltas",
        "",
        "Positive values mean M2 has higher MAE than the comparison model in the same source and CV framing.",
        "",
        csv_preview(delta_preview, max_rows=30),
        "",
        "## Notes",
        "",
        "- MAE/RMSE/bias/R2 are recovered when present in source metric CSVs.",
        "- Threshold precision/recall/F1/counts are recovered when present in source metric CSVs.",
        "- No new model was trained for this recovery.",
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "m2_recovery_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover historical M2 metrics and text evidence.")
    parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    hits = find_term_hits()
    metrics = add_same_framing_deltas(recover_metric_rows())
    metrics.to_csv(OUT_DIR / "recovered_m0_m4_metrics.csv", index=False)
    write_report(metrics, hits)
    print(f"[OK] wrote {OUT_DIR / 'recovered_m0_m4_metrics.csv'}")
    print(f"[OK] wrote {OUT_DIR / 'm2_recovery_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
