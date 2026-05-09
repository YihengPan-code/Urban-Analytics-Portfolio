from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from v09_common import (
    load_config, ensure_dir, to_sgt_series, robust_numeric, haversine_m,
    compute_wbgt_proxy_weather_only, add_wbgt_categories, metrics
)

MORPH_COLS = [
    "svf", "shade_fraction", "tree_canopy_fraction", "ndvi_mean", "gvi_percent",
    "road_fraction", "building_density", "park_distance_m", "water_distance_m",
    "land_use_hint", "vulnerability_score_v071", "outdoor_exposure_score_v071"
]


def load_wbgt_archive(archive_path: Path, variable: str) -> pd.DataFrame:
    df = pd.read_csv(archive_path)
    x = df[df["variable"].eq(variable)].copy()
    if x.empty:
        raise ValueError(f"No {variable} rows found in {archive_path}")
    x["timestamp_sgt"] = to_sgt_series(x["timestamp"])
    x["official_wbgt_c"] = robust_numeric(x["value"])
    x = x.dropna(subset=["timestamp_sgt", "station_id", "official_wbgt_c", "station_lat", "station_lon"])
    keep = [
        "timestamp_sgt", "station_id", "station_name", "station_town_center", "station_lat", "station_lon",
        "official_wbgt_c", "heat_stress_category", "archive_run_utc", "record_updated_timestamp", "fetch_timestamp_utc"
    ]
    keep = [c for c in keep if c in x.columns]
    return x[keep].sort_values(["station_id", "timestamp_sgt"]).reset_index(drop=True)


def interpolate_forecast_to_wbgt_times(wbgt: pd.DataFrame, forecast: pd.DataFrame) -> pd.DataFrame:
    f = forecast.copy()
    f["time_sgt"] = to_sgt_series(f["time_sgt"])
    numeric_cols = [
        c for c in f.columns
        if c not in {"station_id", "station_name", "station_lat", "station_lon", "time_sgt", "openmeteo_endpoint", "openmeteo_url", "openmeteo_api_used"}
        and pd.api.types.is_numeric_dtype(f[c])
    ]
    out_frames = []
    for sid, wg in wbgt.groupby("station_id"):
        fg = f[f["station_id"].eq(sid)].copy()
        if fg.empty:
            tmp = wg.copy()
            for c in numeric_cols:
                tmp[c] = np.nan
            tmp["forecast_pairing_status"] = "no_forecast_for_station"
            out_frames.append(tmp)
            continue
        fg = fg.drop_duplicates("time_sgt").set_index("time_sgt").sort_index()
        target_index = pd.DatetimeIndex(wg["timestamp_sgt"])
        union_index = fg.index.union(target_index).sort_values()
        interp = fg[numeric_cols].reindex(union_index).interpolate(method="time", limit_direction="both").reindex(target_index)
        tmp = wg.copy().reset_index(drop=True)
        for c in numeric_cols:
            tmp[c] = interp[c].to_numpy()
        tmp["forecast_pairing_status"] = "ok"
        # metadata from forecast
        for meta in ["openmeteo_endpoint", "openmeteo_api_used"]:
            if meta in fg.columns:
                tmp[meta] = fg[meta].dropna().iloc[0] if fg[meta].notna().any() else pd.NA
        out_frames.append(tmp)
    return pd.concat(out_frames, ignore_index=True).sort_values(["station_id", "timestamp_sgt"])


