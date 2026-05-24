#!/usr/bin/env python
"""OpenHeat v1.1 / v11 long-term archive collector.

Purpose
-------
Collect one archive snapshot for long-term calibration / ML use:
- NEA/data.gov.sg WBGT + station weather readings, in long + normalized wide formats.
- Open-Meteo forecast snapshots for AOI and optional NEA WBGT station locations.
- Lightweight operational station-weather pairing table for v1.1 alpha/beta/gamma.
- QA report for each run and cumulative archive health.

Design notes
------------
This script intentionally avoids writing giant all-grid hourly forecast files.
The archive should be compact enough for long-term use and ML pairing.

Outputs are append-only CSVs with de-duplication keys. Raw JSON snapshots are
optionally retained for schema debugging.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    from backports.zoneinfo import ZoneInfo  # type: ignore


# -----------------------------------------------------------------------------
# Basic IO
# -----------------------------------------------------------------------------


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def safe_run_id(dt: datetime, prefix: str = "v11") -> str:
    return f"{prefix}_{dt.strftime('%Y%m%d_%H%M%S')}Z"


def parse_dt_any(x: Any) -> pd.Timestamp:
    if pd.isna(x):
        return pd.NaT
    return pd.to_datetime(x, errors="coerce")


def as_sgt(ts: pd.Series | pd.DatetimeIndex, tz_name: str = "Asia/Singapore"):
    out = pd.to_datetime(ts, errors="coerce")
    # If tz-naive, localize as SGT; if tz-aware, convert to SGT.
    try:
        if getattr(out.dt, "tz", None) is None:
            out = out.dt.tz_localize(tz_name)
        else:
            out = out.dt.tz_convert(tz_name)
    except AttributeError:
        # DatetimeIndex path.
        if out.tz is None:
            out = out.tz_localize(tz_name)
        else:
            out = out.tz_convert(tz_name)
    return out


def append_csv_dedup(path: Path, new_df: pd.DataFrame, keys: List[str]) -> pd.DataFrame:
    path.parent.mkdir(parents=True, exist_ok=True)
    if new_df is None or new_df.empty:
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame()
    new_df = new_df.copy()
    if path.exists():
        try:
            old = pd.read_csv(path)
            combined = pd.concat([old, new_df], ignore_index=True, sort=False)
        except Exception:
            combined = new_df
    else:
        combined = new_df
    valid_keys = [k for k in keys if k in combined.columns]
    if valid_keys:
        combined = combined.drop_duplicates(valid_keys, keep="last")
    combined.to_csv(path, index=False)
    return combined


def cleanup_old_raw_json(raw_json_dir: str | Path, keep_days: int = 14) -> int:
    """Delete dated raw-json folders older than keep_days.

    The collector writes raw JSON as raw_json/YYYYMMDD/<run_id>/*.json.
    Keeping this forever creates tens of thousands of small files. This function
    is intentionally conservative: it only deletes directories whose name is an
    8-digit date and is older than the cutoff.
    """
    root = Path(raw_json_dir)
    if keep_days is None or int(keep_days) < 0 or not root.exists():
        return 0
    cutoff_name = (utc_now() - timedelta(days=int(keep_days))).strftime("%Y%m%d")
    deleted = 0
    for d in root.iterdir():
        if d.is_dir() and len(d.name) == 8 and d.name.isdigit() and d.name < cutoff_name:
            shutil.rmtree(d, ignore_errors=True)
            deleted += 1
    return deleted


# -----------------------------------------------------------------------------
# HTTP
# -----------------------------------------------------------------------------


def request_json(url: str, *, params: Optional[dict] = None, headers: Optional[dict] = None,
                 timeout: int = 25, retries: int = 3, sleep_s: float = 1.0) -> Tuple[Optional[dict], Optional[str], int]:
    last_err = None
    for i in range(max(1, retries)):
        try:
            r = requests.get(url, params=params or {}, headers=headers or {}, timeout=timeout)
            if r.status_code == 200:
                return r.json(), None, r.status_code
            last_err = f"HTTP {r.status_code}: {r.text[:500]}"
        except Exception as e:
            last_err = repr(e)
        if i < retries - 1:
            time.sleep(sleep_s * (i + 1))
    return None, last_err, -1


# -----------------------------------------------------------------------------
# NEA / data.gov.sg parser
# -----------------------------------------------------------------------------


def get_nested(d: dict, paths: Iterable[Tuple[str, ...]], default=None):
    for path in paths:
        cur: Any = d
        ok = True
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                ok = False
                break
            cur = cur[p]
        if ok:
            return cur
    return default


def station_metadata_map(data: dict) -> Dict[str, dict]:
    stations = data.get("stations") or data.get("station_metadata") or data.get("metadata") or []
    out: Dict[str, dict] = {}
    if isinstance(stations, dict):
        stations = stations.get("stations", [])
    for s in stations or []:
        if not isinstance(s, dict):
            continue
        sid = s.get("id") or s.get("stationId") or s.get("station_id") or s.get("deviceId") or s.get("device_id")
        if not sid:
            continue
        loc = s.get("location") or {}
        out[str(sid)] = {
            "station_id": str(sid),
            "device_id": s.get("deviceId") or s.get("device_id") or sid,
            "station_name": s.get("name") or s.get("stationName") or s.get("station_name") or "",
            "station_town_center": s.get("townCenter") or s.get("town_center") or s.get("area") or "",
            "station_lat": loc.get("latitude") or s.get("latitude") or s.get("lat"),
            "station_lon": loc.get("longitude") or s.get("longitude") or s.get("lon") or s.get("lng"),
        }
    return out


def parse_data_gov_realtime(js: dict, endpoint_cfg: dict, run_id: str, run_dt: datetime) -> pd.DataFrame:
    """Parse data.gov.sg v2 real-time API responses.

    Handles two response shapes:
    A) Direct endpoint shape (e.g. /v2/real-time/api/air-temperature):
         {"data": {"stations": [...],
                   "readings": [{"timestamp": ...,
                                 "data": [{"stationId":..., "value":...}]}],
                   "readingType": ..., "readingUnit": ...}}
    B) Weather wrapper shape (e.g. /v2/real-time/api/weather?api=wbgt):
         {"data": {"records": [{"datetime": ...,
                                "updatedTimestamp": ...,
                                "item": {"type": "observation",
                                         "isStationData": true,
                                         "readings": [
                                            {"station": {"id":..., "name":..., "townCenter":...},
                                             "location": {"latitude":..., "longtitude":...},
                                             "heatStress": "Low",
                                             "wbgt": "26.9"}]}}]}}

    Note: NEA's WBGT wrapper response misspells "longtitude" — the parser accepts both.
    """
    root_data = js.get("data", js)
    meta = station_metadata_map(root_data if isinstance(root_data, dict) else {})
    readings = []
    if isinstance(root_data, dict):
        readings = root_data.get("readings") or root_data.get("items") or root_data.get("records") or []
    if isinstance(readings, dict):
        readings = readings.get("readings", [])
    rows = []
    reading_type = root_data.get("readingType") if isinstance(root_data, dict) else None
    reading_unit = root_data.get("readingUnit") if isinstance(root_data, dict) else None
    api_version = js.get("apiVersion") or js.get("version") or "data.gov.sg-v2"

    for rd in readings or []:
        if not isinstance(rd, dict):
            continue
        # Timestamp may live at different keys depending on response shape.
        ts = (
            rd.get("timestamp")
            or rd.get("updatedTimestamp")
            or rd.get("time")
            or rd.get("datetime")  # weather-wrapper shape
        )
        rec_updated = (
            rd.get("updatedTimestamp")
            or rd.get("recordUpdatedTimestamp")
            or rd.get("timestamp")
            or rd.get("datetime")
        )

        # Find the per-station readings list across both shapes.
        data_items = rd.get("data") or rd.get("readings") or rd.get("items") or []
        if not data_items and isinstance(rd.get("item"), dict):
            # weather-wrapper: readings are under rd["item"]["readings"]
            data_items = rd["item"].get("readings") or rd["item"].get("data") or []
        if isinstance(data_items, dict):
            data_items = data_items.get("data", []) or data_items.get("readings", [])

        for item in data_items or []:
            if not isinstance(item, dict):
                continue

            # Station id may be at item-level or nested under item["station"].
            station_obj = item.get("station") if isinstance(item.get("station"), dict) else None
            sid = (
                item.get("stationId")
                or item.get("station_id")
                or item.get("id")
                or (station_obj.get("id") if station_obj else None)
                or (station_obj.get("stationId") if station_obj else None)
                or (station_obj.get("station_id") if station_obj else None)
            )
            if sid is None:
                continue
            sid = str(sid)

            value = item.get("value")
            if value is None:
                # WBGT wrapper has the value under "wbgt"; other endpoints under their own var name.
                for k in ["reading", "wbgt", "temperature", "humidity", "windSpeed", "rainfall"]:
                    if k in item:
                        value = item[k]
                        break

            sm = meta.get(sid, {})

            # Station name: from top-level meta first, then from nested station_obj (weather wrapper).
            station_name = (
                sm.get("station_name")
                or (station_obj.get("name") if station_obj else None)
                or item.get("stationName")
                or item.get("name")
                or ""
            )
            station_town_center = (
                sm.get("station_town_center")
                or (station_obj.get("townCenter") if station_obj else None)
                or ""
            )

            # Location: in NEA WBGT wrapper, "location" is at item level (NOT under station).
            #           Also accept the legacy place under station_obj["location"] for safety.
            #           NEA's WBGT wrapper misspells "longtitude" — accept both spellings.
            loc_obj = None
            if isinstance(item.get("location"), dict):
                loc_obj = item["location"]
            elif station_obj and isinstance(station_obj.get("location"), dict):
                loc_obj = station_obj["location"]
            station_lat = sm.get("station_lat")
            station_lon = sm.get("station_lon")
            if loc_obj:
                if station_lat is None:
                    station_lat = loc_obj.get("latitude") or loc_obj.get("lat")
                if station_lon is None:
                    station_lon = (
                        loc_obj.get("longitude")
                        or loc_obj.get("longtitude")  # NEA's typo in WBGT endpoint
                        or loc_obj.get("lon")
                        or loc_obj.get("lng")
                    )
            if station_lat is None:
                station_lat = item.get("latitude") or item.get("lat")
            if station_lon is None:
                station_lon = (
                    item.get("longitude")
                    or item.get("longtitude")
                    or item.get("lon")
                    or item.get("lng")
                )

            # Heat-stress category: NEA's WBGT wrapper uses "heatStress" (string like "Low"/"Moderate"/"High").
            hs_cat = (
                item.get("heatStress")  # actual NEA WBGT wrapper field name
                or item.get("heatStressCategory")
                or item.get("heat_stress_category")
                or item.get("heatStressLevel")
                or item.get("category")
                or item.get("level")
            )

            rows.append({
                "archive_run_id": run_id,
                "archive_run_utc": iso(run_dt),
                "archive_source": "data.gov.sg",
                "archive_status": "ok",
                "api_name": endpoint_cfg.get("api_name") or endpoint_cfg.get("name"),
                "variable": endpoint_cfg.get("variable"),
                "value": value,
                "unit": endpoint_cfg.get("unit") or reading_unit,
                "timestamp": ts,
                "record_updated_timestamp": rec_updated,
                "station_id": sid,
                "device_id": sm.get("device_id", item.get("deviceId") or item.get("device_id") or sid),
                "station_name": station_name,
                "station_town_center": station_town_center,
                "station_lat": station_lat,
                "station_lon": station_lon,
                "heat_stress_category": hs_cat,
                "reading_type": reading_type,
                "reading_unit": reading_unit,
                "api_version": api_version,
                "endpoint_url": endpoint_cfg.get("url") + ("?" + "&".join(f"{k}={v}" for k, v in (endpoint_cfg.get("params") or {}).items()) if endpoint_cfg.get("params") else ""),
                "fetch_timestamp_utc": iso(utc_now()),
                "value_missing": value is None or value == "",
                "raw_item_json": json.dumps(item, ensure_ascii=False, default=str)[:2000],
            })
    return pd.DataFrame(rows)


def normalize_nea_tables(nea_long: pd.DataFrame, tz_name: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if nea_long.empty:
        return pd.DataFrame(), pd.DataFrame()
    df = nea_long.copy()
    # Primary timestamp; fall back to record_updated_timestamp when NEA's "latest"
    # response has missing/null datetime at the outer record level (a known edge
    # case where the most recent observation has updatedTimestamp set but the
    # finalised observation `datetime` is not yet populated).
    ts_primary = as_sgt(df["timestamp"], tz_name)
    if "record_updated_timestamp" in df.columns:
        ts_fallback = as_sgt(df["record_updated_timestamp"], tz_name)
        ts_combined = ts_primary.where(ts_primary.notna(), ts_fallback)
    else:
        ts_combined = ts_primary
    df["timestamp_sgt"] = ts_combined.astype(str)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_sgt"], errors="coerce").dt.tz_convert("UTC").astype(str)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    keep_cols = [
        "archive_run_id", "archive_run_utc", "timestamp_sgt", "timestamp_utc", "station_id",
        "station_name", "station_lat", "station_lon", "variable", "value", "unit",
        "heat_stress_category", "record_updated_timestamp", "fetch_timestamp_utc"
    ]
    df = df[[c for c in keep_cols if c in df.columns]].copy()

    wbgt = df[df["variable"] == "official_wbgt_c"].copy()
    if not wbgt.empty:
        wbgt = wbgt.rename(columns={"value": "official_wbgt_c"})
        wbgt = wbgt.drop_duplicates(["timestamp_sgt", "station_id"], keep="last")

    weather = df[df["variable"].isin(["air_temperature_c", "relative_humidity_percent", "wind_speed_ms", "wind_direction_deg", "rainfall_mm"])].copy()
    if not weather.empty:
        idx_cols = ["timestamp_sgt", "timestamp_utc", "station_id", "station_name", "station_lat", "station_lon"]
        weather = weather.pivot_table(index=idx_cols, columns="variable", values="value", aggfunc="last").reset_index()
        weather.columns.name = None
        weather = weather.drop_duplicates(["timestamp_sgt", "station_id"], keep="last")
    return wbgt, weather


# -----------------------------------------------------------------------------
# Open-Meteo
# -----------------------------------------------------------------------------


def maybe_should_fetch_openmeteo(cfg: dict, state: dict, run_dt: datetime) -> bool:
    ocfg = cfg.get("openmeteo", {})
    if not ocfg.get("enabled", True):
        return False
    min_minutes = float(ocfg.get("min_minutes_between_runs", 60))
    last = state.get("last_openmeteo_run_utc")
    if not last:
        return True
    try:
        last_dt = pd.to_datetime(last, utc=True).to_pydatetime()
        return (run_dt - last_dt).total_seconds() >= min_minutes * 60
    except Exception:
        return True


def build_openmeteo_locations(cfg: dict, wbgt_df: pd.DataFrame) -> List[dict]:
    ocfg = cfg.get("openmeteo", {})
    locs = list(ocfg.get("locations") or [])
    if ocfg.get("fetch_station_locations_from_wbgt", True) and wbgt_df is not None and not wbgt_df.empty:
        maxn = int(ocfg.get("max_station_locations", 40))
        prefix = ocfg.get("station_location_prefix", "station_")
        st = wbgt_df[["station_id", "station_name", "station_lat", "station_lon"]].drop_duplicates("station_id").copy()
        st["station_lat"] = pd.to_numeric(st["station_lat"], errors="coerce")
        st["station_lon"] = pd.to_numeric(st["station_lon"], errors="coerce")
        st = st.dropna(subset=["station_lat", "station_lon"]).head(maxn)
        existing_ids = {x.get("location_id") for x in locs}
        for _, r in st.iterrows():
            lid = f"{prefix}{r['station_id']}"
            if lid in existing_ids:
                continue
            locs.append({
                "location_id": lid,
                "name": str(r.get("station_name") or r["station_id"]),
                "lat": float(r["station_lat"]),
                "lon": float(r["station_lon"]),
                "role": "nea_station",
                "station_id": str(r["station_id"]),
            })
    # De-duplicate by location_id.
    seen, out = set(), []
    for loc in locs:
        lid = loc.get("location_id")
        if not lid or lid in seen:
            continue
        seen.add(lid)
        out.append(loc)
    return out


def fetch_openmeteo_location(cfg: dict, loc: dict, run_id: str, run_dt: datetime) -> Tuple[pd.DataFrame, Optional[dict], Optional[str]]:
    ocfg = cfg.get("openmeteo", {})
    hourly_vars = ocfg.get("hourly_variables") or []
    params = {
        "latitude": loc["lat"],
        "longitude": loc["lon"],
        "timezone": ocfg.get("timezone", "Asia/Singapore"),
        "forecast_days": ocfg.get("forecast_days", 4),
        "past_days": ocfg.get("past_days", 0),
        "hourly": ",".join(hourly_vars),
    }
    js, err, status = request_json(
        ocfg.get("base_url", "https://api.open-meteo.com/v1/forecast"),
        params=params,
        timeout=int(ocfg.get("timeout_seconds", 35)),
        retries=int(ocfg.get("retries", 3)),
        sleep_s=1.0,
    )
    if err or not js:
        return pd.DataFrame(), js, err or f"HTTP {status}"
    hourly = js.get("hourly") or {}
    times = hourly.get("time") or []
    rows = []
    for i, t in enumerate(times):
        row = {
            "archive_run_id": run_id,
            "forecast_issue_time_utc": iso(run_dt),
            "fetch_timestamp_utc": iso(utc_now()),
            "location_id": loc.get("location_id"),
            "location_name": loc.get("name"),
            "location_role": loc.get("role"),
            "station_id": loc.get("station_id"),
            "latitude": loc.get("lat"),
            "longitude": loc.get("lon"),
            "valid_time_sgt": str(t),
            "timezone": ocfg.get("timezone", "Asia/Singapore"),
            "api_source": "open-meteo_forecast",
            "elevation_m": js.get("elevation"),
            "utc_offset_seconds": js.get("utc_offset_seconds"),
        }
        for var in hourly_vars:
            arr = hourly.get(var)
            if arr is not None and i < len(arr):
                row[var] = arr[i]
        rows.append(row)
    return pd.DataFrame(rows), js, None


# -----------------------------------------------------------------------------
# Pairing and feature engineering
# -----------------------------------------------------------------------------


def stull_wetbulb_c(t_c: pd.Series, rh: pd.Series) -> pd.Series:
    """Stull 2011 wet-bulb approximation in °C.

    Accepts air temperature in C and RH in %.
    """
    t = pd.to_numeric(t_c, errors="coerce")
    r = pd.to_numeric(rh, errors="coerce")
    return (
        t * np.arctan(0.151977 * np.sqrt(r + 8.313659))
        + np.arctan(t + r)
        - np.arctan(r - 1.676331)
        + 0.00391838 * np.power(r, 1.5) * np.arctan(0.023101 * r)
        - 4.686035
    )


def add_proxy_features(pairs: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    if pairs.empty or not cfg.get("proxy_features", {}).get("compute_fallback_wbgt_proxy", True):
        return pairs
    out = pairs.copy()
    tcol = "temperature_2m"
    rhcol = "relative_humidity_2m"
    swcol = "shortwave_radiation"
    windcol = "wind_speed_10m"
    if tcol in out.columns and rhcol in out.columns:
        out["wetbulb_stull_c"] = stull_wetbulb_c(out[tcol], out[rhcol])
        # Very lightweight smoke-test proxy only. It is intentionally labeled so
        # downstream reports do not over-interpret it as the production OpenHeat WBGT model.
        out["raw_proxy_wbgt_fallback_c"] = 0.7 * out["wetbulb_stull_c"] + 0.3 * pd.to_numeric(out[tcol], errors="coerce")
        if swcol in out.columns:
            out["shortwave_3h_mean"] = np.nan
            # Per station/location rolling mean after sort.
            sort_cols = [c for c in ["station_id", "timestamp_sgt"] if c in out.columns]
            if sort_cols:
                out = out.sort_values(sort_cols)
                group = out.groupby("station_id", dropna=False) if "station_id" in out.columns else [(None, out)]
                chunks = []
                for _, g in group:
                    gg = g.copy()
                    gg["shortwave_3h_mean"] = pd.to_numeric(gg[swcol], errors="coerce").rolling(12, min_periods=1).mean().values
                    chunks.append(gg)
                out = pd.concat(chunks, ignore_index=True)
            out["raw_proxy_wbgt_radiative_fallback_c"] = out["raw_proxy_wbgt_fallback_c"] + 0.0020 * pd.to_numeric(out[swcol], errors="coerce").fillna(0)
        if windcol in out.columns and "raw_proxy_wbgt_radiative_fallback_c" in out.columns:
            out["raw_proxy_wbgt_radiative_fallback_c"] = out["raw_proxy_wbgt_radiative_fallback_c"] - 0.10 * pd.to_numeric(out[windcol], errors="coerce").fillna(0)
    return out


def load_feature_tables(cfg: dict) -> pd.DataFrame:
    fcfg = cfg.get("v10_features", {})
    station_map_path = Path(fcfg.get("station_to_cell_csv", ""))
    if not station_map_path.exists():
        return pd.DataFrame()
    stmap = pd.read_csv(station_map_path)
    if "station_id" not in stmap.columns or "cell_id" not in stmap.columns:
        return pd.DataFrame()
    stmap["station_id"] = stmap["station_id"].astype(str)
    stmap["cell_id"] = stmap["cell_id"].astype(str)

    def read_feature(path: str, suffix: str = "") -> pd.DataFrame:
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        df = pd.read_csv(p)
        if "cell_id" not in df.columns:
            return pd.DataFrame()
        df["cell_id"] = df["cell_id"].astype(str)
        # Avoid geometry-like text bloat and duplicate columns.
        drop_cols = [c for c in df.columns if c.lower() in {"geometry"}]
        df = df.drop(columns=drop_cols, errors="ignore")
        return df

    out = stmap.copy()
    for name, path in [
        ("umep", fcfg.get("umep_features_csv", "")),
        ("overhead", fcfg.get("overhead_features_csv", "")),
        ("morph", fcfg.get("basic_morphology_csv", "")),
    ]:
        feat = read_feature(path)
        if feat.empty:
            continue
        # Prefix duplicate non-key columns only if they collide.
        rename = {}
        for c in feat.columns:
            if c != "cell_id" and c in out.columns:
                rename[c] = f"{name}_{c}"
        feat = feat.rename(columns=rename)
        out = out.merge(feat, on="cell_id", how="left")
    return out


def build_pairs(wbgt: pd.DataFrame, openmeteo: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    pcfg = cfg.get("pairing", {})
    if not pcfg.get("enabled", True) or wbgt.empty or openmeteo.empty:
        return pd.DataFrame()
    tz_name = cfg.get("archive", {}).get("timezone", "Asia/Singapore")
    obs = wbgt.copy()
    obs["timestamp_sgt_dt"] = as_sgt(obs["timestamp_sgt"], tz_name)
    obs["obs_utc_dt"] = obs["timestamp_sgt_dt"].dt.tz_convert("UTC")
    if pcfg.get("valid_time_rounding", "floor_hour") == "nearest_hour":
        obs["valid_time_sgt_hour"] = obs["timestamp_sgt_dt"].dt.round("h")
    else:
        obs["valid_time_sgt_hour"] = obs["timestamp_sgt_dt"].dt.floor("h")

    om = openmeteo.copy()
    om["valid_time_sgt_dt"] = as_sgt(om["valid_time_sgt"], tz_name)
    om["forecast_issue_utc_dt"] = pd.to_datetime(om["forecast_issue_time_utc"], errors="coerce", utc=True)

    # Candidate location mapping: station-specific first, otherwise AOI centroid.
    station_prefix = cfg.get("openmeteo", {}).get("station_location_prefix", "station_")
    obs["preferred_location_id"] = station_prefix + obs["station_id"].astype(str)

    # station-specific candidates
    cand1 = obs.merge(
        om,
        left_on=["preferred_location_id", "valid_time_sgt_hour"],
        right_on=["location_id", "valid_time_sgt_dt"],
        how="left",
        suffixes=("", "_om"),
    )
    cand1["pair_location_source"] = "station_openmeteo"

    # fallback AOI centroid candidates
    aoi_id = None
    for loc in cfg.get("openmeteo", {}).get("locations") or []:
        if loc.get("role") == "aoi_centroid":
            aoi_id = loc.get("location_id")
            break
    if not aoi_id:
        aoi_id = "toa_payoh_center"
    om_aoi = om[om["location_id"].astype(str) == str(aoi_id)].copy()
    cand2 = obs.merge(
        om_aoi,
        left_on="valid_time_sgt_hour",
        right_on="valid_time_sgt_dt",
        how="left",
        suffixes=("", "_om"),
    )
    cand2["pair_location_source"] = "aoi_centroid_openmeteo"

    # Prefer station if it had a match; otherwise AOI.
    combined = pd.concat([cand1, cand2], ignore_index=True, sort=False)
    combined["has_weather_match"] = combined["forecast_issue_utc_dt"].notna()
    max_age_h = float(pcfg.get("max_forecast_issue_age_hours", 72))
    combined["issue_age_hours"] = (combined["obs_utc_dt"] - combined["forecast_issue_utc_dt"]).dt.total_seconds() / 3600
    combined["abs_issue_age_hours"] = combined["issue_age_hours"].abs()

    # Two match semantics are kept separate:
    # - operational_match: weather forecast was already issued before the WBGT observation
    # - posthoc_weather_match: retrospective calibration can use Open-Meteo past_days/hindcast rows
    # This avoids silently throwing away useful retrospective weather while preserving
    # operational evaluation flags for later analysis.
    combined["operational_match"] = (
        combined["has_weather_match"]
        & (combined["issue_age_hours"] >= -0.10)  # allow 6 min clock/API jitter
        & (combined["issue_age_hours"] <= max_age_h)
    )
    combined["posthoc_weather_match"] = combined["has_weather_match"] & (combined["abs_issue_age_hours"] <= max_age_h)
    allow_posthoc = bool(pcfg.get("allow_posthoc_weather_if_no_operational_match", True))
    combined["pair_used_for_calibration"] = combined["posthoc_weather_match"] if allow_posthoc else combined["operational_match"]

    combined["weather_match_mode"] = "no_weather_match"
    combined.loc[combined["has_weather_match"] & ~combined["posthoc_weather_match"], "weather_match_mode"] = "stale_or_too_far"
    combined.loc[combined["posthoc_weather_match"], "weather_match_mode"] = "posthoc_hindcast_or_forecast"
    combined.loc[combined["operational_match"], "weather_match_mode"] = "operational_forecast"

    # Prefer usable calibration pair, then station-specific Open-Meteo, then operational
    # forecast, then closest issue time, then newest issue. This gives a single
    # authoritative pair table for v11-alpha/beta while retaining match-mode columns.
    combined["source_priority"] = combined["pair_location_source"].map({"station_openmeteo": 0, "aoi_centroid_openmeteo": 1}).fillna(9)
    combined = combined.sort_values(
        ["timestamp_sgt", "station_id", "pair_used_for_calibration", "source_priority", "operational_match", "abs_issue_age_hours", "forecast_issue_utc_dt"],
        ascending=[True, True, False, True, False, True, False],
    )
    out = combined.drop_duplicates(["timestamp_sgt", "station_id"], keep="first").copy()

    # Merge station-to-cell and v10 morphology/overhead features.
    if cfg.get("v10_features", {}).get("join_features_to_pairs", True):
        feat = load_feature_tables(cfg)
        if not feat.empty:
            out = out.merge(feat, on="station_id", how="left", suffixes=("", "_v10feature"))

    out = add_proxy_features(out, cfg)

    # Cleanup helper datetime columns to stable strings.
    for c in ["timestamp_sgt_dt", "obs_utc_dt", "valid_time_sgt_hour", "valid_time_sgt_dt", "forecast_issue_utc_dt"]:
        if c in out.columns:
            out[c] = out[c].astype(str)
    return out


# -----------------------------------------------------------------------------
# QA report
# -----------------------------------------------------------------------------


def event_counts(wbgt: pd.DataFrame) -> dict:
    if wbgt.empty or "official_wbgt_c" not in wbgt.columns:
        return {}
    x = pd.to_numeric(wbgt["official_wbgt_c"], errors="coerce")
    return {
        "rows": int(len(wbgt)),
        "stations": int(wbgt["station_id"].nunique()) if "station_id" in wbgt.columns else 0,
        "timestamps": int(wbgt["timestamp_sgt"].nunique()) if "timestamp_sgt" in wbgt.columns else 0,
        "wbgt_ge_29": int((x >= 29).sum()),
        "wbgt_ge_31": int((x >= 31).sum()),
        "wbgt_ge_33": int((x >= 33).sum()),
        "max_wbgt": float(x.max()) if x.notna().any() else math.nan,
        "mean_wbgt": float(x.mean()) if x.notna().any() else math.nan,
    }


def write_qa_report(path: Path, *, run_id: str, cfg: dict, nea_long: pd.DataFrame, wbgt: pd.DataFrame,
                    nea_weather: pd.DataFrame, openmeteo: pd.DataFrame, pairs: pd.DataFrame, errors: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ev = event_counts(wbgt)
    lines = []
    lines.append(f"# OpenHeat v1.1 archive run QA — {run_id}\n")
    lines.append("## Summary\n")
    lines.append(f"- NEA long rows this run / cumulative loaded: **{len(nea_long)}**")
    lines.append(f"- WBGT rows cumulative: **{ev.get('rows', 0)}**")
    lines.append(f"- WBGT stations cumulative: **{ev.get('stations', 0)}**")
    lines.append(f"- WBGT timestamps cumulative: **{ev.get('timestamps', 0)}**")
    lines.append(f"- WBGT ≥29 / ≥31 / ≥33 rows: **{ev.get('wbgt_ge_29', 0)} / {ev.get('wbgt_ge_31', 0)} / {ev.get('wbgt_ge_33', 0)}**")
    lines.append(f"- Max WBGT: **{ev.get('max_wbgt', float('nan')):.2f}°C**" if ev else "- Max WBGT: n/a")
    lines.append(f"- NEA station-weather wide rows: **{len(nea_weather)}**")
    lines.append(f"- Open-Meteo forecast rows cumulative: **{len(openmeteo)}**")
    lines.append(f"- Operational paired rows cumulative: **{len(pairs)}**")

    if errors:
        lines.append("\n## Fetch warnings / errors\n")
        for e in errors:
            lines.append(f"- {e}")

    lines.append("\n## Variable counts in NEA long table\n")
    if not nea_long.empty and "variable" in nea_long.columns:
        lines.append(nea_long["variable"].value_counts(dropna=False).to_frame("rows").to_markdown())
    else:
        lines.append("No NEA long rows.")

    lines.append("\n## WBGT rows by station — top 20\n")
    if not wbgt.empty:
        tmp = wbgt.groupby("station_id").agg(
            n=("official_wbgt_c", "size"),
            max_wbgt=("official_wbgt_c", "max"),
            ge31=("official_wbgt_c", lambda s: int((pd.to_numeric(s, errors="coerce") >= 31).sum())),
            ge33=("official_wbgt_c", lambda s: int((pd.to_numeric(s, errors="coerce") >= 33).sum())),
        ).reset_index().sort_values(["ge33", "ge31", "max_wbgt"], ascending=False).head(20)
        lines.append(tmp.to_markdown(index=False))
    else:
        lines.append("No WBGT rows.")

    lines.append("\n## Pairing health\n")
    if not pairs.empty:
        cols = [c for c in ["pair_used_for_calibration", "operational_match", "posthoc_weather_match", "weather_match_mode", "pair_location_source", "has_weather_match"] if c in pairs.columns]
        for c in cols:
            lines.append(f"### {c}\n")
            lines.append(pairs[c].value_counts(dropna=False).to_frame("rows").to_markdown())
        if "issue_age_hours" in pairs.columns:
            desc = pd.to_numeric(pairs["issue_age_hours"], errors="coerce").describe().to_frame("issue_age_hours")
            lines.append("\n### issue_age_hours\n")
            lines.append(desc.to_markdown())
    else:
        lines.append("No paired rows yet.")

    lines.append("\n## Notes\n")
    lines.append("- `raw_proxy_wbgt_fallback_c` and `raw_proxy_wbgt_radiative_fallback_c` are smoke-test fallback proxies only.")
    lines.append("- For formal v1.1 calibration, prefer the project’s production WBGT proxy if available.")
    lines.append("- Do not commit raw archive CSVs or forecast snapshots to Git; keep them in local/archive storage.")
    path.write_text("\n".join(lines), encoding="utf-8")


# -----------------------------------------------------------------------------
# Main collector
# -----------------------------------------------------------------------------


def collect_once(cfg: dict) -> dict:
    acfg = cfg.get("archive", {})
    root = ensure_dir(acfg.get("root_dir", "data/archive/v11_longterm"))
    outputs = ensure_dir(acfg.get("outputs_dir", "outputs/v11_archive_longterm"))
    raw_json_dir = ensure_dir(acfg.get("raw_json_dir", root / "raw_json"))
    state_path = Path(acfg.get("state_path", root / "archive_state.json"))
    state = read_json(state_path) if state_path.exists() else {}
    run_dt = utc_now()
    run_id = safe_run_id(run_dt, acfg.get("run_label_prefix", "v11"))
    run_date = run_dt.strftime("%Y%m%d")
    tz_name = acfg.get("timezone", "Asia/Singapore")
    errors: List[str] = []

    # Paths
    long_dir = ensure_dir(root / "long")
    norm_dir = ensure_dir(root / "normalized")
    pair_dir = ensure_dir(root / "paired")
    run_report_dir = ensure_dir(outputs / "run_reports")
    nea_long_path = long_dir / "nea_realtime_observations_v11_longterm.csv"
    wbgt_path = norm_dir / "nea_wbgt_v11_longterm_normalized.csv"
    nea_weather_path = norm_dir / "nea_station_weather_v11_longterm_wide.csv"
    openmeteo_path = norm_dir / "openmeteo_forecast_snapshots_v11_longterm.csv"
    pairs_path = Path(cfg.get("pairing", {}).get("output_operational_pairs_csv", pair_dir / "v11_operational_station_weather_pairs.csv"))
    latest_pairs_path = Path(cfg.get("pairing", {}).get("output_latest_pairs_csv", "data/calibration/v11/v11_station_weather_pairs_from_archive.csv"))

    # Fetch NEA endpoints.
    endpoint_rows = []
    dcfg = cfg.get("data_gov_sg", {})
    headers = {}
    api_key_env = dcfg.get("api_key_env")
    if api_key_env and os.getenv(api_key_env):
        headers["x-api-key"] = os.getenv(api_key_env)

    for ep in dcfg.get("endpoints", []):
        if not ep.get("enabled", True):
            continue
        js, err, _ = request_json(
            ep["url"],
            params=ep.get("params") or {},
            headers=headers,
            timeout=int(dcfg.get("timeout_seconds", 25)),
            retries=int(dcfg.get("retries", 3)),
            sleep_s=1.0,
        )
        if js and acfg.get("save_raw_json", True):
            raw_path = Path(raw_json_dir) / run_date / run_id / f"data_gov_{ep.get('name')}.json"
            write_json(raw_path, js)
        if err or not js:
            errors.append(f"{ep.get('name')}: {err}")
            continue
        df = parse_data_gov_realtime(js, ep, run_id, run_dt)
        if df.empty:
            errors.append(f"{ep.get('name')}: parsed 0 rows")
        else:
            endpoint_rows.append(df)
        time.sleep(float(dcfg.get("sleep_between_calls_seconds", 0.7)))

    nea_new = pd.concat(endpoint_rows, ignore_index=True, sort=False) if endpoint_rows else pd.DataFrame()
    nea_long = append_csv_dedup(nea_long_path, nea_new, ["timestamp", "station_id", "variable"])

    # Normalize from cumulative NEA long table.
    wbgt, nea_weather = normalize_nea_tables(nea_long, tz_name)
    wbgt_all = append_csv_dedup(wbgt_path, wbgt, ["timestamp_sgt", "station_id"])
    nea_weather_all = append_csv_dedup(nea_weather_path, nea_weather, ["timestamp_sgt", "station_id"])

    # Fetch Open-Meteo snapshots, less frequently if configured.
    openmeteo_new = pd.DataFrame()
    if maybe_should_fetch_openmeteo(cfg, state, run_dt):
        locs = build_openmeteo_locations(cfg, wbgt if not wbgt.empty else wbgt_all)
        om_rows = []
        for loc in locs:
            df, js, err = fetch_openmeteo_location(cfg, loc, run_id, run_dt)
            if js and acfg.get("save_raw_json", True):
                raw_path = Path(raw_json_dir) / run_date / run_id / f"openmeteo_{loc.get('location_id')}.json"
                write_json(raw_path, js)
            if err:
                errors.append(f"openmeteo {loc.get('location_id')}: {err}")
            elif not df.empty:
                om_rows.append(df)
            time.sleep(float(cfg.get("openmeteo", {}).get("sleep_between_location_calls_seconds", 0.4)))
        openmeteo_new = pd.concat(om_rows, ignore_index=True, sort=False) if om_rows else pd.DataFrame()
        state["last_openmeteo_run_utc"] = iso(run_dt)
    else:
        print("[INFO] Skipping Open-Meteo this run due to min_minutes_between_runs.")

    openmeteo_all = append_csv_dedup(openmeteo_path, openmeteo_new, ["forecast_issue_time_utc", "location_id", "valid_time_sgt"])

    # Build operational pairs from cumulative normalized tables.
    pairs = build_pairs(wbgt_all, openmeteo_all, cfg)
    pairs_all = append_csv_dedup(pairs_path, pairs, ["timestamp_sgt", "station_id"])
    latest_pairs_path.parent.mkdir(parents=True, exist_ok=True)
    pairs_all.to_csv(latest_pairs_path, index=False)

    # Optional daily partitions (compact and easy to inspect).
    if acfg.get("write_daily_partitions", True):
        part_dir = ensure_dir(root / "daily" / run_date)
        if not nea_new.empty:
            nea_new.to_csv(part_dir / f"{run_id}_nea_long.csv", index=False)
        if not openmeteo_new.empty:
            openmeteo_new.to_csv(part_dir / f"{run_id}_openmeteo.csv", index=False)

    # Clean old raw JSON snapshots if configured.
    raw_json_deleted_dirs = 0
    if acfg.get("save_raw_json", True):
        raw_json_deleted_dirs = cleanup_old_raw_json(raw_json_dir, int(acfg.get("max_raw_json_days_to_keep", 14)))
        if raw_json_deleted_dirs:
            print(f"[INFO] Cleaned {raw_json_deleted_dirs} old raw-json date directories.")

    # Run report and state.
    report_path = run_report_dir / f"{run_id}_archive_run_QA.md"
    write_qa_report(report_path, run_id=run_id, cfg=cfg, nea_long=nea_long, wbgt=wbgt_all,
                    nea_weather=nea_weather_all, openmeteo=openmeteo_all, pairs=pairs_all, errors=errors)
    # Also write latest QA pointer.
    latest_report = outputs / "v11_archive_latest_QA_report.md"
    latest_report.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    state.update({
        "last_run_id": run_id,
        "last_run_utc": iso(run_dt),
        "last_report": str(report_path),
        "last_errors": errors,
        "nea_long_rows": int(len(nea_long)),
        "wbgt_rows": int(len(wbgt_all)),
        "openmeteo_rows": int(len(openmeteo_all)),
        "pairs_rows": int(len(pairs_all)),
        "raw_json_deleted_dirs": int(raw_json_deleted_dirs),
    })
    write_json(state_path, state)

    return {
        "run_id": run_id,
        "errors": errors,
        "report_path": str(report_path),
        "nea_long_rows": len(nea_long),
        "wbgt_rows": len(wbgt_all),
        "openmeteo_rows": len(openmeteo_all),
        "pairs_rows": len(pairs_all),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect one OpenHeat v1.1 long-term archive snapshot.")
    parser.add_argument("--config", default="configs/v11/v11_longterm_archive_config.example.json")
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args()
    cfg = read_json(Path(args.config))
    res = collect_once(cfg)
    print("[OK] archive run:", res["run_id"])
    print("[OK] QA report:", res["report_path"])
    print(f"[OK] rows: WBGT={res['wbgt_rows']} OpenMeteo={res['openmeteo_rows']} pairs={res['pairs_rows']}")
    if res["errors"]:
        print("[WARN] errors/warnings:")
        for e in res["errors"]:
            print("  -", e)


if __name__ == "__main__":
    main()
