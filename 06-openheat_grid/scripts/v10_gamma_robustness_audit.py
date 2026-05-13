#!/usr/bin/env python
"""
OpenHeat v10-gamma robustness audit.

This script is read-only: it does not modify any model outputs, rasters, grids, or rankings.
It audits four issues raised after the v10-gamma final findings report:

1. transition-class consistency, especially TP_0315;
2. false-positive candidate definition and whether criteria are co-derived from v10 data;
3. baseline comparison: old-top20 false-positive candidates vs non-candidates leaving v10 top20;
4. dense / fully-built edge cases, especially TP_0945.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def bool_series(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.fillna(False)
    return s.astype(str).str.lower().isin(["true", "1", "yes", "y"])


def pick_first_existing(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def safe_float(x, default=np.nan):
    try:
        return float(x)
    except Exception:
        return default


def hypergeom_prob(a: int, row1: int, col1: int, n: int) -> float:
    # Table: [[a, row1-a], [col1-a, n-row1-col1+a]] with fixed margins.
    if a < max(0, row1 + col1 - n) or a > min(row1, col1):
        return 0.0
    return math.comb(col1, a) * math.comb(n - col1, row1 - a) / math.comb(n, row1)


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> Tuple[float, float]:
    """Pure-Python Fisher exact two-sided p-value and odds ratio.

    Table:
        [[a, b],
         [c, d]]
    where rows are candidate/non-candidate and columns are left/stayed.
    """
    row1 = a + b
    row2 = c + d
    col1 = a + c
    n = row1 + row2
    obs = hypergeom_prob(a, row1, col1, n)
    amin = max(0, row1 + col1 - n)
    amax = min(row1, col1)
    p = 0.0
    for x in range(amin, amax + 1):
        prob = hypergeom_prob(x, row1, col1, n)
        if prob <= obs + 1e-12:
            p += prob
    odds = np.inf if b * c == 0 and a * d > 0 else ((a * d) / (b * c) if b * c != 0 else np.nan)
    return float(p), float(odds)


def transition_class(row: pd.Series) -> str:
    old_top = bool(row["in_old_topN"])
    new_top = bool(row["in_v10_topN"])
    fp = bool(row["co_derived_fp_candidate"])
    if old_top and new_top and fp:
        return "old_top_fp_retained_top"
    if old_top and (not new_top) and fp:
        return "old_top_fp_left_top"
    if old_top and new_top and (not fp):
        return "old_top_nonfp_retained_top"
    if old_top and (not new_top) and (not fp):
        return "old_top_nonfp_left_top"
    if (not old_top) and new_top and fp:
        return "entering_v10_top_fp_candidate"
    if (not old_top) and new_top and (not fp):
        return "entering_v10_top_nonfp"
    if fp:
        return "fp_candidate_outside_top_transition"
    return "other"


def describe_numeric(s: pd.Series) -> Dict[str, float]:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) == 0:
        return {"count": 0}
    return {
        "count": int(len(s)),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "min": float(s.min()),
        "p25": float(s.quantile(0.25)),
        "p75": float(s.quantile(0.75)),
        "max": float(s.max()),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/v10/v10_gamma_robustness_config.example.json")
    args = parser.parse_args()

    cfg = read_json(Path(args.config))
    inp = cfg["inputs"]
    par = cfg.get("parameters", {})
    out = cfg["outputs"]

    top_n = int(par.get("top_n", 20))
    old_topn_def = int(par.get("old_topn_for_candidate_definition", 50))
    old_comp_thr = float(par.get("old_completeness_threshold", 0.10))
    density_gain_thr = float(par.get("building_density_gain_threshold", 0.10))
    coverage_gain_thr = float(par.get("coverage_gain_threshold", 0.50))
    dense_thresholds = [float(x) for x in par.get("dense_thresholds", [0.85, 0.95, 0.99])]

    rank_path = Path(inp["rank_comparison_csv"])
    v10_rank_path = Path(inp["v10_hotspot_ranking_csv"])
    morph_path = Path(inp["morphology_shift_csv"])
    fp_path = Path(inp.get("old_false_positive_candidates_csv", ""))

    missing = [str(p) for p in [rank_path, v10_rank_path, morph_path] if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required input(s): " + "; ".join(missing))

    rank = pd.read_csv(rank_path)
    v10_rank = pd.read_csv(v10_rank_path)
    morph = pd.read_csv(morph_path)
    fp_candidates = pd.read_csv(fp_path) if fp_path and fp_path.exists() else pd.DataFrame(columns=["cell_id"])

    old_rank_col = pick_first_existing(rank, ["rank_v08_hazard_score", "old_rank", "rank_v08"])
    new_rank_col = pick_first_existing(rank, ["rank_v10_hazard_score", "new_rank", "rank_v10"])
    fp_col = pick_first_existing(rank, ["is_old_dsm_gap_false_positive_candidate", "possible_old_dsm_gap_false_positive"])
    if old_rank_col is None or new_rank_col is None:
        raise KeyError("Could not find rank columns in rank comparison CSV.")

    merged = rank.copy()
    merged["rank_v08"] = pd.to_numeric(merged[old_rank_col], errors="coerce")
    merged["rank_v10"] = pd.to_numeric(merged[new_rank_col], errors="coerce")
    merged["in_old_topN"] = merged["rank_v08"] <= top_n
    merged["in_v10_topN"] = merged["rank_v10"] <= top_n

    if fp_col:
        merged["co_derived_fp_candidate"] = bool_series(merged[fp_col])
    else:
        fp_set = set(fp_candidates["cell_id"].astype(str))
        merged["co_derived_fp_candidate"] = merged["cell_id"].astype(str).isin(fp_set)

    # Merge morphology-shift criteria for transparent candidate-definition audit.
    criteria_cols = [
        "cell_id",
        "hazard_rank_true_v08",
        "old_vs_osm_completeness",
        "reviewed_vs_osm_completeness",
        "coverage_gain_vs_osm",
        "old_building_density",
        "v10_building_density",
        "delta_building_density",
        "delta_building_area_m2",
        "possible_old_dsm_gap_false_positive",
        "audit_flags",
    ]
    criteria_cols = [c for c in criteria_cols if c in morph.columns]
    criteria = morph[criteria_cols].copy()
    merged = merged.merge(criteria, on="cell_id", how="left", suffixes=("", "_morph"))

    # Independent definition: only old rank + old completeness audit threshold.
    old_comp = pd.to_numeric(merged.get("old_vs_osm_completeness"), errors="coerce")
    merged["independent_old_dsm_gap_candidate"] = (merged["rank_v08"] <= old_topn_def) & (
        old_comp.fillna(np.inf) <= old_comp_thr
    )

    # Co-derived transparent definition approximation, if criteria are available.
    cov_gain = pd.to_numeric(merged.get("coverage_gain_vs_osm"), errors="coerce")
    dens_gain = pd.to_numeric(merged.get("delta_building_density"), errors="coerce")
    merged["co_derived_criteria_recomputed"] = (
        (merged["rank_v08"] <= old_topn_def)
        & (old_comp.fillna(np.inf) <= old_comp_thr)
        & (cov_gain.fillna(0) >= coverage_gain_thr)
        & (dens_gain.fillna(0) >= density_gain_thr)
    )

    merged["transition_class"] = merged.apply(transition_class, axis=1)

    transition_keep = merged[
        merged["in_old_topN"]
        | merged["in_v10_topN"]
        | merged["co_derived_fp_candidate"]
        | merged["independent_old_dsm_gap_candidate"]
    ].copy()
    transition_keep = transition_keep.sort_values(["in_v10_topN", "in_old_topN", "rank_v10", "rank_v08"], ascending=[False, False, True, True])

    # TP_0315 diagnostic.
    tp0315 = merged[merged["cell_id"].astype(str).eq("TP_0315")].copy()

    # Contingency among old topN cells.
    old_top = merged[merged["in_old_topN"]].copy()
    def contingency(candidate_col: str, label: str) -> dict:
        cand = bool_series(old_top[candidate_col]) if old_top[candidate_col].dtype != bool else old_top[candidate_col].fillna(False)
        left = ~old_top["in_v10_topN"]
        a = int((cand & left).sum())
        b = int((cand & ~left).sum())
        c = int((~cand & left).sum())
        d = int((~cand & ~left).sum())
        p, odds = fisher_exact_two_sided(a, b, c, d) if (a + b + c + d) > 0 else (np.nan, np.nan)
        return {
            "candidate_definition": label,
            "candidate_left_topN": a,
            "candidate_stayed_topN": b,
            "noncandidate_left_topN": c,
            "noncandidate_stayed_topN": d,
            "candidate_leave_rate": a / (a + b) if (a + b) else np.nan,
            "noncandidate_leave_rate": c / (c + d) if (c + d) else np.nan,
            "fisher_two_sided_p": p,
            "odds_ratio": odds,
            "top_n": top_n,
        }

    cont_rows = [
        contingency("co_derived_fp_candidate", "co_derived_v10_beta_flag"),
        contingency("independent_old_dsm_gap_candidate", f"independent_old_rank_top{old_topn_def}_old_completeness_le_{old_comp_thr}"),
        contingency("co_derived_criteria_recomputed", "recomputed_co_derived_criteria"),
    ]
    contingency_df = pd.DataFrame(cont_rows)

    # False-positive criteria table.
    fp_def_cols = [
        "cell_id",
        "rank_v08",
        "rank_v10",
        "co_derived_fp_candidate",
        "independent_old_dsm_gap_candidate",
        "co_derived_criteria_recomputed",
        "old_vs_osm_completeness",
        "reviewed_vs_osm_completeness",
        "coverage_gain_vs_osm",
        "old_building_density",
        "v10_building_density",
        "delta_building_density",
        "transition_class",
        "audit_flags",
    ]
    fp_def_cols = [c for c in fp_def_cols if c in merged.columns]
    fp_def = merged[fp_def_cols].copy().sort_values(["co_derived_fp_candidate", "rank_v08"], ascending=[False, True])

    # Dense / fully-built sanity check.
    density_col = pick_first_existing(v10_rank, ["building_pixel_fraction_v10", "v10_building_density", "building_density"])
    dense_df = pd.DataFrame()
    dense_summary_rows = []
    if density_col:
        v10_rank[density_col] = pd.to_numeric(v10_rank[density_col], errors="coerce")
        for thr in dense_thresholds:
            q = v10_rank[v10_rank[density_col] > thr].copy()
            row = {"density_column": density_col, "threshold": thr, "n_cells": len(q)}
            for metric in ["hazard_score", "max_utci_c", "svf", "shade_fraction", "rank", "risk_priority_score"]:
                if metric in q.columns:
                    desc = describe_numeric(q[metric])
                    for k, v in desc.items():
                        row[f"{metric}_{k}"] = v
            dense_summary_rows.append(row)
        dense_df = v10_rank[v10_rank[density_col] > min(dense_thresholds)].copy()
        keep_cols = [
            "cell_id", density_col, "hazard_score", "rank", "max_utci_c", "svf", "shade_fraction",
            "v10_open_pixel_fraction", "mean_building_height_m", "max_building_height_m",
            "land_use_hint", "building_source_v10"
        ]
        keep_cols = [c for c in keep_cols if c in dense_df.columns]
        dense_df = dense_df[keep_cols].sort_values(density_col, ascending=False)
    dense_summary = pd.DataFrame(dense_summary_rows)

    # Save outputs.
    output_dir = Path(out.get("output_dir", "outputs/v10_gamma_robustness"))
    output_dir.mkdir(parents=True, exist_ok=True)

    transition_path = Path(out["transition_classes_csv"])
    fpdef_path = Path(out["false_positive_definition_check_csv"])
    contingency_path = Path(out["fp_vs_nonfp_contingency_csv"])
    dense_path = Path(out["dense_cell_sanity_csv"])
    tp0315_path = Path(out["tp0315_diagnostic_csv"])
    report_path = Path(out["robustness_report_md"])
    for p in [transition_path, fpdef_path, contingency_path, dense_path, tp0315_path, report_path]:
        ensure_parent(p)

    transition_keep.to_csv(transition_path, index=False)
    fp_def.to_csv(fpdef_path, index=False)
    contingency_df.to_csv(contingency_path, index=False)
    dense_df.to_csv(dense_path, index=False)
    tp0315.to_csv(tp0315_path, index=False)

    transition_counts = transition_keep["transition_class"].value_counts().rename_axis("transition_class").reset_index(name="n")

    old_top_count = int(merged["in_old_topN"].sum())
    new_top_count = int(merged["in_v10_topN"].sum())
    overlap = int((merged["in_old_topN"] & merged["in_v10_topN"]).sum())

    co_row = contingency_df[contingency_df["candidate_definition"].eq("co_derived_v10_beta_flag")].iloc[0].to_dict()
    ind_row = contingency_df[contingency_df["candidate_definition"].str.startswith("independent")].iloc[0].to_dict()

    tp0315_text = "TP_0315 not found in rank comparison."
    if len(tp0315):
        r = tp0315.iloc[0]
        tp0315_text = (
            f"TP_0315 diagnostic: v08_rank={safe_float(r.get('rank_v08')):.0f}, "
            f"v10_rank={safe_float(r.get('rank_v10')):.0f}, "
            f"co_derived_fp_candidate={bool(r.get('co_derived_fp_candidate'))}, "
            f"transition_class={r.get('transition_class')}."
        )

    dense_text = "No dense-cell sanity check was run because no building-density column was found."
    if density_col:
        dense_text = dense_summary.to_string(index=False)

    report_lines = []
    report_lines.append("# v10-gamma robustness audit report")
    report_lines.append("")
    report_lines.append("This read-only audit checks transition-class consistency, false-positive candidate definitions, old-top20 baseline rates, and dense-cell edge cases after v10-gamma.")
    report_lines.append("")
    report_lines.append("## Inputs")
    report_lines.append(f"- rank comparison CSV: `{rank_path}`")
    report_lines.append(f"- v10 hotspot ranking CSV: `{v10_rank_path}`")
    report_lines.append(f"- morphology shift CSV: `{morph_path}`")
    report_lines.append(f"- old false-positive candidates CSV: `{fp_path}`")
    report_lines.append("")
    report_lines.append("## Top-set summary")
    report_lines.append(f"- Top-N used: **{top_n}**")
    report_lines.append(f"- Old top-N cells: **{old_top_count}**")
    report_lines.append(f"- v10 top-N cells: **{new_top_count}**")
    report_lines.append(f"- Top-N overlap: **{overlap} / {top_n}**")
    report_lines.append("")
    report_lines.append("## Transition-class counts")
    report_lines.append("```text")
    report_lines.append(transition_counts.to_string(index=False))
    report_lines.append("```")
    report_lines.append("")
    report_lines.append("## TP_0315 classification diagnostic")
    report_lines.append(tp0315_text)
    report_lines.append("")
    report_lines.append("Interpretation: if TP_0315 is listed as `entering_v10_top_fp_candidate`, it should **not** be described as an old-top20 false-positive that remained in the top20. It entered v10 top20 from outside old top20 while carrying the broader v10-beta candidate flag.")
    report_lines.append("")
    report_lines.append("## False-positive candidate definition check")
    report_lines.append("Two definitions are reported:")
    report_lines.append("")
    report_lines.append("1. `co_derived_fp_candidate`: the v10-beta diagnostic flag / rank-comparison flag. This uses v10 reviewed-DSM information such as coverage gain and building-density gain, so it should be framed as a co-derived diagnostic signal, not a fully independent validation target.")
    report_lines.append(f"2. `independent_old_dsm_gap_candidate`: old rank ≤ {old_topn_def} and old-vs-OSM completeness ≤ {old_comp_thr}. This uses old-rank and old completeness only, not v10 rank; it is a cleaner robustness check.")
    report_lines.append("")
    report_lines.append("## Old-topN leaving-rate baseline")
    report_lines.append("```text")
    report_lines.append(contingency_df.to_string(index=False))
    report_lines.append("```")
    report_lines.append("")
    report_lines.append("Recommended wording: v10-gamma does not independently prove that every diagnosed candidate was a false positive; rather, cells diagnosed as old DSM-gap candidates were disproportionately affected by reviewed-DSM morphology correction.")
    report_lines.append("")
    if not pd.isna(co_row.get("candidate_leave_rate")):
        report_lines.append(
            f"For the co-derived v10-beta flag, candidate old-top{top_n} cells left the top{top_n} at "
            f"**{co_row['candidate_left_topN']}/{co_row['candidate_left_topN'] + co_row['candidate_stayed_topN']} = {co_row['candidate_leave_rate']:.3f}**, "
            f"while non-candidates left at **{co_row['noncandidate_left_topN']}/{co_row['noncandidate_left_topN'] + co_row['noncandidate_stayed_topN']} = {co_row['noncandidate_leave_rate']:.3f}**."
        )
        if not pd.isna(co_row.get("fisher_two_sided_p")):
            report_lines.append(f"Fisher exact two-sided p-value for this 2×2 table: **{co_row['fisher_two_sided_p']:.4f}**. Treat this as a small-sample descriptive check, not a definitive statistical proof.")
    report_lines.append("")
    report_lines.append("## Dense / fully-built cell sanity check")
    report_lines.append(f"Density column used: `{density_col}`" if density_col else "No density column detected.")
    report_lines.append("```text")
    report_lines.append(dense_text)
    report_lines.append("```")
    report_lines.append("")
    if density_col and len(dense_df):
        tp0945 = dense_df[dense_df["cell_id"].astype(str).eq("TP_0945")]
        if len(tp0945):
            report_lines.append("TP_0945 appears in the dense-cell set. It should be treated as a fully/near-fully built edge case rather than a normal open-pedestrian hazard cell.")
    report_lines.append("")
    report_lines.append("## Outputs")
    report_lines.append(f"- transition classes: `{transition_path}`")
    report_lines.append(f"- false-positive definition check: `{fpdef_path}`")
    report_lines.append(f"- FP vs non-FP contingency: `{contingency_path}`")
    report_lines.append(f"- dense-cell sanity check: `{dense_path}`")
    report_lines.append(f"- TP_0315 diagnostic: `{tp0315_path}`")
    report_lines.append("")
    report_lines.append("## Suggested edits to v10-gamma final findings report")
    report_lines.append("- Split TP_0315 from 'old-top20 retained candidates'; describe it as an `entering_v10_top_fp_candidate` if applicable.")
    report_lines.append("- Explicitly state that the v10-beta false-positive candidate flag is co-derived from reviewed-DSM diagnostics.")
    report_lines.append("- Add the FP-vs-nonFP old-top20 leaving-rate baseline.")
    report_lines.append("- Add a dense-cell edge-case note for TP_0945 and any other cells above the dense thresholds.")
    report_lines.append("- Keep the main v10-gamma conclusion, but phrase it as a disproportionate correction of diagnosed DSM-gap candidates rather than independent proof for every candidate.")

    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"[OK] robustness report: {report_path}")
    print(f"[OK] transition classes: {transition_path}")
    print(f"[OK] FP definition check: {fpdef_path}")
    print(f"[OK] contingency: {contingency_path}")
    print(f"[OK] dense cell sanity: {dense_path}")


if __name__ == "__main__":
    main()