def attach_nearest_grid_morphology(pairs: pd.DataFrame, grid_path: Path, cfg: dict) -> pd.DataFrame:
    out = pairs.copy()
    if not grid_path.exists():
        out["nearest_grid_cell"] = pd.NA
        out["nearest_grid_distance_m"] = np.nan
        out["morphology_representativeness"] = "no_grid_file"
        return out
    grid = pd.read_csv(grid_path)
    if not {"cell_id", "lat", "lon"}.issubset(grid.columns):
        out["nearest_grid_cell"] = pd.NA
        out["nearest_grid_distance_m"] = np.nan
        out["morphology_representativeness"] = "grid_missing_lat_lon"
        return out
    local_m = cfg.get("pairing", {}).get("morphology_local_m", 1000)
    nearby_m = cfg.get("pairing", {}).get("morphology_nearby_m", 3000)

    # compute nearest only for unique stations
    stations = out[["station_id", "station_lat", "station_lon"]].drop_duplicates("station_id").copy()
    rows = []
    glat = grid["lat"].astype(float).to_numpy()
    glon = grid["lon"].astype(float).to_numpy()
    for _, st in stations.iterrows():
        d = haversine_m(float(st["station_lat"]), float(st["station_lon"]), glat, glon)
        idx = int(np.nanargmin(d))
        dist = float(d[idx])
        g = grid.iloc[idx]
        rep = "local_grid_proxy" if dist <= local_m else ("nearby_grid_proxy" if dist <= nearby_m else "regional_distance_not_representative")
        rec = {
            "station_id": st["station_id"],
            "nearest_grid_cell": g["cell_id"],
            "nearest_grid_distance_m": dist,
            "morphology_representativeness": rep,
        }
        for c in MORPH_COLS:
            if c in grid.columns:
                rec[f"station_nearest_grid_{c}"] = g[c]
        rows.append(rec)
    nearest = pd.DataFrame(rows)
    out = out.merge(nearest, on="station_id", how="left")
    return out


