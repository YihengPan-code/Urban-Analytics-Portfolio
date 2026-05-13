from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from v11_lib import (
    read_json, expand_globs, read_many, ensure_dir, first_present, parse_timestamp_series,
    safe_numeric, normalize_station_id, infer_station_from_file, fallback_wbgt_proxy,
    add_time_features, add_weather_lags, write_md, df_to_md_table
)

NEA_TS_CAND = ["timestamp", "datetime", "date_time", "time", "local_time", "obs_time", "valid_time"]
NEA_ST_CAND = ["station_id", "station", "station_code", "station_name", "id", "name"]
WBGT_CAND = ["official_wbgt_c", "wbgt_c", "wbgt", "WBGT_C", "WBGT", "wet_bulb_globe_temperature"]

W_TS_CAND = NEA_TS_CAND
W_ST_CAND = NEA_ST_CAND
TEMP_CAND = ["air_temperature_c", "temperature_2m_c", "temperature_c", "temp_c", "air_temperature", "temperature_2m", "temperature"]
RH_CAND = ["relative_humidity_pct", "relative_humidity_2m", "relative_humidity", "rh", "humidity", "rh_pct"]
WIND_CAND = ["wind_speed_m_s", "wind_speed_10m", "wind_speed", "wind_m_s", "windspeed"]
SHORTWAVE_CAND = ["shortwave_w_m2", "shortwave_radiation", "global_tilted_irradiance", "kdown", "kdown_w_m2", "ghi", "swdown"]
CLOUD_CAND = ["cloud_cover_pct", "cloud_cover", "fcld", "cloudiness"]
RAIN_CAND = ["precipitation_mm", "precipitation", "rain_mm", "rainfall"]
PROXY_CAND = ["raw_proxy_wbgt_c", "proxy_wbgt_c", "wbgt_proxy_c", "forecast_wbgt_c", "predicted_wbgt_c"]


