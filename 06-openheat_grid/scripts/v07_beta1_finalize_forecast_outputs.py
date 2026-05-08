"""OpenHeat-ToaPayoh v0.7-beta.1 finalisation utilities.

This script is intentionally non-invasive: it does not re-run the forecast model
or change model coefficients. It takes an existing forecast output directory and
an existing v0.7-beta grid-feature CSV, then produces interpretation-ready
ranking tables, optional GeoJSON, and a QA markdown report.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


DEFAULT_EXPLANATORY_COLS = [
    "cell_id",
    "lat",
    "lon",
    "centroid_x_svy21",
    "centroid_y_svy21",
    "building_density",
    "road_fraction",
    "land_use_hint",
    "land_use_raw",
    "land_use_fraction",
    "gpr_area_weighted",
    "park_distance_m",
    "large_park_distance_m",
    "water_distance_m",
    "mean_building_height_m",
    "max_building_height_m",
    "tree_canopy_fraction",
    "grass_fraction",
    "water_fraction",
    "built_up_fraction",
    "ndvi_mean",
    "impervious_fraction",
    "impervious_fraction_old_beta",
    "impervious_fraction_vector_component",
    "impervious_fraction_dw_component",
    "impervious_fraction_green_component",
    "gvi_percent",
    "svf",
    "shade_fraction",
    "elderly_proxy",
    "outdoor_exposure_proxy",
    "forecast_spatial_note",
]

SUMMARY_COLS = [
    "max_utci_c",
    "mean_utci_c",
    "max_wbgt_proxy_c",
    "mean_wbgt_proxy_c",
    "hazard_score",
    "risk_priority_score",
    "vulnerability_score",
    "exposure_score",
    "gvi_percent",
    "svf",
    "shade_fraction",
    "mean_building_height_m",
    "max_building_height_m",
    "tree_canopy_fraction",
    "grass_fraction",
    "ndvi_mean",
    "impervious_fraction",
    "building_density",
    "road_fraction",
    "park_distance_m",
    "large_park_distance_m",
    "water_distance_m",
]

TOP_TABLE_COLS = [
    "rank",
    "cell_id",
    "max_utci_c",
    "max_wbgt_proxy_c",
    "hazard_score",
    "risk_priority_score",
    "gvi_percent",
    "svf",
    "shade_fraction",
    "mean_building_height_m",
    "tree_canopy_fraction",
    "ndvi_mean",
    "impervious_fraction",
    "building_density",
    "road_fraction",
    "park_distance_m",
    "land_use_hint",
]


def _read_csv(path: Path, name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing {name}: {path}")
    return pd.read_csv(path)


def _safe_keep_cols(df: pd.DataFrame, cols: Iterable[str]) -> list[str]:
    return [c for c in cols if c in df.columns]


def _ensure_rank(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "rank" not in out.columns:
        if "risk_priority_score" in out.columns:
            out = out.sort_values("risk_priority_score", ascending=False).reset_index(drop=True)
        elif "hazard_score" in out.columns:
            out = out.sort_values("hazard_score", ascending=False).reset_index(drop=True)
        out["rank"] = np.arange(1, len(out) + 1)
    return out


def merge_explanatory_features(ranking: pd.DataFrame, grid: pd.DataFrame) -> pd.DataFrame:
    """Merge grid explanatory columns into ranking without pandas _x/_y chaos."""
    ranking = _ensure_rank(ranking)
    if "cell_id" not in ranking.columns or "cell_id" not in grid.columns:
        raise ValueError("Both ranking and grid must contain cell_id.")

    keep = ["cell_id"]
    for col in DEFAULT_EXPLANATORY_COLS:
        if col == "cell_id":
            continue
        if col in grid.columns and col not in ranking.columns:
            keep.append(col)

    out = ranking.merge(grid[keep], on="cell_id", how="left")
    return out


def build_top_vs_all_summary(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    cols = _safe_keep_cols(df, SUMMARY_COLS)
    top = df.nsmallest(top_n, "rank") if "rank" in df.columns else df.head(top_n)
    parts = []
    if cols:
        parts.append(df[cols].mean(numeric_only=True).rename("all_mean"))
        parts.append(top[cols].mean(numeric_only=True).rename(f"top{top_n}_mean"))
        parts.append(df[cols].median(numeric_only=True).rename("all_median"))
        parts.append(top[cols].median(numeric_only=True).rename(f"top{top_n}_median"))
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, axis=1)


def build_hazard_risk_comparison(df: pd.DataFrame, top_n: int = 20) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    metrics: dict[str, object] = {}
    if "hazard_score" in out.columns:
        out["hazard_rank"] = out["hazard_score"].rank(ascending=False, method="min").astype(int)
    if "risk_priority_score" in out.columns:
        out["risk_score_rank"] = out["risk_priority_score"].rank(ascending=False, method="min").astype(int)
    if "rank" in out.columns and "hazard_rank" in out.columns:
        metrics["spearman_rank_vs_hazard_rank"] = float(out["rank"].corr(out["hazard_rank"], method="spearman"))
        risk_top = set(out.nsmallest(top_n, "rank")["cell_id"])
        hazard_top = set(out.nsmallest(top_n, "hazard_rank")["cell_id"])
        metrics[f"top{top_n}_risk_hazard_overlap"] = len(risk_top & hazard_top)
    cols = _safe_keep_cols(
        out,
        [
            "rank",
            "hazard_rank",
            "risk_score_rank",
            "cell_id",
            "risk_priority_score",
            "hazard_score",
            "max_utci_c",
            "max_wbgt_proxy_c",
            "vulnerability_score",
            "exposure_score",
            "elderly_proxy",
            "outdoor_exposure_proxy",
            "land_use_hint",
        ],
    )
    return out[cols].sort_values("rank" if "rank" in cols else cols[0]), metrics


def feature_diagnostics(df: pd.DataFrame) -> dict:
    diag: dict[str, object] = {"n_cells": int(len(df))}
    if "svf" in df.columns:
        diag["svf_ge_0_98_count"] = int((df["svf"] >= 0.979).sum())
        diag["svf_ge_0_98_share"] = float((df["svf"] >= 0.979).mean())
        diag["svf_ge_0_95_count"] = int((df["svf"] >= 0.95).sum())
        diag["svf_ge_0_95_share"] = float((df["svf"] >= 0.95).mean())
        diag["svf_min"] = float(df["svf"].min())
        diag["svf_mean"] = float(df["svf"].mean())
        diag["svf_median"] = float(df["svf"].median())
        diag["svf_max"] = float(df["svf"].max())
    if "shade_fraction" in df.columns:
        diag["shade_min"] = float(df["shade_fraction"].min())
        diag["shade_mean"] = float(df["shade_fraction"].mean())
        diag["shade_median"] = float(df["shade_fraction"].median())
        diag["shade_max"] = float(df["shade_fraction"].max())
        shade_floor = max(float(df["shade_fraction"].min()) + 0.005, 0.045)
        diag["shade_floorish_count"] = int((df["shade_fraction"] <= shade_floor).sum())
        diag["shade_floorish_share"] = float((df["shade_fraction"] <= shade_floor).mean())
    if "tree_canopy_fraction" in df.columns:
        diag["tree_canopy_zero_count"] = int((df["tree_canopy_fraction"] <= 1e-9).sum())
        diag["tree_canopy_zero_share"] = float((df["tree_canopy_fraction"] <= 1e-9).mean())
    if "impervious_fraction" in df.columns:
        diag["impervious_mean"] = float(df["impervious_fraction"].mean())
        diag["impervious_median"] = float(df["impervious_fraction"].median())
        diag["impervious_ge_0_95_share"] = float((df["impervious_fraction"] >= 0.95).mean())
    if "impervious_fraction_old_beta" in df.columns:
        diag["impervious_old_mean"] = float(df["impervious_fraction_old_beta"].mean())
        diag["impervious_old_median"] = float(df["impervious_fraction_old_beta"].median())
        diag["impervious_old_ge_0_95_share"] = float((df["impervious_fraction_old_beta"] >= 0.95).mean())
    return diag


def event_window_summary(event_path: Path) -> dict:
    if not event_path.exists():
        return {"event_file_found": False}
    ev = pd.read_csv(event_path)
    out: dict[str, object] = {"event_file_found": True, "n_event_hours": int(len(ev))}
    for col in ["wbgt_alert", "utci_alert", "combined_alert", "neighbourhood_alert"]:
        if col in ev.columns:
            out[f"{col}_counts"] = ev[col].value_counts(dropna=False).to_dict()
    for col in ["max_wbgt_proxy_c", "p90_wbgt_proxy_c", "max_utci_c", "p90_utci_c"]:
        if col in ev.columns:
            out[f"{col}_max"] = float(ev[col].max())
    if "time" in ev.columns:
        if "max_utci_c" in ev.columns:
            row = ev.loc[ev["max_utci_c"].idxmax()]
            out["peak_utci_time"] = str(row.get("time", ""))
            out["peak_utci_value"] = float(row.get("max_utci_c", np.nan))
        if "max_wbgt_proxy_c" in ev.columns:
            row = ev.loc[ev["max_wbgt_proxy_c"].idxmax()]
            out["peak_wbgt_time"] = str(row.get("time", ""))
            out["peak_wbgt_value"] = float(row.get("max_wbgt_proxy_c", np.nan))
    return out


def safe_markdown_table(df: pd.DataFrame, max_rows: int = 20, float_fmt: str = ".3f") -> str:
    if df is None or df.empty:
        return "_No data available._"
    view = df.head(max_rows).copy()
    # Use pandas markdown if tabulate exists; fall back to csv-like plain table.
    try:
        return view.to_markdown(index=True, floatfmt=float_fmt)
    except Exception:
        return "```\n" + view.to_string() + "\n```"


def make_interpretive_flags(summary: pd.DataFrame, diag: dict, top_n: int) -> list[str]:
    flags: list[str] = []
    def get(row: str, col: str) -> float | None:
        try:
            val = summary.loc[row, col]
            return float(val) if pd.notna(val) else None
        except Exception:
            return None

    top_col = f"top{top_n}_mean"
    checks = [
        ("max_utci_c", ">", "Top hotspots have higher peak UTCI than the grid average."),
        ("max_wbgt_proxy_c", ">", "Top hotspots have higher peak WBGT proxy than the grid average."),
        ("hazard_score", ">", "Top hotspots have higher hazard score than the grid average."),
        ("gvi_percent", "<", "Top hotspots have lower greenery proxy than the grid average."),
        ("shade_fraction", "<", "Top hotspots have lower shade fraction than the grid average."),
        ("svf", ">", "Top hotspots have higher SVF / sky exposure than the grid average."),
        ("road_fraction", ">", "Top hotspots have higher road fraction than the grid average."),
        ("tree_canopy_fraction", "<", "Top hotspots have lower tree canopy fraction than the grid average."),
        ("ndvi_mean", "<", "Top hotspots have lower NDVI than the grid average."),
    ]
    for row, op, msg in checks:
        all_m = get(row, "all_mean")
        top_m = get(row, top_col)
        if all_m is None or top_m is None:
            continue
        ok = (top_m > all_m) if op == ">" else (top_m < all_m)
        mark = "OK" if ok else "CHECK"
        flags.append(f"- **{mark}**: {msg} (`all_mean={all_m:.3f}`, `top{top_n}_mean={top_m:.3f}`).")

    svf98 = diag.get("svf_ge_0_98_share")
    if isinstance(svf98, float):
        if svf98 >= 0.4:
            flags.append(f"- **WARN**: SVF saturation is high (`svf>=0.98` share {svf98:.1%}); consider revising SVF proxy or replacing with UMEP-derived SVF.")
        elif svf98 >= 0.2:
            flags.append(f"- **CHECK**: SVF upper-end saturation is moderate (`svf>=0.98` share {svf98:.1%}).")
        else:
            flags.append(f"- **OK**: SVF upper-end saturation is not severe (`svf>=0.98` share {svf98:.1%}).")
    imp_old = diag.get("impervious_old_mean")
    imp_new = diag.get("impervious_mean")
    if isinstance(imp_old, float) and isinstance(imp_new, float):
        flags.append(f"- **OK**: Impervious fraction was revised from old beta mean `{imp_old:.3f}` to `{imp_new:.3f}`; keep the revised file as the beta-final grid if ranking remains stable.")
    return flags


def write_qa_report(
    out_path: Path,
    ranking: pd.DataFrame,
    summary: pd.DataFrame,
    diag: dict,
    event_summary: dict,
    hazard_metrics: dict,
    top_n: int,
    paths: dict[str, Path],
) -> None:
    lines: list[str] = []
    lines.append("# OpenHeat-ToaPayoh v0.7-beta.1 Hotspot QA Report\n")
    lines.append("This report is generated from the v0.7-beta real-grid forecast outputs. It is a QA and interpretation aid, not a validation report.\n")
    lines.append("## Input files\n")
    for k, p in paths.items():
        lines.append(f"- `{k}`: `{p}`")
    lines.append("\n## Key diagnostics\n")
    lines.append("```json\n" + json.dumps(diag, indent=2, ensure_ascii=False) + "\n```\n")
    lines.append("\n## Event-window summary\n")
    lines.append("```json\n" + json.dumps(event_summary, indent=2, ensure_ascii=False) + "\n```\n")
    lines.append("\n## Hazard vs risk metrics\n")
    lines.append("```json\n" + json.dumps(hazard_metrics, indent=2, ensure_ascii=False) + "\n```\n")
    lines.append(f"\n## Top {top_n} vs all cells\n")
    lines.append(safe_markdown_table(summary, max_rows=200))
    lines.append("\n## Interpretive flags\n")
    flags = make_interpretive_flags(summary, diag, top_n)
    lines.extend(flags if flags else ["_No automated flags generated._"])
    lines.append(f"\n## Top {top_n} ranking table\n")
    cols = _safe_keep_cols(ranking, TOP_TABLE_COLS)
    lines.append(safe_markdown_table(ranking[cols].nsmallest(top_n, "rank"), max_rows=top_n))
    lines.append("\n## Recommended interpretation\n")
    lines.append(
        "- Treat this output as a **screening-level hotspot prioritisation** based on forecast meteorology and real 100 m grid features.\n"
        "- Use `hazard_score` to discuss physically hotter cells; use `risk_priority_score` only with caution until v0.7.1 adds stronger elderly/exposure proxies.\n"
        "- If top hotspots are high-SVF, low-shade, low-greenery and road-dominated, the ranking is directionally plausible.\n"
        "- If top hotspots fall in water bodies or dense green interiors during map QA, revisit water/greenery/shade feature scaling.\n"
        "- Replace proxy SVF/shade with UMEP-derived values in v0.8/v0.9.\n"
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def maybe_write_geojson(grid_geojson: Path, ranking: pd.DataFrame, out_geojson: Path) -> None:
    if not grid_geojson.exists():
        print(f"[SKIP] grid GeoJSON not found: {grid_geojson}")
        return
    try:
        import geopandas as gpd
    except Exception as exc:
        print(f"[SKIP] geopandas unavailable, cannot write GeoJSON: {exc}")
        return
    grid = gpd.read_file(grid_geojson)
    if "cell_id" not in grid.columns:
        print(f"[SKIP] grid GeoJSON lacks cell_id: {grid_geojson}")
        return
    out = grid[["cell_id", "geometry"]].merge(ranking, on="cell_id", how="right")
    out = gpd.GeoDataFrame(out, geometry="geometry", crs=grid.crs)
    out.to_file(out_geojson, driver="GeoJSON")
    print(f"[OK] wrote GeoJSON: {out_geojson}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalise v0.7-beta forecast outputs with explanatory feature merge and QA report.")
    parser.add_argument("--forecast-dir", default="outputs/v07_beta_final_forecast_live")
    parser.add_argument("--grid-csv", default="data/grid/toa_payoh_grid_v07_features_beta_final.csv")
    parser.add_argument("--grid-geojson", default="data/grid/toa_payoh_grid_v07_features.geojson")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--ranking-name", default="v06_live_hotspot_ranking.csv")
    parser.add_argument("--event-name", default="v06_live_event_windows.csv")
    args = parser.parse_args()

    forecast_dir = Path(args.forecast_dir)
    ranking_path = forecast_dir / args.ranking_name
    event_path = forecast_dir / args.event_name
    grid_csv = Path(args.grid_csv)
    grid_geojson = Path(args.grid_geojson)

    ranking = _read_csv(ranking_path, "hotspot ranking")
    grid = _read_csv(grid_csv, "grid feature CSV")
    merged = merge_explanatory_features(ranking, grid)

    out_ranking = forecast_dir / "v07_beta1_hotspot_ranking_with_grid_features.csv"
    out_summary = forecast_dir / "v07_beta1_top_vs_all_summary.csv"
    out_hazard_risk = forecast_dir / "v07_beta1_hazard_vs_risk_comparison.csv"
    out_diag = forecast_dir / "v07_beta1_feature_diagnostics.json"
    out_report = forecast_dir / "v07_beta1_hotspot_QA_report.md"
    out_geojson = forecast_dir / "v07_beta1_hotspot_ranking_with_grid_features.geojson"

    merged.to_csv(out_ranking, index=False)
    summary = build_top_vs_all_summary(merged, top_n=args.top_n)
    summary.to_csv(out_summary)
    hazard_risk_table, hazard_metrics = build_hazard_risk_comparison(merged, top_n=args.top_n)
    hazard_risk_table.to_csv(out_hazard_risk, index=False)
    diag = feature_diagnostics(merged)
    event_summary = event_window_summary(event_path)
    out_diag.write_text(json.dumps({"feature_diagnostics": diag, "event_summary": event_summary, "hazard_risk_metrics": hazard_metrics}, indent=2, ensure_ascii=False), encoding="utf-8")

    write_qa_report(
        out_report,
        merged,
        summary,
        diag,
        event_summary,
        hazard_metrics,
        top_n=args.top_n,
        paths={"ranking": ranking_path, "grid_csv": grid_csv, "event_windows": event_path, "grid_geojson": grid_geojson},
    )
    maybe_write_geojson(grid_geojson, merged, out_geojson)

    cols = _safe_keep_cols(merged, TOP_TABLE_COLS)
    print("[OK] wrote:")
    for p in [out_ranking, out_summary, out_hazard_risk, out_diag, out_report, out_geojson]:
        if p.exists():
            print(" -", p)
    print("\nTop rows:")
    print(merged[cols].nsmallest(args.top_n, "rank").to_string(index=False))


if __name__ == "__main__":
    main()
