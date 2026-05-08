from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def weighted_sum(df: pd.DataFrame, weights: dict[str, float], out_col: str) -> pd.Series:
    total = pd.Series(0.0, index=df.index)
    used = []
    for col, w in weights.items():
        if col in df.columns:
            total += float(w) * pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            used.append(col)
    if not used:
        raise ValueError(f"None of the weight columns for {out_col} were found: {weights}")
    return total.clip(0, 1)


def apply_v071_risk(config: dict[str, Any], forecast_dir: str | Path | None = None) -> dict[str, Path]:
    forecast_dir = ROOT / (forecast_dir or config.get("forecast_dir", "outputs/v07_beta_final_forecast_live"))
    out_dir = ROOT / config.get("out_dir", "outputs/v071_risk_exposure")
    out_dir.mkdir(parents=True, exist_ok=True)

    grid_csv = ROOT / config.get("out_grid_csv", "data/grid/toa_payoh_grid_v07_features_beta_final_v071_risk.csv")
    grid_geojson = ROOT / config.get("grid_geojson", "data/grid/toa_payoh_grid_v07_features.geojson")
    hotspot_path = forecast_dir / "v06_live_hotspot_ranking.csv"
    hourly_path = forecast_dir / "v06_live_hourly_grid_heatstress_forecast.csv"

    if not hotspot_path.exists():
        raise FileNotFoundError(f"Missing hotspot ranking: {hotspot_path}. Run forecast first.")
    if not grid_csv.exists():
        raise FileNotFoundError(f"Missing v0.7.1 risk grid CSV: {grid_csv}. Run v071_build_risk_exposure_features.py first.")

    h = pd.read_csv(hotspot_path)
    g = pd.read_csv(grid_csv)
    h["cell_id"] = h["cell_id"].astype(str)
    g["cell_id"] = g["cell_id"].astype(str)

    # Merge only columns not already in hotspot table; preserve forecast-derived hazard columns.
    preferred = [
        "cell_id",
        "elderly_pct_65plus", "children_pct_under5", "demographic_vulnerability_score",
        "node_vulnerability_score", "vulnerability_score_v071", "outdoor_exposure_score_v071",
        "outdoor_exposure_raw", "node_vulnerability_raw", "dominant_subzone", "dominant_planning_area",
        "bus_stop_score_raw", "mrt_exit_score_raw", "sport_facility_score_raw",
        "hawker_centre_score_raw", "eldercare_score_raw", "preschool_score_raw",
        "bus_stop_count", "mrt_exit_count", "sport_facility_count", "hawker_centre_count", "eldercare_count", "preschool_count",
        "land_use_hint", "building_density", "road_fraction", "gvi_percent", "svf", "shade_fraction",
        "mean_building_height_m", "tree_canopy_fraction", "ndvi_mean", "impervious_fraction",
    ]
    merge_cols = [c for c in preferred if c in g.columns and (c not in h.columns or c == "cell_id")]
    out = h.merge(g[merge_cols], on="cell_id", how="left")

    # Backward-compatible copies of pre-v0.7.1 risk, if present.
    if "risk_priority_score" in out.columns:
        out["risk_priority_score_pre_v071"] = out["risk_priority_score"]
    if "vulnerability_score" in out.columns:
        out["vulnerability_score_pre_v071"] = out["vulnerability_score"]
    if "exposure_score" in out.columns:
        out["exposure_score_pre_v071"] = out["exposure_score"]

    risk_weights = config.get("risk_weights", {})
    out["risk_priority_score_v071"] = weighted_sum(out, risk_weights.get("risk_priority_score_v071", {"hazard_score": 0.60, "vulnerability_score_v071": 0.25, "outdoor_exposure_score_v071": 0.15}), "risk_priority_score_v071")
    out["risk_priority_score_v071_equity"] = weighted_sum(out, risk_weights.get("risk_priority_score_v071_equity", {"hazard_score": 0.50, "vulnerability_score_v071": 0.35, "outdoor_exposure_score_v071": 0.15}), "risk_priority_score_v071_equity")
    out = out.sort_values("risk_priority_score_v071", ascending=False).reset_index(drop=True)
    out["risk_rank_v071"] = range(1, len(out) + 1)
    out = out.sort_values("rank").reset_index(drop=True)

    out_csv = out_dir / "v071_risk_hotspot_ranking.csv"
    out.to_csv(out_csv, index=False)

    # Hazard vs risk comparison.
    compare_cols = [
        "cell_id", "rank", "risk_rank_v071", "hazard_score", "risk_priority_score_v071",
        "max_utci_c", "max_wbgt_proxy_c", "vulnerability_score_v071", "outdoor_exposure_score_v071",
        "elderly_pct_65plus", "children_pct_under5", "dominant_subzone", "land_use_hint",
    ]
    compare_cols = [c for c in compare_cols if c in out.columns]
    compare = out[compare_cols].copy()
    compare["rank_delta_hazard_minus_risk"] = compare.get("rank", pd.Series(dtype=float)) - compare.get("risk_rank_v071", pd.Series(dtype=float))
    compare_path = out_dir / "v071_hazard_vs_risk_comparison.csv"
    compare.to_csv(compare_path, index=False)

    # GeoJSON.
    if grid_geojson.exists():
        grid_geo = gpd.read_file(grid_geojson)
        if grid_geo.crs is None:
            grid_geo = grid_geo.set_crs("EPSG:4326")
        geo = grid_geo[["cell_id", "geometry"]].merge(out, on="cell_id", how="right")
        geo_out = out_dir / "v071_risk_hotspot_ranking.geojson"
        geo.to_file(geo_out, driver="GeoJSON")
    else:
        geo_out = out_dir / "v071_risk_hotspot_ranking.geojson"

    # Optional hourly risk table: append static v0.7.1 scores to each cell-hour.
    hourly_out = out_dir / "v071_hourly_grid_heatstress_forecast_with_risk.csv"
    if hourly_path.exists():
        hourly = pd.read_csv(hourly_path)
        hourly["cell_id"] = hourly["cell_id"].astype(str)
        static_cols = ["cell_id", "vulnerability_score_v071", "outdoor_exposure_score_v071", "demographic_vulnerability_score", "node_vulnerability_score"]
        static_cols = [c for c in static_cols if c in g.columns]
        hourly = hourly.merge(g[static_cols], on="cell_id", how="left")
        hourly.to_csv(hourly_out, index=False)

    report_path = out_dir / "v071_risk_ranking_QA_report.md"
    report_path.write_text(make_report(out, compare), encoding="utf-8")

    return {
        "risk_hotspot_csv": out_csv,
        "hazard_vs_risk_csv": compare_path,
        "risk_hotspot_geojson": geo_out,
        "hourly_with_risk_csv": hourly_out,
        "qa_report": report_path,
    }


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows_"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        vals = []
        for c in cols:
            v = row[c]
            if isinstance(v, float):
                vals.append(f"{v:.4f}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def make_report(out: pd.DataFrame, compare: pd.DataFrame) -> str:
    lines = ["# OpenHeat v0.7.1 hazard-vs-risk ranking QA report", ""]
    lines.append(f"Cells ranked: **{len(out)}**")
    lines.append("")
    lines.append("## Top 20 by v0.7.1 risk priority")
    cols = ["risk_rank_v071", "cell_id", "rank", "hazard_score", "risk_priority_score_v071", "vulnerability_score_v071", "outdoor_exposure_score_v071", "elderly_pct_65plus", "dominant_subzone"]
    cols = [c for c in cols if c in out.columns]
    top_risk = out.sort_values("risk_priority_score_v071", ascending=False)[cols].head(20)
    lines.append(_markdown_table(top_risk))
    lines.append("")
    lines.append("## Top 20 by heat hazard")
    cols2 = ["rank", "cell_id", "hazard_score", "risk_rank_v071", "risk_priority_score_v071", "max_utci_c", "max_wbgt_proxy_c", "dominant_subzone"]
    cols2 = [c for c in cols2 if c in out.columns]
    lines.append(_markdown_table(out.sort_values("rank")[cols2].head(20)))
    lines.append("")
    lines.append("## Summary")
    for c in ["hazard_score", "risk_priority_score_v071", "vulnerability_score_v071", "outdoor_exposure_score_v071", "elderly_pct_65plus", "children_pct_under5"]:
        if c in out.columns:
            s = pd.to_numeric(out[c], errors="coerce")
            lines.append(f"- `{c}`: min={s.min():.3f}, mean={s.mean():.3f}, median={s.median():.3f}, max={s.max():.3f}")
    if "rank_delta_hazard_minus_risk" in compare.columns:
        d = pd.to_numeric(compare["rank_delta_hazard_minus_risk"], errors="coerce")
        lines.append(f"- Hazard-vs-risk rank delta: mean={d.mean():.2f}, max upward shift toward risk={d.max():.0f}, max downward shift={d.min():.0f}")
    lines.append("")
    lines.append("## Interpretation notes")
    lines.append("- `rank` is the original heat-hazard/risk ranking from the forecast engine; `risk_rank_v071` is recomputed using v0.7.1 static vulnerability/exposure proxies.")
    lines.append("- v0.7.1 does not represent observed pedestrian counts or time-of-day exposure; it is a static public-node and demographic priority layer.")
    lines.append("- Use `rank` to discuss physical heat hazard. Use `risk_rank_v071` to discuss intervention priority where heat overlaps with vulnerable residential population and public outdoor exposure potential.")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply v0.7.1 risk/exposure features to forecast hotspot ranking")
    parser.add_argument("--config", default=str(ROOT / "configs/v071_risk_exposure_config.example.json"))
    parser.add_argument("--forecast-dir", default=None)
    args = parser.parse_args()
    config = load_json(args.config)
    files = apply_v071_risk(config, forecast_dir=args.forecast_dir)
    print("[OK] v0.7.1 risk ranking generated")
    for k, v in files.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
