"""
OpenHeat v0.8 risk scenario generator

Purpose
-------
Generate multiple v0.8 risk-priority scenarios from the UMEP+vegetation
hotspot ranking table:

1. hazard-only ranking
2. conservative hazard-conditioned risk ranking
3. social-sensitive hazard-conditioned risk ranking
4. optional candidate-only policy ranking within the top-hazard candidate set

This script does not change the heat-hazard model. It only creates additional
risk-prioritisation columns and QA summaries.

Default input:
  outputs/v08_umep_with_veg_forecast_live/v08_risk_hotspot_ranking_conditioned.csv

Default outputs:
  outputs/v08_umep_with_veg_forecast_live/risk_scenarios/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd


def robust_minmax(s: pd.Series, lower_q: float = 0.05, upper_q: float = 0.95) -> pd.Series:
    """Robust 0-1 scaling with quantile clipping."""
    x = pd.to_numeric(s, errors="coerce")
    lo = x.quantile(lower_q)
    hi = x.quantile(upper_q)
    if pd.isna(lo) or pd.isna(hi) or hi <= lo:
        return pd.Series(0.0, index=s.index)
    return ((x - lo) / (hi - lo)).clip(0, 1).fillna(0)


def rank_desc(s: pd.Series) -> pd.Series:
    """Rank high values as 1."""
    return pd.to_numeric(s, errors="coerce").rank(method="min", ascending=False).astype("Int64")


def top_set(df: pd.DataFrame, rank_col: str, n: int) -> set:
    return set(df.nsmallest(n, rank_col)["cell_id"].astype(str))


def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    required = ["cell_id", "hazard_score"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")

    df = df.copy()
    df["hazard_score"] = pd.to_numeric(df["hazard_score"], errors="coerce")
    if df["hazard_score"].isna().all():
        raise ValueError("hazard_score is entirely missing or non-numeric.")

    if "vulnerability_score_v071" not in df.columns:
        print("[WARN] vulnerability_score_v071 missing; using 0.")
        df["vulnerability_score_v071"] = 0.0
    if "outdoor_exposure_score_v071" not in df.columns:
        print("[WARN] outdoor_exposure_score_v071 missing; using 0.")
        df["outdoor_exposure_score_v071"] = 0.0

    df["vulnerability_score_v071"] = pd.to_numeric(
        df["vulnerability_score_v071"], errors="coerce"
    ).fillna(0).clip(0, 1)
    df["outdoor_exposure_score_v071"] = pd.to_numeric(
        df["outdoor_exposure_score_v071"], errors="coerce"
    ).fillna(0).clip(0, 1)

    # True heat-hazard ranks.
    df["hazard_rank_true_v08"] = rank_desc(df["hazard_score"])
    if "max_utci_c" in df.columns:
        df["utci_rank_true_v08"] = rank_desc(df["max_utci_c"])

    return df


def compute_conditioned_score(
    df: pd.DataFrame,
    candidate_mask: pd.Series,
    hazard_weight: float,
    vulnerability_weight: float,
    exposure_weight: float,
    penalty_factor: float,
    score_col: str,
    rank_col: str,
) -> pd.DataFrame:
    """Compute hazard-conditioned multiplicative risk score."""
    h = df["hazard_score"]
    v = df["vulnerability_score_v071"]
    e = df["outdoor_exposure_score_v071"]

    score = hazard_weight * h + vulnerability_weight * (h * v) + exposure_weight * (h * e)
    score = score.astype(float)
    score.loc[~candidate_mask] = penalty_factor * h.loc[~candidate_mask]

    df[score_col] = score
    df[rank_col] = rank_desc(df[score_col])
    return df


def compute_candidate_policy_score(
    df: pd.DataFrame,
    candidate_mask: pd.Series,
    hazard_weight: float,
    vulnerability_weight: float,
    exposure_weight: float,
    penalty_factor: float,
) -> pd.DataFrame:
    """
    Compute a policy scenario that first selects high-hazard candidates, then
    re-ranks within candidates using normalised hazard + social factors.

    This is intentionally more social-sensitive than the conservative score.
    """
    out = df.copy()
    out["hazard_score_within_candidates"] = 0.0
    if candidate_mask.sum() > 1:
        out.loc[candidate_mask, "hazard_score_within_candidates"] = robust_minmax(
            out.loc[candidate_mask, "hazard_score"], 0.0, 1.0
        )
    elif candidate_mask.sum() == 1:
        out.loc[candidate_mask, "hazard_score_within_candidates"] = 1.0

    score = (
        hazard_weight * out["hazard_score_within_candidates"]
        + vulnerability_weight * out["vulnerability_score_v071"]
        + exposure_weight * out["outdoor_exposure_score_v071"]
    )
    # Non-candidates are kept below candidates, while preserving some hazard order.
    score.loc[~candidate_mask] = penalty_factor * out.loc[~candidate_mask, "hazard_score"]

    out["risk_priority_score_v08_candidate_policy"] = score
    out["risk_rank_v08_candidate_policy"] = rank_desc(score)
    return out


def overlap_row(df: pd.DataFrame, rank_col: str, top_n: int) -> Dict[str, object]:
    hazard = top_set(df, "hazard_rank_true_v08", top_n)
    scenario = top_set(df, rank_col, top_n)
    return {
        "scenario_rank_col": rank_col,
        "top_n": top_n,
        "overlap_with_hazard_top_n": len(hazard & scenario),
        "risk_only_cells": ", ".join(sorted(scenario - hazard)),
        "hazard_only_cells": ", ".join(sorted(hazard - scenario)),
    }


def summarise_top(df: pd.DataFrame, rank_col: str, top_n: int) -> Dict[str, object]:
    top = df.nsmallest(top_n, rank_col)
    row: Dict[str, object] = {"rank_col": rank_col, "top_n": top_n, "n": len(top)}
    for col in [
        "hazard_score",
        "max_utci_c",
        "max_wbgt_proxy_c",
        "vulnerability_score_v071",
        "outdoor_exposure_score_v071",
        "svf",
        "shade_fraction",
        "gvi_percent",
        "tree_canopy_fraction",
        "ndvi_mean",
        "road_fraction",
        "building_density",
    ]:
        if col in top.columns:
            x = pd.to_numeric(top[col], errors="coerce")
            row[f"{col}_min"] = x.min()
            row[f"{col}_mean"] = x.mean()
            row[f"{col}_max"] = x.max()
    return row


def make_markdown_report(
    df: pd.DataFrame,
    overlap_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    args: argparse.Namespace,
) -> str:
    lines: List[str] = []
    lines.append("# OpenHeat v0.8 risk scenario QA report")
    lines.append("")
    lines.append(f"Input: `{args.input}`")
    lines.append(f"Rows: **{len(df)}**")
    lines.append(f"Candidate quantile: **p{int(args.candidate_quantile*100)}**")
    lines.append(f"Candidate cells: **{int(df['hazard_candidate_v08'].sum())} / {len(df)}**")
    lines.append("")
    lines.append("## Scenario definitions")
    lines.append("")
    lines.append("- `hazard_rank_true_v08`: pure physical heat-hazard ranking by `hazard_score`.")
    lines.append("- `risk_rank_v08_conditioned`: conservative hazard-conditioned ranking.")
    lines.append("- `risk_rank_v08_social_conditioned`: social-sensitive hazard-conditioned ranking.")
    lines.append("- `risk_rank_v08_candidate_policy`: two-stage policy scenario: select high-hazard candidates, then re-rank by hazard + vulnerability + exposure.")
    lines.append("")
    lines.append("## Top-N overlap with hazard ranking")
    lines.append("")
    lines.append(overlap_df.to_string(index=False))
    lines.append("")
    lines.append("## Top-N summaries")
    lines.append("")
    lines.append(summary_df.to_string(index=False))
    lines.append("")
    lines.append("## Interpretation guidance")
    lines.append("")
    lines.append("- Use `hazard_rank_true_v08` to show where physical heat hazard is highest.")
    lines.append("- Use `risk_rank_v08_conditioned` for a conservative heat-hazard-first intervention priority.")
    lines.append("- Use `risk_rank_v08_social_conditioned` to test how priorities shift when vulnerability and public outdoor exposure receive greater weight.")
    lines.append("- Use `risk_rank_v08_candidate_policy` as a policy-oriented sensitivity layer, not as a physically validated health-risk probability.")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("These scores are static prioritisation scenarios. They do not estimate observed pedestrian counts, real-time exposed elderly populations, or heat illness probability. Vulnerability and exposure proxies should be interpreted as open-data decision-support layers.")
    lines.append("")
    return "\n".join(lines)


def write_geojson_if_possible(df: pd.DataFrame, grid_geojson: str, out_geojson: Path) -> None:
    if not grid_geojson:
        print("[INFO] No grid GeoJSON provided; skipping GeoJSON output.")
        return
    p = Path(grid_geojson)
    if not p.exists():
        print(f"[WARN] Grid GeoJSON not found, skipping GeoJSON: {p}")
        return
    try:
        import geopandas as gpd
    except Exception as exc:  # pragma: no cover
        print(f"[WARN] geopandas unavailable, skipping GeoJSON: {exc}")
        return

    geom = gpd.read_file(p)
    if "cell_id" not in geom.columns:
        print("[WARN] grid GeoJSON has no cell_id; skipping GeoJSON output.")
        return
    geom = geom[["cell_id", "geometry"]].drop_duplicates("cell_id")
    gout = geom.merge(df, on="cell_id", how="inner")
    missing = set(df["cell_id"].astype(str)) - set(gout["cell_id"].astype(str))
    if missing:
        missing_path = out_geojson.with_suffix(".missing_geometry_cells.csv")
        pd.DataFrame({"cell_id": sorted(missing)}).to_csv(missing_path, index=False)
        print(f"[WARN] {len(missing)} rows missing geometry; wrote {missing_path}")
    gout = gpd.GeoDataFrame(gout, geometry="geometry", crs=geom.crs)
    gout = gout[gout.geometry.notna()].copy()
    gout.to_file(out_geojson, driver="GeoJSON")
    print("[OK] GeoJSON:", out_geojson)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate v0.8 risk scenario rankings.")
    parser.add_argument(
        "--input",
        default="outputs/v08_umep_with_veg_forecast_live/v08_risk_hotspot_ranking_conditioned.csv",
        help="Input v0.8 ranking CSV with hazard_score and v071 vulnerability/exposure columns.",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/v08_umep_with_veg_forecast_live/risk_scenarios",
        help="Output directory for scenario CSV/QA files.",
    )
    parser.add_argument(
        "--grid-geojson",
        default="outputs/v08_umep_with_veg_forecast_live/v08_umep_with_veg_hotspot_ranking_with_grid_features.geojson",
        help="Optional grid GeoJSON or hotspot GeoJSON containing cell_id and geometry.",
    )
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--candidate-quantile", type=float, default=0.75)
    parser.add_argument("--penalty-factor", type=float, default=0.50)
    parser.add_argument("--cons-hazard", type=float, default=0.75)
    parser.add_argument("--cons-vuln", type=float, default=0.15)
    parser.add_argument("--cons-exposure", type=float, default=0.10)
    parser.add_argument("--social-hazard", type=float, default=0.55)
    parser.add_argument("--social-vuln", type=float, default=0.30)
    parser.add_argument("--social-exposure", type=float, default=0.15)
    parser.add_argument("--policy-hazard", type=float, default=0.50)
    parser.add_argument("--policy-vuln", type=float, default=0.35)
    parser.add_argument("--policy-exposure", type=float, default=0.15)
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    df = pd.read_csv(input_path)
    df = ensure_required_columns(df)

    q = df["hazard_score"].quantile(args.candidate_quantile)
    df["hazard_candidate_v08"] = df["hazard_score"] >= q

    # Conservative scenario: heat-hazard-first.
    df = compute_conditioned_score(
        df,
        df["hazard_candidate_v08"],
        args.cons_hazard,
        args.cons_vuln,
        args.cons_exposure,
        args.penalty_factor,
        "risk_priority_score_v08_conditioned",
        "risk_rank_v08_conditioned",
    )

    # Social-sensitive scenario: still hazard-conditioned, but larger social modifier.
    df = compute_conditioned_score(
        df,
        df["hazard_candidate_v08"],
        args.social_hazard,
        args.social_vuln,
        args.social_exposure,
        args.penalty_factor,
        "risk_priority_score_v08_social_conditioned",
        "risk_rank_v08_social_conditioned",
    )

    # Candidate-policy scenario: re-rank within high-hazard candidates.
    df = compute_candidate_policy_score(
        df,
        df["hazard_candidate_v08"],
        args.policy_hazard,
        args.policy_vuln,
        args.policy_exposure,
        args.penalty_factor,
    )

    out_csv = out_dir / "v08_risk_scenario_rankings.csv"
    df.to_csv(out_csv, index=False)
    print("[OK] CSV:", out_csv)

    rank_cols = [
        "risk_rank_v08_conditioned",
        "risk_rank_v08_social_conditioned",
        "risk_rank_v08_candidate_policy",
    ]
    overlap_df = pd.DataFrame([overlap_row(df, c, args.top_n) for c in rank_cols])
    overlap_csv = out_dir / "v08_risk_scenario_topn_overlap.csv"
    overlap_df.to_csv(overlap_csv, index=False)
    print("[OK] overlap:", overlap_csv)

    summary_rows = [summarise_top(df, "hazard_rank_true_v08", args.top_n)]
    summary_rows += [summarise_top(df, c, args.top_n) for c in rank_cols]
    summary_df = pd.DataFrame(summary_rows)
    summary_csv = out_dir / "v08_risk_scenario_topn_summary.csv"
    summary_df.to_csv(summary_csv, index=False)
    print("[OK] summary:", summary_csv)

    top_tables: List[pd.DataFrame] = []
    display_cols = [
        "cell_id",
        "hazard_rank_true_v08",
        "max_utci_c",
        "hazard_score",
        "vulnerability_score_v071",
        "outdoor_exposure_score_v071",
        "dominant_subzone",
        "svf",
        "shade_fraction",
        "gvi_percent",
        "ndvi_mean",
    ]
    for c in ["hazard_rank_true_v08"] + rank_cols:
        top = df.nsmallest(args.top_n, c).copy()
        top.insert(0, "scenario", c)
        top_tables.append(top[[x for x in ["scenario", c] + display_cols if x in top.columns]])
    top_df = pd.concat(top_tables, ignore_index=True, sort=False)
    top_csv = out_dir / "v08_risk_scenario_top_cells.csv"
    top_df.to_csv(top_csv, index=False)
    print("[OK] top cells:", top_csv)

    report = make_markdown_report(df, overlap_df, summary_df, args)
    report_path = out_dir / "v08_risk_scenario_QA_report.md"
    report_path.write_text(report, encoding="utf-8")
    print("[OK] report:", report_path)

    meta = {
        "input": str(input_path),
        "candidate_quantile": args.candidate_quantile,
        "hazard_p75_threshold": float(q),
        "top_n": args.top_n,
        "penalty_factor": args.penalty_factor,
        "weights": {
            "conservative": {
                "hazard": args.cons_hazard,
                "vulnerability_x_hazard": args.cons_vuln,
                "exposure_x_hazard": args.cons_exposure,
            },
            "social_sensitive": {
                "hazard": args.social_hazard,
                "vulnerability_x_hazard": args.social_vuln,
                "exposure_x_hazard": args.social_exposure,
            },
            "candidate_policy": {
                "hazard_within_candidate": args.policy_hazard,
                "vulnerability": args.policy_vuln,
                "exposure": args.policy_exposure,
            },
        },
    }
    meta_path = out_dir / "v08_risk_scenario_metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("[OK] metadata:", meta_path)

    write_geojson_if_possible(
        df,
        args.grid_geojson,
        out_dir / "v08_risk_scenario_rankings.geojson",
    )

    print("\nTop-N overlap with hazard ranking:")
    print(overlap_df.to_string(index=False))
    print("\nTop cells by social-sensitive scenario:")
    cols = [
        "risk_rank_v08_social_conditioned",
        "cell_id",
        "hazard_rank_true_v08",
        "max_utci_c",
        "hazard_score",
        "risk_priority_score_v08_social_conditioned",
        "vulnerability_score_v071",
        "outdoor_exposure_score_v071",
    ]
    print(df.nsmallest(args.top_n, "risk_rank_v08_social_conditioned")[[c for c in cols if c in df.columns]].to_string(index=False))


if __name__ == "__main__":
    main()
