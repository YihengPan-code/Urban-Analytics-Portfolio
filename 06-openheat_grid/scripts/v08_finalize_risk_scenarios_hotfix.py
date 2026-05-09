"""
OpenHeat v0.8 risk-scenarios finalisation hotfix.

Use this when `v08_generate_risk_scenarios.py` has already written
`v08_risk_scenario_rankings.csv` but fails while concatenating top-N tables
with pandas InvalidIndexError caused by duplicate/non-unique columns.

It regenerates:
- v08_risk_scenario_top_cells.csv
- v08_risk_scenario_topn_overlap.csv
- v08_risk_scenario_topn_summary.csv
- v08_risk_scenario_rankings.geojson, if geometry is available
- v08_risk_scenario_QA_report.md
- v08_risk_scenario_metadata.json
"""
from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

try:
    import geopandas as gpd
except Exception:  # pragma: no cover
    gpd = None


DEFAULT_SCENARIO_CSV = Path(
    "outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_rankings.csv"
)
DEFAULT_OUT_DIR = Path("outputs/v08_umep_with_veg_forecast_live/risk_scenarios")
DEFAULT_GEOMETRY = Path(
    "outputs/v08_umep_with_veg_forecast_live/v08_umep_with_veg_hotspot_ranking_with_grid_features.geojson"
)

SCENARIOS: Dict[str, Dict[str, str]] = {
    "hazard_only": {
        "rank_col": "hazard_rank_true_v08",
        "score_col": "hazard_score",
        "label": "Physical heat-hazard ranking",
    },
    "conservative_conditioned": {
        "rank_col": "risk_rank_v08_conditioned",
        "score_col": "risk_priority_score_v08_conditioned",
        "label": "Conservative hazard-conditioned risk ranking",
    },
    "social_conditioned": {
        "rank_col": "risk_rank_v08_social_conditioned",
        "score_col": "risk_priority_score_v08_social_conditioned",
        "label": "Social-sensitive hazard-conditioned risk ranking",
    },
    "candidate_policy": {
        "rank_col": "risk_rank_v08_candidate_policy",
        "score_col": "risk_priority_score_v08_candidate_policy",
        "label": "Candidate-zone policy ranking",
    },
}

SUMMARY_COLS = [
    "max_utci_c",
    "max_wbgt_proxy_c",
    "hazard_score",
    "risk_priority_score",
    "risk_priority_score_v08_conditioned",
    "risk_priority_score_v08_social_conditioned",
    "risk_priority_score_v08_candidate_policy",
    "vulnerability_score_v071",
    "outdoor_exposure_score_v071",
    "elderly_pct_65plus",
    "children_pct_under5",
    "svf",
    "shade_fraction",
    "gvi_percent",
    "tree_canopy_fraction",
    "ndvi_mean",
    "road_fraction",
    "building_density",
]

DISPLAY_COLS = [
    "scenario",
    "scenario_label",
    "scenario_rank",
    "scenario_score",
    "cell_id",
    "hazard_rank_true_v08",
    "risk_rank_v08_conditioned",
    "risk_rank_v08_social_conditioned",
    "risk_rank_v08_candidate_policy",
    "max_utci_c",
    "max_wbgt_proxy_c",
    "hazard_score",
    "vulnerability_score_v071",
    "outdoor_exposure_score_v071",
    "elderly_pct_65plus",
    "children_pct_under5",
    "dominant_subzone",
    "land_use_hint",
    "svf",
    "shade_fraction",
    "gvi_percent",
    "tree_canopy_fraction",
    "ndvi_mean",
    "road_fraction",
    "building_density",
]


def make_unique_columns(cols: List[str]) -> List[str]:
    """Return unique column names while preserving order."""
    counts: Dict[str, int] = {}
    out: List[str] = []
    for c in cols:
        if c not in counts:
            counts[c] = 0
            out.append(c)
        else:
            counts[c] += 1
            out.append(f"{c}__dup{counts[c]}")
    return out