def normalize_nea(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    colmap = cfg.get("column_overrides", {}).get("nea", {})
    ts_col = first_present(df, NEA_TS_CAND, colmap.get("timestamp"))
    wbgt_col = first_present(df, WBGT_CAND, colmap.get("official_wbgt_c"))
    st_col = first_present(df, NEA_ST_CAND, colmap.get("station_id"))
    if ts_col is None or wbgt_col is None:
        raise ValueError(f"Could not infer NEA timestamp/WBGT columns. Columns={list(df.columns)}")
    out = pd.DataFrame()
    out["timestamp"] = parse_timestamp_series(df[ts_col], cfg["archive"].get("timezone", "Asia/Singapore"), cfg["archive"].get("timestamp_round", "15min"))
    if st_col:
        out["station_id"] = normalize_station_id(df[st_col])
    else:
        out["station_id"] = infer_station_from_file(df["_source_file"]) if "_source_file" in df.columns else np.nan
    out["official_wbgt_c"] = safe_numeric(df, wbgt_col)
    out["_nea_source_file"] = df.get("_source_file", "")
    # Preserve raw proxy if it lives in NEA archive.
    proxy_col = first_present(df, PROXY_CAND, colmap.get("raw_proxy_wbgt_c"))
    if proxy_col:
        out["raw_proxy_wbgt_c"] = safe_numeric(df, proxy_col)
    return out.dropna(subset=["timestamp", "official_wbgt_c"])


def normalize_weather(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    colmap = cfg.get("column_overrides", {}).get("weather", {})
    ts_col = first_present(df, W_TS_CAND, colmap.get("timestamp"))
    if ts_col is None:
        raise ValueError(f"Could not infer weather timestamp column. Columns={list(df.columns)}")
    out = pd.DataFrame()
    out["timestamp"] = parse_timestamp_series(df[ts_col], cfg["archive"].get("timezone", "Asia/Singapore"), cfg["archive"].get("timestamp_round", "15min"))
    st_col = first_present(df, W_ST_CAND, colmap.get("station_id"))
    if st_col:
        out["station_id"] = normalize_station_id(df[st_col])
    elif cfg["archive"].get("weather_is_global", True):
        out["station_id"] = "GLOBAL"
    else:
        out["station_id"] = infer_station_from_file(df["_source_file"]) if "_source_file" in df.columns else np.nan
    for out_col, candidates, key in [
        ("air_temperature_c", TEMP_CAND, "air_temperature_c"),
        ("relative_humidity_pct", RH_CAND, "relative_humidity_pct"),
        ("wind_speed_m_s", WIND_CAND, "wind_speed_m_s"),
        ("shortwave_w_m2", SHORTWAVE_CAND, "shortwave_w_m2"),
        ("cloud_cover_pct", CLOUD_CAND, "cloud_cover_pct"),
        ("precipitation_mm", RAIN_CAND, "precipitation_mm"),
        ("raw_proxy_wbgt_c", PROXY_CAND, "raw_proxy_wbgt_c"),
    ]:
        c = first_present(df, candidates, colmap.get(key))
        if c:
            out[out_col] = safe_numeric(df, c)
    out["_weather_source_file"] = df.get("_source_file", "")
    return out.dropna(subset=["timestamp"])


def merge_weather(nea: pd.DataFrame, weather: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    tol = pd.Timedelta(minutes=float(cfg["archive"].get("merge_tolerance_minutes", 20)))
    nea = nea.sort_values("timestamp").copy()
    weather = weather.sort_values("timestamp").copy()
    weather_global = weather[weather["station_id"].fillna("GLOBAL").astype(str) == "GLOBAL"].copy()
    weather_station = weather[~weather.index.isin(weather_global.index)].copy()

    pieces = []
    for st, g in nea.groupby("station_id", dropna=False):
        g = g.sort_values("timestamp")
        w = weather_station[weather_station["station_id"] == st].sort_values("timestamp") if len(weather_station) else pd.DataFrame()
        if w.empty and not weather_global.empty:
            w = weather_global.sort_values("timestamp")
            # remove GLOBAL station_id from right to avoid duplicate naming confusion
            w = w.drop(columns=["station_id"], errors="ignore")
            merged = pd.merge_asof(g, w, on="timestamp", direction="nearest", tolerance=tol)
        elif not w.empty:
            merged = pd.merge_asof(g, w, on="timestamp", by="station_id", direction="nearest", tolerance=tol)
        else:
            merged = g.copy()
        pieces.append(merged)
    return pd.concat(pieces, ignore_index=True, sort=False) if pieces else pd.DataFrame()


def attach_station_and_grid_features(pairs: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    out = pairs.copy()
    station_csv = Path(cfg["paths"].get("station_to_cell_csv", ""))
    if station_csv.exists():
        st = pd.read_csv(station_csv)
        if "station_id" in st.columns:
            st["station_id"] = normalize_station_id(st["station_id"])
            out = out.merge(st, on="station_id", how="left", suffixes=("", "_station"))
    # Merge v10 overhead/morphology features by cell_id if present.
    for key in ["v10_umep_features_csv", "overhead_sensitivity_grid_csv"]:
        p = Path(cfg["paths"].get(key, ""))
        if p.exists() and "cell_id" in out.columns:
            feat = pd.read_csv(p)
            if "cell_id" in feat.columns:
                keep = [c for c in feat.columns if c == "cell_id" or c not in out.columns]
                out = out.merge(feat[keep], on="cell_id", how="left")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v11/v11_alpha_archive_config.example.json")
    args = ap.parse_args()
    cfg = read_json(args.config)
    out_dir = ensure_dir(cfg["paths"].get("output_dir", "outputs/v11_alpha_archive"))
    calib_dir = ensure_dir(cfg["paths"].get("calibration_dir", "data/calibration/v11"))

    nea_paths = expand_globs(cfg["archive"].get("nea_wbgt_globs", []))
    weather_paths = expand_globs(cfg["archive"].get("weather_globs", []))
    nea_raw = read_many(nea_paths, "nea_wbgt")
    weather_raw = read_many(weather_paths, "weather")
    if nea_raw.empty:
        raise SystemExit("[ERROR] No NEA/WBGT archive files found. Edit config archive.nea_wbgt_globs.")
    nea = normalize_nea(nea_raw, cfg)
    if weather_raw.empty:
        print("[WARN] No weather archive files found; pairs will contain official WBGT only.")
        pairs = nea.copy()
    else:
        weather = normalize_weather(weather_raw, cfg)
        pairs = merge_weather(nea, weather, cfg)

    # Prefer project proxy if present; otherwise compute fallback if temp/rh are available.
    if "raw_proxy_wbgt_c" not in pairs.columns or pairs["raw_proxy_wbgt_c"].isna().all():
        if {"air_temperature_c", "relative_humidity_pct"}.issubset(pairs.columns):
            pairs["raw_proxy_wbgt_c"] = fallback_wbgt_proxy(pairs["air_temperature_c"], pairs["relative_humidity_pct"])
            pairs["raw_proxy_source"] = "fallback_shaded_wbgt_formula_from_temp_rh"
        else:
            pairs["raw_proxy_source"] = "missing"
    else:
        pairs["raw_proxy_source"] = "archive_or_forecast_proxy"

    pairs = add_time_features(pairs)
    pairs = add_weather_lags(pairs)
    pairs = attach_station_and_grid_features(pairs, cfg)

    # Stable sort and save.
    pairs = pairs.sort_values(["station_id", "timestamp"]).reset_index(drop=True)
    pairs_path = Path(cfg["paths"].get("paired_dataset_csv", calib_dir / "v11_station_weather_pairs.csv"))
    ensure_dir(pairs_path.parent)
    # Save timestamps as strings to avoid timezone parser surprises.
    out_pairs = pairs.copy()
    out_pairs["timestamp"] = out_pairs["timestamp"].astype(str)
    out_pairs.to_csv(pairs_path, index=False)

    # Summary report.
    event_thresholds = cfg.get("qa", {}).get("event_thresholds_c", [29, 31, 33])
    station_summary = pairs.groupby("station_id", dropna=False).agg(
        n_rows=("official_wbgt_c", "size"),
        n_valid_wbgt=("official_wbgt_c", lambda x: int(x.notna().sum())),
        start=("timestamp", "min"),
        end=("timestamp", "max"),
        mean_wbgt=("official_wbgt_c", "mean"),
        max_wbgt=("official_wbgt_c", "max"),
    ).reset_index()
    for thr in event_thresholds:
        station_summary[f"n_wbgt_ge_{str(thr).replace('.', '_')}"] = pairs.groupby("station_id")["official_wbgt_c"].apply(lambda x, t=thr: int((x >= t).sum())).values
    station_summary_path = out_dir / "v11_station_summary.csv"
    station_summary.to_csv(station_summary_path, index=False)

    report = [
        "# OpenHeat v1.1-alpha paired archive dataset report",
        "",
        f"Rows in paired dataset: **{len(pairs):,}**",
        f"Stations: **{pairs['station_id'].nunique(dropna=True)}**",
        f"Paired dataset: `{pairs_path}`",
        "",
        "## Station summary",
        df_to_md_table(station_summary, max_rows=30),
        "",
        "## Column coverage",
    ]
    coverage = pd.DataFrame({"column": pairs.columns, "non_null": [int(pairs[c].notna().sum()) for c in pairs.columns], "non_null_pct": [float(pairs[c].notna().mean()) for c in pairs.columns]})
    coverage_path = out_dir / "v11_pair_column_coverage.csv"
    coverage.to_csv(coverage_path, index=False)
    report += [df_to_md_table(coverage.sort_values("non_null_pct"), max_rows=40), ""]
    if pairs.get("raw_proxy_source", pd.Series()).astype(str).eq("fallback_shaded_wbgt_formula_from_temp_rh").any():
        report += [
            "## Warning: fallback proxy used",
            "`raw_proxy_wbgt_c` was not found in the archive, so the script computed a simple shaded WBGT-like fallback from temperature and humidity. For final v1.1-beta calibration, prefer your v0.9/v10 project WBGT proxy if available.",
            "",
        ]
    report_path = out_dir / "v11_paired_dataset_report.md"
    write_md(report_path, "\n".join(report))
    print(f"[OK] paired dataset: {pairs_path}")
    print(f"[OK] station summary: {station_summary_path}")
    print(f"[OK] report: {report_path}")


if __name__ == "__main__":
    main()
