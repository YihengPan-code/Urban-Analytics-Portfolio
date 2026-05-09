from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import requests

from v09_common import load_config, ensure_dir, to_sgt_series, station_table_from_archive


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def request_openmeteo(endpoint: str, stations: pd.DataFrame, variables: list[str], start_date: str, end_date: str, cfg: dict) -> list[pd.DataFrame]:
    lats = ",".join(stations["station_lat"].astype(str).tolist())
    lons = ",".join(stations["station_lon"].astype(str).tolist())
    params = {
        "latitude": lats,
        "longitude": lons,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(variables),
        "timezone": cfg.get("time", {}).get("timezone", "Asia/Singapore"),
        "wind_speed_unit": cfg.get("historical_forecast", {}).get("wind_speed_unit", "ms"),
    }
    url = endpoint + "?" + urlencode(params, safe=",")
    timeout = cfg.get("historical_forecast", {}).get("timeout_seconds", 60)
    r = requests.get(endpoint, params=params, timeout=timeout)
    if r.status_code >= 400:
        raise requests.HTTPError(f"{r.status_code} for {r.url}: {r.text[:500]}")
    payload = r.json()
    payloads = payload if isinstance(payload, list) else [payload]
    out = []
    if len(payloads) != len(stations):
        # Some APIs return a single object for single-location chunks.
        if len(stations) == 1 and len(payloads) == 1:
            pass
        else:
            raise ValueError(f"Open-Meteo returned {len(payloads)} payloads for {len(stations)} stations")
    for idx, p in enumerate(payloads):
        st = stations.iloc[idx]
        hourly = p.get("hourly", {})
        if not hourly or "time" not in hourly:
            raise ValueError(f"No hourly data for station {st.get('station_id')}: keys={p.keys()}")
        df = pd.DataFrame(hourly)
        df["station_id"] = st["station_id"]
        df["station_name"] = st.get("station_name")
        df["station_lat"] = st["station_lat"]
        df["station_lon"] = st["station_lon"]
        df["openmeteo_endpoint"] = endpoint
        df["openmeteo_url"] = r.url
        df["openmeteo_utc_offset_seconds"] = p.get("utc_offset_seconds")
        out.append(df)
    return out


def main():
    parser = argparse.ArgumentParser(description="OpenHeat v0.9-alpha: fetch Open-Meteo historical forecast/weather for NEA WBGT stations.")
    parser.add_argument("--config", default="configs/v09_alpha_config.example.json")
    parser.add_argument("--archive", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--api", choices=["historical_forecast", "historical_weather", "auto"], default="auto")
    parser.add_argument("--start-date", default=None, help="Override start date YYYY-MM-DD")
    parser.add_argument("--end-date", default=None, help="Override end date YYYY-MM-DD")
    args = parser.parse_args()

    cfg = load_config(args.config)
    archive_path = Path(args.archive or cfg["archive_csv"])
    out_dir = ensure_dir(cfg.get("calibration_dir", "data/calibration"))
    out_fp = Path(args.out or out_dir / "v09_historical_forecast_by_station_hourly.csv")

    archive = pd.read_csv(archive_path)
    stations = station_table_from_archive(archive, cfg.get("pairing", {}).get("wbgt_variable_name", "official_wbgt_c"))
    if stations.empty:
        raise ValueError("No WBGT stations found in archive.")

    ts = to_sgt_series(archive["timestamp"])
    start_date = args.start_date or ts.min().date().isoformat()
    end_date = args.end_date or ts.max().date().isoformat()

    hf = cfg["historical_forecast"]
    chunk_size = int(hf.get("chunk_size", 20))

    api_order = []
    if args.api == "auto":
        api_order = [hf.get("primary_api", "historical_forecast"), hf.get("fallback_api", "historical_weather")]
    else:
        api_order = [args.api]

    last_err = None
    frames = None
    used_api = None

    for api in api_order:
        try:
            if api == "historical_forecast":
                endpoint = hf["historical_forecast_endpoint"]
                variables = hf["hourly_variables"]
            elif api == "historical_weather":
                endpoint = hf["historical_weather_endpoint"]
                variables = hf.get("hourly_variables_historical_weather", hf["hourly_variables"])
            else:
                raise ValueError(f"Unknown API: {api}")
            print(f"[INFO] Fetching {api} from {start_date} to {end_date} for {len(stations)} stations")
            all_frames = []
            for ch in chunks(list(range(len(stations))), chunk_size):
                st_chunk = stations.iloc[ch].reset_index(drop=True)
                all_frames.extend(request_openmeteo(endpoint, st_chunk, variables, start_date, end_date, cfg))
            frames = all_frames
            used_api = api
            break
        except Exception as e:
            print(f"[WARN] {api} failed: {e!r}")
            last_err = e
            frames = None
            continue

    if frames is None:
        raise RuntimeError(f"All Open-Meteo fetch attempts failed. Last error: {last_err!r}")

    out = pd.concat(frames, ignore_index=True)
    out["time_sgt"] = to_sgt_series(out["time"])
    out["openmeteo_api_used"] = used_api
    out = out.drop(columns=["time"], errors="ignore")

    out_fp.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_fp, index=False)

    report_lines = [
        "# OpenHeat v0.9-alpha Open-Meteo historical forcing fetch report",
        "",
        f"API used: **{used_api}**",
        f"Date range: **{start_date} → {end_date}**",
        f"Stations: **{len(stations)}**",
        f"Rows: **{len(out)}**",
        f"Output: `{out_fp}`",
        "",
        "## Variables",
        ", ".join([c for c in out.columns if c not in {"station_id","station_name","station_lat","station_lon","time_sgt","openmeteo_endpoint","openmeteo_url","openmeteo_utc_offset_seconds","openmeteo_api_used"}]),
        "",
        "## Notes",
        "- Historical Forecast API is preferred for forecast-like calibration. Historical Weather API is used only as fallback.",
        "- Radiation variables available may differ between APIs; check missing columns before modelling.",
    ]
    report_fp = Path(cfg.get("outputs_dir", "outputs/v09_alpha_calibration")) / "v09_historical_forecast_fetch_report.md"
    report_fp.parent.mkdir(parents=True, exist_ok=True)
    report_fp.write_text("\n".join(report_lines), encoding="utf-8")

    print("[OK] Historical forcing fetched")
    print("api_used:", used_api)
    print("csv:", out_fp)
    print("report:", report_fp)


if __name__ == "__main__":
    main()
