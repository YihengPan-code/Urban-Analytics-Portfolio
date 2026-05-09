"""
OpenHeat v0.8-beta: apply UMEP morphology with vegetation to the grid.

This script merges UMEP-derived SVF and shadow outputs into the existing
v0.7/v0.7.1 grid feature table, preserves the v0.7 proxy morphology columns,
and replaces `svf` and `shade_fraction` with DSM/UMEP-derived values.

Default use:
    python scripts/v08_apply_umep_morphology_with_veg.py

Typical explicit use:
    python scripts/v08_apply_umep_morphology_with_veg.py ^
      --base-grid data/grid/toa_payoh_grid_v07_features_beta_final_v071_risk.csv ^
      --umep data/grid/toa_payoh_grid_v08_umep_morphology_with_veg.csv ^
      --out-grid data/grid/toa_payoh_grid_v08_features_umep_with_veg.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _safe_describe(s: pd.Series) -> dict:
    s = pd.to_numeric(s, errors="coerce")
    return {
        "count": int(s.count()),
        "missing": int(s.isna().sum()),
        "min": float(s.min()) if s.count() else None,
        "mean": float(s.mean()) if s.count() else None,
        "median": float(s.median()) if s.count() else None,
        "p25": float(s.quantile(0.25)) if s.count() else None,
        "p75": float(s.quantile(0.75)) if s.count() else None,
        "p95": float(s.quantile(0.95)) if s.count() else None,
        "max": float(s.max()) if s.count() else None,
    }


def _fmt(x) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "NA"
    if isinstance(x, (int, np.integer)):
        return str(x)
    if isinstance(x, (float, np.floating)):
        return f"{x:.4f}"
    return str(x)


def _merge_prefer_new(base: pd.DataFrame, umep: pd.DataFrame) -> pd.DataFrame:
    """Merge by cell_id and prefer newly supplied UMEP columns if names overlap."""
    merged = base.merge(umep, on="cell_id", how="left", suffixes=("", "__umepnew"))
    for c in umep.columns:
        if c == "cell_id":
            continue
        new_c = f"{c}__umepnew"
        if new_c in merged.columns:
            merged[c] = merged[new_c]
            merged = merged.drop(columns=[new_c])
    return merged


def apply_umep(
    base_grid: Path,
    umep_path: Path,
    out_grid: Path,
    svf_col: str,
    shade_col: str,
    qa_md: Path,
    qa_json: Path,
) -> dict:
    base = pd.read_csv(base_grid)
    umep = pd.read_csv(umep_path)

    if "cell_id" not in base.columns:
        raise ValueError(f"Base grid lacks cell_id: {base_grid}")
    if "cell_id" not in umep.columns:
        raise ValueError(f"UMEP morphology lacks cell_id: {umep_path}")
    if base["cell_id"].duplicated().any():
        dups = base.loc[base["cell_id"].duplicated(), "cell_id"].head(10).tolist()
        raise ValueError(f"Duplicate cell_id in base grid, examples: {dups}")
    if umep["cell_id"].duplicated().any():
        dups = umep.loc[umep["cell_id"].duplicated(), "cell_id"].head(10).tolist()
        raise ValueError(f"Duplicate cell_id in UMEP morphology, examples: {dups}")
    for c in [svf_col, shade_col]:
        if c not in umep.columns:
            raise ValueError(f"UMEP morphology does not contain requested column `{c}`")

    # Preserve proxy morphology before replacement.
    base = base.copy()
    if "svf_proxy_v07" not in base.columns:
        if "svf" not in base.columns:
            raise ValueError("Base grid has neither svf nor svf_proxy_v07")
        base["svf_proxy_v07"] = base["svf"]
    if "shade_fraction_proxy_v07" not in base.columns:
        if "shade_fraction" not in base.columns:
            raise ValueError("Base grid has neither shade_fraction nor shade_fraction_proxy_v07")
        base["shade_fraction_proxy_v07"] = base["shade_fraction"]

    merged = _merge_prefer_new(base, umep)
    missing_umep = int(merged[svf_col].isna().sum())

    # Replace morphology with UMEP values; fallback to v0.7 proxy only for missing cells.
    merged["svf_umep_selected"] = pd.to_numeric(merged[svf_col], errors="coerce").clip(0, 1)
    merged["shade_fraction_umep_selected"] = pd.to_numeric(merged[shade_col], errors="coerce").clip(0, 1)
    merged["svf"] = merged["svf_umep_selected"].where(merged["svf_umep_selected"].notna(), merged["svf_proxy_v07"]).clip(0, 1)
    merged["shade_fraction"] = merged["shade_fraction_umep_selected"].where(
        merged["shade_fraction_umep_selected"].notna(), merged["shade_fraction_proxy_v07"]
    ).clip(0, 1)

    merged["svf_source_v08"] = np.where(merged["svf_umep_selected"].notna(), f"umep_with_veg:{svf_col}", "fallback:svf_proxy_v07")
    merged["shade_source_v08"] = np.where(
        merged["shade_fraction_umep_selected"].notna(), f"umep_with_veg:{shade_col}", "fallback:shade_fraction_proxy_v07"
    )
    merged["umep_morphology_version"] = "v0.8-beta-building-plus-canopy"
    merged["umep_morphology_notes"] = (
        "SVF and shade_fraction replaced with UMEP DSM-derived building+canopy open-pixel values; "
        "v0.7 proxy columns retained for comparison."
    )

    if "umep_includes_vegetation" not in merged.columns:
        merged["umep_includes_vegetation"] = True

    # Diagnostics.
    for c in ["svf_proxy_v07", "shade_fraction_proxy_v07", "svf", "shade_fraction"]:
        merged[c] = pd.to_numeric(merged[c], errors="coerce")
    merged["delta_svf_v08_minus_proxy"] = merged["svf"] - merged["svf_proxy_v07"]
    merged["delta_shade_v08_minus_proxy"] = merged["shade_fraction"] - merged["shade_fraction_proxy_v07"]

    _ensure_dir(out_grid)
    merged.to_csv(out_grid, index=False)

    diagnostics = {
        "base_grid": str(base_grid),
        "umep_morphology": str(umep_path),
        "out_grid": str(out_grid),
        "rows_base": int(len(base)),
        "rows_umep": int(len(umep)),
        "rows_out": int(len(merged)),
        "missing_umep_svf_rows_after_merge": missing_umep,
        "svf_col_used": svf_col,
        "shade_col_used": shade_col,
        "summaries": {
            c: _safe_describe(merged[c])
            for c in [
                "svf_proxy_v07",
                "svf",
                "delta_svf_v08_minus_proxy",
                "shade_fraction_proxy_v07",
                "shade_fraction",
                "delta_shade_v08_minus_proxy",
                "open_pixel_fraction",
                "building_pixel_fraction",
            ]
            if c in merged.columns
        },
        "counts": {
            "svf_ge_0_95": int((merged["svf"] >= 0.95).sum()),
            "svf_le_0_10": int((merged["svf"] <= 0.10).sum()),
            "shade_ge_0_70": int((merged["shade_fraction"] >= 0.70).sum()),
            "shade_eq_0": int((merged["shade_fraction"] <= 1e-9).sum()),
            "fallback_svf_rows": int((merged["svf_source_v08"] == "fallback:svf_proxy_v07").sum()),
            "fallback_shade_rows": int((merged["shade_source_v08"] == "fallback:shade_fraction_proxy_v07").sum()),
        },
    }

    _ensure_dir(qa_json)
    qa_json.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append("# OpenHeat v0.8-beta UMEP with vegetation merge QA")
    lines.append("")
    lines.append(f"Base grid: `{base_grid}`")
    lines.append(f"UMEP morphology: `{umep_path}`")
    lines.append(f"Output grid: `{out_grid}`")
    lines.append("")
    lines.append(f"Rows: base={len(base)}, UMEP={len(umep)}, output={len(merged)}")
    lines.append(f"Missing UMEP rows after merge: **{missing_umep}**")
    lines.append("")
    lines.append("## Selected replacement columns")
    lines.append(f"- `svf` ← `{svf_col}`")
    lines.append(f"- `shade_fraction` ← `{shade_col}`")
    lines.append("")
    lines.append("## Feature summaries")
    for c, d in diagnostics["summaries"].items():
        lines.append(
            f"- `{c}`: missing={d['missing']}, min={_fmt(d['min'])}, mean={_fmt(d['mean'])}, "
            f"median={_fmt(d['median'])}, p75={_fmt(d['p75'])}, p95={_fmt(d['p95'])}, max={_fmt(d['max'])}"
        )
    lines.append("")
    lines.append("## Counts")
    for k, v in diagnostics["counts"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Interpretation notes")
    lines.append("- This is the v0.8-beta building + canopy UMEP morphology layer.")
    lines.append("- `shade_fraction` is UMEP building + vegetation shadow over open pixels for the chosen date/time window.")
    lines.append("- `svf` also includes vegetation obstruction, so it is lower than building-only SVF and should be interpreted as canopy-aware open-pixel SVF.")
    lines.append("- v0.7 proxy columns are retained as `svf_proxy_v07` and `shade_fraction_proxy_v07` for comparison.")
    lines.append("- This remains morphology/radiation screening, not full SOLWEIG Tmrt simulation.")
    _ensure_dir(qa_md)
    qa_md.write_text("\n".join(lines), encoding="utf-8")

    return diagnostics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-grid", default="data/grid/toa_payoh_grid_v07_features_beta_final_v071_risk.csv")
    parser.add_argument("--umep", default="data/grid/toa_payoh_grid_v08_umep_morphology_with_veg.csv")
    parser.add_argument("--out-grid", default="data/grid/toa_payoh_grid_v08_features_umep_with_veg.csv")
    parser.add_argument("--svf-col", default="svf_umep_mean_open_with_veg")
    parser.add_argument("--shade-col", default="shade_fraction_umep_10_16_open_with_veg")
    parser.add_argument("--qa-md", default="outputs/v08_umep_with_veg_morphology_merge_QA.md")
    parser.add_argument("--qa-json", default="outputs/v08_umep_with_veg_morphology_merge_QA.json")
    args = parser.parse_args()

    diagnostics = apply_umep(
        Path(args.base_grid),
        Path(args.umep),
        Path(args.out_grid),
        args.svf_col,
        args.shade_col,
        Path(args.qa_md),
        Path(args.qa_json),
    )
    print("[OK] Applied UMEP with vegetation morphology")
    print("out_grid:", diagnostics["out_grid"])
    print("qa_report:", args.qa_md)
    print("missing_umep_rows:", diagnostics["missing_umep_svf_rows_after_merge"])


if __name__ == "__main__":
    main()
