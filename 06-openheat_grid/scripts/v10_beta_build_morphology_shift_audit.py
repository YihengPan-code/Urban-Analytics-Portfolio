from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np


def read_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def find_first_existing(candidates: list[str]) -> Path | None:
    for c in candidates:
        if c and Path(c).exists():
            return Path(c)
    return None


def locate_completeness_csv(cfg: dict[str, Any]) -> Path | None:
    paths = cfg.get("paths", {})
    candidates = [paths.get("v10_completeness_per_cell_csv", "")]
    candidates += sorted(glob.glob("outputs/v10_dsm_audit/*alpha3*per_cell*.csv"))
    candidates += sorted(glob.glob("outputs/v10_dsm_audit/*review*per_cell*.csv"))
    candidates += sorted(glob.glob("outputs/v10_dsm_audit/*completeness*per_cell*.csv"))
    return find_first_existing(candidates)


def normalise_completeness_cols(df: pd.DataFrame) -> pd.DataFrame:
    renames = {}
    # Reviewed / new columns vary across alpha versions.
    if "new_vs_osm_completeness" in df.columns and "reviewed_vs_osm_completeness" not in df.columns:
        renames["new_vs_osm_completeness"] = "reviewed_vs_osm_completeness"
    if "new_minus_old_dsm_area_m2" in df.columns and "reviewed_minus_old_dsm_area_m2" not in df.columns:
        renames["new_minus_old_dsm_area_m2"] = "reviewed_minus_old_dsm_area_m2"
    if "new_dsm_area_m2" in df.columns and "reviewed_dsm_area_m2" not in df.columns:
        renames["new_dsm_area_m2"] = "reviewed_dsm_area_m2"
    df = df.rename(columns=renames)
    return df


def load_old_ranking(cfg: dict[str, Any]) -> pd.DataFrame:
    paths = cfg.get("paths", {})
    risk_path = Path(paths.get("old_risk_scenario_csv", ""))
    hot_path = Path(paths.get("old_hotspot_csv", ""))
    if risk_path.exists():
        r = pd.read_csv(risk_path)
        cols = ["cell_id"]
        for c in [
            "hazard_rank_true_v08", "hazard_score", "max_utci_c", "max_wbgt_proxy_c",
            "risk_rank_v08_conditioned", "risk_priority_score_v08_conditioned",
            "risk_rank_v08_social_conditioned", "risk_priority_score_v08_social_conditioned",
            "risk_rank_v08_candidate_policy", "risk_priority_score_v08_candidate_policy",
            "vulnerability_score_v071", "outdoor_exposure_score_v071"
        ]:
            if c in r.columns:
                cols.append(c)
        out = r[cols].drop_duplicates("cell_id").copy()
        if "hazard_rank_true_v08" not in out.columns and "hazard_score" in out.columns:
            out["hazard_rank_true_v08"] = out["hazard_score"].rank(method="min", ascending=False).astype(int)
        return out
    if hot_path.exists():
        h = pd.read_csv(hot_path)
        cols = ["cell_id"]
        for c in ["rank", "hazard_score", "max_utci_c", "max_wbgt_proxy_c", "risk_priority_score"]:
            if c in h.columns:
                cols.append(c)
        out = h[cols].drop_duplicates("cell_id").copy()
        if "rank" in out.columns:
            out = out.rename(columns={"rank": "hazard_rank_true_v08"})
        elif "hazard_score" in out.columns:
            out["hazard_rank_true_v08"] = out["hazard_score"].rank(method="min", ascending=False).astype(int)
        return out
    return pd.DataFrame({"cell_id": []})