def read_rankings(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Scenario ranking CSV not found: {path}")
    df = pd.read_csv(path)
    if df.columns.duplicated().any():
        dupes = df.columns[df.columns.duplicated()].tolist()
        print(f"[WARN] Duplicate columns detected and renamed: {dupes}")
        df.columns = make_unique_columns(list(df.columns))
    if "cell_id" not in df.columns:
        raise KeyError("Scenario ranking CSV must contain cell_id")
    return df


def available_scenarios(df: pd.DataFrame) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for key, meta in SCENARIOS.items():
        rank_col = meta["rank_col"]
        score_col = meta["score_col"]
        if rank_col in df.columns:
            out[key] = meta.copy()
            if score_col not in df.columns:
                print(f"[WARN] {key}: score column missing: {score_col}; using rank-only output")
        else:
            print(f"[WARN] Scenario skipped because rank column is missing: {rank_col}")
    if not out:
        raise KeyError("No recognised scenario rank columns found.")
    return out


def make_top_cells(df: pd.DataFrame, scenarios: Dict[str, Dict[str, str]], top_n: int) -> pd.DataFrame:
    top_tables: List[pd.DataFrame] = []
    for key, meta in scenarios.items():
        rank_col = meta["rank_col"]
        score_col = meta["score_col"]
        sub = df.dropna(subset=[rank_col]).nsmallest(top_n, rank_col).copy()
        sub = sub.loc[:, ~sub.columns.duplicated()].copy()
        sub.insert(0, "scenario", key)
        sub.insert(1, "scenario_label", meta["label"])
        sub.insert(2, "scenario_rank", sub[rank_col].astype("Int64"))
        if score_col in sub.columns:
            sub.insert(3, "scenario_score", sub[score_col])
        else:
            sub.insert(3, "scenario_score", pd.NA)
        cols = [c for c in DISPLAY_COLS if c in sub.columns]
        top_tables.append(sub[cols].copy())
    return pd.concat(top_tables, ignore_index=True, sort=False)


def top_set(df: pd.DataFrame, rank_col: str, n: int) -> set:
    return set(df.dropna(subset=[rank_col]).nsmallest(n, rank_col)["cell_id"])


def make_overlap(df: pd.DataFrame, scenarios: Dict[str, Dict[str, str]], top_n: int) -> pd.DataFrame:
    rows = []
    for a, b in combinations(scenarios.keys(), 2):
        a_rank = scenarios[a]["rank_col"]
        b_rank = scenarios[b]["rank_col"]
        a_set = top_set(df, a_rank, top_n)
        b_set = top_set(df, b_rank, top_n)
        rows.append(
            {
                "scenario_a": a,
                "scenario_b": b,
                "top_n": top_n,
                "overlap_count": len(a_set & b_set),
                "overlap_fraction": len(a_set & b_set) / top_n if top_n else pd.NA,
                "a_only_count": len(a_set - b_set),
                "b_only_count": len(b_set - a_set),
                "a_only_cells": ",".join(sorted(a_set - b_set)),
                "b_only_cells": ",".join(sorted(b_set - a_set)),
            }
        )
    return pd.DataFrame(rows)


def make_summary(df: pd.DataFrame, scenarios: Dict[str, Dict[str, str]], top_n: int) -> pd.DataFrame:
    rows = []
    numeric_cols = [c for c in SUMMARY_COLS if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    for key, meta in scenarios.items():
        rank_col = meta["rank_col"]
        top = df.dropna(subset=[rank_col]).nsmallest(top_n, rank_col)
        row = {"scenario": key, "scenario_label": meta["label"], "top_n": top_n, "n_cells": len(top)}
        for c in numeric_cols:
            row[f"{c}_mean"] = top[c].mean()
            row[f"{c}_median"] = top[c].median()
            row[f"{c}_min"] = top[c].min()
            row[f"{c}_max"] = top[c].max()
        rows.append(row)
    return pd.DataFrame(rows)


def write_geojson(df: pd.DataFrame, geometry_path: Path, out_path: Path) -> Tuple[int, int]:
    if gpd is None:
        print("[WARN] geopandas unavailable; GeoJSON not written.")
        return len(df), 0
    if not geometry_path.exists():
        print(f"[WARN] Geometry source not found; GeoJSON not written: {geometry_path}")
        return len(df), 0
    geom = gpd.read_file(geometry_path)
    if geom.columns.duplicated().any():
        geom.columns = make_unique_columns(list(geom.columns))
    if "cell_id" not in geom.columns:
        print(f"[WARN] Geometry source has no cell_id; GeoJSON not written: {geometry_path}")
        return len(df), 0
    geom = geom[["cell_id", "geometry"]].drop_duplicates("cell_id")
    gout = geom.merge(df, on="cell_id", how="inner")
    gout = gpd.GeoDataFrame(gout, geometry="geometry", crs=geom.crs)
    before = len(gout)
    gout = gout[gout.geometry.notna()].copy()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gout.to_file(out_path, driver="GeoJSON")
    missing = len(df) - len(gout)
    return before, missing


def write_report(
    report_path: Path,
    df: pd.DataFrame,
    scenarios: Dict[str, Dict[str, str]],
    overlap: pd.DataFrame,
    summary: pd.DataFrame,
    top_cells: pd.DataFrame,
    top_n: int,
    geo_missing: int,
):
    lines = []
    lines.append("# OpenHeat v0.8 risk-scenario finalisation QA report")
    lines.append("")
    lines.append(f"Scenario ranking rows: **{len(df)}**")
    lines.append(f"Top-N used: **{top_n}**")
    lines.append(f"GeoJSON rows without geometry: **{geo_missing}**")
    lines.append("")
    lines.append("## Available scenarios")
    for key, meta in scenarios.items():
        lines.append(f"- `{key}`: rank=`{meta['rank_col']}`, score=`{meta['score_col']}`")
    lines.append("")
    lines.append("## Top-N overlap")
    if not overlap.empty:
        lines.append(overlap[["scenario_a", "scenario_b", "overlap_count", "top_n", "overlap_fraction"]].to_string(index=False))
    lines.append("")
    lines.append("## Scenario top-cell summary")
    basic_cols = ["scenario", "top_n", "n_cells"]
    for c in ["max_utci_c_mean", "hazard_score_mean", "vulnerability_score_v071_mean", "outdoor_exposure_score_v071_mean", "svf_mean", "shade_fraction_mean"]:
        if c in summary.columns:
            basic_cols.append(c)
    lines.append(summary[[c for c in basic_cols if c in summary.columns]].to_string(index=False))
    lines.append("")
    lines.append("## Top cells preview")
    preview_cols = ["scenario", "scenario_rank", "cell_id", "scenario_score", "hazard_rank_true_v08", "max_utci_c", "hazard_score", "vulnerability_score_v071", "outdoor_exposure_score_v071"]
    lines.append(top_cells[[c for c in preview_cols if c in top_cells.columns]].head(60).to_string(index=False))
    lines.append("")
    lines.append("## Interpretation note")
    lines.append("- Use `hazard_rank_true_v08` for the pure physical heat-hazard map.")
    lines.append("- Use `risk_rank_v08_conditioned` for a conservative heat-hazard-anchored priority scenario.")
    lines.append("- Use `risk_rank_v08_social_conditioned` for a more equity-sensitive scenario within heat-hazard conditions.")
    lines.append("- Use `risk_rank_v08_candidate_policy` as a policy scenario that first selects high-hazard candidates and then reorders them by social vulnerability/exposure.")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario-csv", default=str(DEFAULT_SCENARIO_CSV))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--geometry", default=str(DEFAULT_GEOMETRY))
    parser.add_argument("--top-n", type=int, default=20)
    args = parser.parse_args()

    scenario_csv = Path(args.scenario_csv)
    out_dir = Path(args.out_dir)
    geometry_path = Path(args.geometry)
    top_n = args.top_n

    df = read_rankings(scenario_csv)
    scenarios = available_scenarios(df)
    out_dir.mkdir(parents=True, exist_ok=True)

    top_cells = make_top_cells(df, scenarios, top_n)
    overlap = make_overlap(df, scenarios, top_n)
    summary = make_summary(df, scenarios, top_n)

    top_cells_path = out_dir / "v08_risk_scenario_top_cells.csv"
    overlap_path = out_dir / "v08_risk_scenario_topn_overlap.csv"
    summary_path = out_dir / "v08_risk_scenario_topn_summary.csv"
    geojson_path = out_dir / "v08_risk_scenario_rankings.geojson"
    report_path = out_dir / "v08_risk_scenario_QA_report.md"
    metadata_path = out_dir / "v08_risk_scenario_metadata.json"

    top_cells.to_csv(top_cells_path, index=False)
    overlap.to_csv(overlap_path, index=False)
    summary.to_csv(summary_path, index=False)
    _, geo_missing = write_geojson(df, geometry_path, geojson_path)

    write_report(report_path, df, scenarios, overlap, summary, top_cells, top_n, geo_missing)

    metadata = {
        "scenario_csv": str(scenario_csv),
        "geometry_source": str(geometry_path),
        "top_n": top_n,
        "rows": int(len(df)),
        "available_scenarios": scenarios,
        "outputs": {
            "top_cells": str(top_cells_path),
            "overlap": str(overlap_path),
            "summary": str(summary_path),
            "geojson": str(geojson_path),
            "report": str(report_path),
        },
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("[OK] top cells:", top_cells_path)
    print("[OK] overlap:", overlap_path)
    print("[OK] summary:", summary_path)
    print("[OK] geojson:", geojson_path if gpd is not None else "skipped")
    print("[OK] report:", report_path)
    print("[OK] metadata:", metadata_path)


if __name__ == "__main__":
    main()