def main():
    parser = argparse.ArgumentParser(description="OpenHeat v0.9-alpha: build official WBGT × historical forecast paired table.")
    parser.add_argument("--config", default="configs/v09_alpha_config.example.json")
    parser.add_argument("--archive", default=None)
    parser.add_argument("--forecast", default="data/calibration/v09_historical_forecast_by_station_hourly.csv")
    parser.add_argument("--grid", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    archive_path = Path(args.archive or cfg["archive_csv"])
    forecast_path = Path(args.forecast)
    grid_path = Path(args.grid or cfg.get("grid_csv", "data/grid/toa_payoh_grid_v08_features_umep_with_veg.csv"))
    out_dir = ensure_dir(cfg.get("calibration_dir", "data/calibration"))
    out_fp = Path(args.out or out_dir / "v09_wbgt_station_pairs.csv")
    outputs_dir = ensure_dir(cfg.get("outputs_dir", "outputs/v09_alpha_calibration"))

    if not forecast_path.exists():
        raise FileNotFoundError(f"Historical forecast CSV not found: {forecast_path}. Run v09_fetch_historical_forecast_for_archive.py first.")

    wbgt = load_wbgt_archive(archive_path, cfg.get("pairing", {}).get("wbgt_variable_name", "official_wbgt_c"))
    forecast = pd.read_csv(forecast_path)

    pairs = interpolate_forecast_to_wbgt_times(wbgt, forecast)
    pairs = compute_wbgt_proxy_weather_only(pairs)
    pairs = add_wbgt_categories(pairs, "wbgt_proxy_weather_only_c", "wbgt_proxy_weather_only_category")
    pairs["wbgt_residual_weather_only_c"] = pairs["official_wbgt_c"] - pairs["wbgt_proxy_weather_only_c"]
    pairs["wbgt_proxy_physics"] = pairs["wbgt_proxy_weather_only_c"]
    pairs["wbgt_residual_physics"] = pairs["official_wbgt_c"] - pairs["wbgt_proxy_physics"]

    pairs = attach_nearest_grid_morphology(pairs, grid_path, cfg)

    # useful time features
    t = to_sgt_series(pairs["timestamp_sgt"])
    pairs["hour_sgt"] = t.dt.hour + t.dt.minute / 60.0
    pairs["hour_sin"] = np.sin(2 * np.pi * pairs["hour_sgt"] / 24.0)
    pairs["hour_cos"] = np.cos(2 * np.pi * pairs["hour_sgt"] / 24.0)
    pairs["date_sgt"] = t.dt.date.astype(str)

    out_fp.parent.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(out_fp, index=False)

    metric = metrics(pairs["official_wbgt_c"], pairs["wbgt_proxy_physics"])
    metric_df = pd.DataFrame([metric])
    metric_fp = outputs_dir / "v09_raw_proxy_baseline_metrics.csv"
    metric_df.to_csv(metric_fp, index=False)

    by_station = []
    for (sid, sname), g in pairs.groupby(["station_id", "station_name"], dropna=False):
        m = metrics(g["official_wbgt_c"], g["wbgt_proxy_physics"])
        m.update({
            "station_id": sid,
            "station_name": sname,
            "n": len(g),
            "official_wbgt_mean": g["official_wbgt_c"].mean(),
            "official_wbgt_max": g["official_wbgt_c"].max(),
            "moderate_obs": int(g["heat_stress_category"].eq("Moderate").sum()) if "heat_stress_category" in g.columns else None,
            "high_obs": int(g["heat_stress_category"].eq("High").sum()) if "heat_stress_category" in g.columns else None,
            "nearest_grid_distance_m": g["nearest_grid_distance_m"].iloc[0] if "nearest_grid_distance_m" in g.columns else np.nan,
            "morphology_representativeness": g["morphology_representativeness"].iloc[0] if "morphology_representativeness" in g.columns else None,
        })
        by_station.append(m)
    station_metrics = pd.DataFrame(by_station).sort_values("mae")
    station_metrics_fp = outputs_dir / "v09_raw_proxy_metrics_by_station.csv"
    station_metrics.to_csv(station_metrics_fp, index=False)

    report_lines = []
    report_lines.append("# OpenHeat v0.9-alpha WBGT station-pairing QA report")
    report_lines.append("")
    report_lines.append(f"Pairs CSV: `{out_fp}`")
    report_lines.append(f"Rows: **{len(pairs)}**")
    report_lines.append(f"Stations: **{pairs['station_id'].nunique()}**")
    report_lines.append(f"Dates: **{pairs['date_sgt'].min()} → {pairs['date_sgt'].max()}**")
    report_lines.append("")
    report_lines.append("## Raw physics WBGT proxy baseline")
    report_lines.append(metric_df.to_string(index=False))
    report_lines.append("")
    report_lines.append("## Morphology representativeness")
    if "morphology_representativeness" in pairs.columns:
        report_lines.append(pairs[["station_id","morphology_representativeness"]].drop_duplicates()["morphology_representativeness"].value_counts(dropna=False).to_string())
    report_lines.append("")
    report_lines.append("## Best/worst station metrics preview")
    preview_cols = ["station_id","station_name","n","mae","rmse","bias_pred_minus_obs","official_wbgt_max","moderate_obs","high_obs","nearest_grid_distance_m","morphology_representativeness"]
    preview_cols = [c for c in preview_cols if c in station_metrics.columns]
    report_lines.append(station_metrics[preview_cols].head(10).to_string(index=False))
    report_lines.append("")
    report_lines.append("## Interpretation notes")
    report_lines.append("- This paired dataset is a v0.9-alpha pilot calibration table, not a final ML training set.")
    report_lines.append("- `wbgt_proxy_physics` is a screening-level weather-only WBGT proxy; official WBGT residuals are suitable for baseline calibration diagnostics.")
    report_lines.append("- Station morphology joined from the Toa Payoh v0.8 grid is only meaningful for nearby stations; distant stations are flagged as `regional_distance_not_representative`.")

    report_fp = outputs_dir / "v09_wbgt_pairing_QA_report.md"
    report_fp.write_text("\n".join(report_lines), encoding="utf-8")

    print("[OK] WBGT station pairs built")
    print("pairs:", out_fp)
    print("metrics:", metric_fp)
    print("station_metrics:", station_metrics_fp)
    print("report:", report_fp)


if __name__ == "__main__":
    main()