def build_flags(df: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    th = cfg.get("audit_thresholds", {})
    top_n = int(th.get("old_top_hazard_rank_n", 50))
    low_comp = float(th.get("low_old_completeness", 0.20))
    high_gain = float(th.get("high_coverage_gain", 0.50))
    large_area_gain = float(th.get("large_building_area_gain_m2", 1000))
    large_density_gain = float(th.get("large_building_density_gain", 0.10))
    min_v10_density = float(th.get("minimum_v10_building_density_for_false_positive", 0.05))

    if "hazard_rank_true_v08" in df.columns:
        df["old_hazard_top20"] = df["hazard_rank_true_v08"] <= 20
        df["old_hazard_top50"] = df["hazard_rank_true_v08"] <= 50
        df["old_hazard_topN"] = df["hazard_rank_true_v08"] <= top_n
    else:
        df["old_hazard_top20"] = False
        df["old_hazard_top50"] = False
        df["old_hazard_topN"] = False

    old_comp_col = "old_vs_osm_completeness"
    gain_col = "coverage_gain_vs_osm"
    if old_comp_col in df.columns:
        df["low_old_completeness"] = df[old_comp_col].fillna(np.inf) <= low_comp
        df["zero_old_completeness"] = df[old_comp_col].fillna(np.inf) == 0
    else:
        df["low_old_completeness"] = False
        df["zero_old_completeness"] = False
    if gain_col in df.columns:
        df["high_coverage_gain"] = df[gain_col].fillna(0) >= high_gain
    else:
        df["high_coverage_gain"] = False

    df["large_building_area_gain"] = df.get("delta_building_area_m2", pd.Series(0, index=df.index)).fillna(0) >= large_area_gain
    df["large_building_density_gain"] = df.get("delta_building_density", pd.Series(0, index=df.index)).fillna(0) >= large_density_gain
    df["v10_building_density_nontrivial"] = df.get("v10_building_density", pd.Series(0, index=df.index)).fillna(0) >= min_v10_density

    df["possible_old_dsm_gap_false_positive"] = (
        df["old_hazard_topN"]
        & df["low_old_completeness"]
        & df["high_coverage_gain"]
        & df["v10_building_density_nontrivial"]
    )

    flags = []
    for _, r in df.iterrows():
        f = []
        if r.get("old_hazard_top20", False): f.append("old_top20_hazard")
        elif r.get("old_hazard_top50", False): f.append("old_top50_hazard")
        if r.get("zero_old_completeness", False): f.append("zero_old_completeness")
        elif r.get("low_old_completeness", False): f.append("low_old_completeness")
        if r.get("high_coverage_gain", False): f.append("high_coverage_gain")
        if r.get("large_building_density_gain", False): f.append("large_building_density_gain")
        if r.get("possible_old_dsm_gap_false_positive", False): f.append("possible_old_dsm_gap_false_positive")
        flags.append(";".join(f))
    df["audit_flags"] = flags
    return df


def make_report(df: pd.DataFrame, fp: pd.DataFrame, cfg: dict[str, Any], out: Path) -> None:
    lines: list[str] = []
    lines.append("# v10-beta morphology shift audit report")
    lines.append("")
    lines.append("This report audits how the reviewed v10 augmented building DSM changes basic building morphology relative to the old v08/current DSM.")
    lines.append("")
    lines.append("**Important:** This is not final heat-hazard reranking. Final hazard ranking requires v10 UMEP SVF/shadow recomputation.")
    lines.append("")
    lines.append(f"Rows: **{len(df)}**")
    lines.append(f"Possible old DSM-gap false-positive candidates: **{len(fp)}**")
    lines.append("")

    count_cols = ["old_hazard_top20", "old_hazard_top50", "low_old_completeness", "zero_old_completeness", "high_coverage_gain", "large_building_density_gain", "possible_old_dsm_gap_false_positive"]
    present = [c for c in count_cols if c in df.columns]
    if present:
        counts = {c: int(df[c].fillna(False).sum()) for c in present}
        lines.append("## Flag counts")
        lines.append("```text")
        lines.append(pd.Series(counts).to_string())
        lines.append("```")
        lines.append("")

    summary_cols = [
        "old_building_density", "v10_building_density", "delta_building_density",
        "old_building_area_m2", "v10_building_area_m2", "delta_building_area_m2",
        "old_vs_osm_completeness", "reviewed_vs_osm_completeness", "coverage_gain_vs_osm"
    ]
    present = [c for c in summary_cols if c in df.columns]
    if present:
        lines.append("## Summary statistics")
        lines.append("```text")
        lines.append(df[present].describe().to_string())
        lines.append("```")
        lines.append("")

    if not fp.empty:
        cols = [c for c in [
            "cell_id", "hazard_rank_true_v08", "hazard_score", "old_vs_osm_completeness", "reviewed_vs_osm_completeness", "coverage_gain_vs_osm",
            "old_building_density", "v10_building_density", "delta_building_density", "delta_building_area_m2", "audit_flags"
        ] if c in fp.columns]
        lines.append("## Top possible old DSM-gap false-positive candidates")
        lines.append("```text")
        lines.append(fp.sort_values(["hazard_rank_true_v08" if "hazard_rank_true_v08" in fp.columns else "cell_id"]).head(40)[cols].to_string(index=False))
        lines.append("```")
        lines.append("")

    critical = cfg.get("critical_cells", [])
    if critical:
        sub = df[df["cell_id"].isin(critical)].copy()
        if not sub.empty:
            cols = [c for c in [
                "cell_id", "hazard_rank_true_v08", "old_vs_osm_completeness", "reviewed_vs_osm_completeness", "coverage_gain_vs_osm",
                "old_building_density", "v10_building_density", "delta_building_density", "audit_flags"
            ] if c in sub.columns]
            lines.append("## Critical cells")
            lines.append("```text")
            lines.append(sub[cols].to_string(index=False))
            lines.append("```")
            lines.append("")

    lines.append("## Interpretation")
    lines.append("- Cells flagged as possible old DSM-gap false positives were highly ranked under the old current-DSM hazard layer but had low old building completeness and high v10 coverage gain.")
    lines.append("- This audit should guide which cells to inspect before final v10 hazard ranking.")
    lines.append("- Final hazard ranking should wait until v10 UMEP SVF/shadow are recomputed using the reviewed DSM.")

    ensure_parent(out)
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build v10 old-vs-new morphology shift audit.")
    parser.add_argument("--config", default="configs/v10/v10_beta_morphology_config.example.json")
    args = parser.parse_args()

    cfg = read_json(Path(args.config))
    outs = cfg["outputs"]
    morph_path = Path(outs["basic_morphology_csv"])
    if not morph_path.exists():
        raise FileNotFoundError(f"Run v10_beta_compute_basic_morphology.py first: {morph_path}")
    df = pd.read_csv(morph_path)

    ranking = load_old_ranking(cfg)
    if not ranking.empty:
        df = df.merge(ranking, on="cell_id", how="left")

    comp_path = locate_completeness_csv(cfg)
    if comp_path is not None and comp_path.exists():
        comp = pd.read_csv(comp_path)
        comp = normalise_completeness_cols(comp)
        comp_cols = ["cell_id"] + [c for c in [
            "old_vs_osm_completeness", "reviewed_vs_osm_completeness", "coverage_gain_vs_osm",
            "old_dsm_area_m2", "reviewed_dsm_area_m2", "osm_area_m2", "reviewed_minus_old_dsm_area_m2"
        ] if c in comp.columns]
        df = df.merge(comp[comp_cols].drop_duplicates("cell_id"), on="cell_id", how="left")
    else:
        print("[WARN] No completeness per-cell CSV found. False-positive flags will be incomplete.")

    df = build_flags(df, cfg)

    out_csv = Path(outs["shift_audit_csv"])
    ensure_parent(out_csv)
    df.to_csv(out_csv, index=False)

    # False positives.
    fp = df[df["possible_old_dsm_gap_false_positive"]].copy()
    if "hazard_rank_true_v08" in fp.columns:
        fp = fp.sort_values("hazard_rank_true_v08")
    out_fp = Path(outs["false_positive_candidates_csv"])
    ensure_parent(out_fp)
    fp.to_csv(out_fp, index=False)

    # Old top50.
    if "hazard_rank_true_v08" in df.columns:
        top50 = df[df["hazard_rank_true_v08"] <= 50].sort_values("hazard_rank_true_v08")
    else:
        top50 = df.head(0)
    out_top50 = Path(outs["old_top50_shift_csv"])
    ensure_parent(out_top50)
    top50.to_csv(out_top50, index=False)

    out_report = Path(outs["shift_audit_report"])
    make_report(df, fp, cfg, out_report)

    print("[OK] shift audit CSV:", out_csv)
    print("[OK] false-positive candidates:", out_fp)
    print("[OK] old top50 shift:", out_top50)
    print("[OK] report:", out_report)


if __name__ == "__main__":
    main()
