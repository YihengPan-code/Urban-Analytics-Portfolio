from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from openheat_forecast.live_api import normalise_realtime_station_readings
from openheat_forecast.live_pipeline import (
    fetch_latest_nea_observation_long_bundle,
    station_observations_to_long,
)


def fixture_long_obs() -> pd.DataFrame:
    """Build long-format archive rows from bundled NEA fixtures."""
    fixture_specs = [
        ("air_temperature", "air_temperature_c", ROOT / "data/fixtures/nea_air_temperature_sample.json", "air_temperature_c", "deg C"),
        ("relative_humidity", "relative_humidity_percent", ROOT / "data/fixtures/nea_relative_humidity_sample.json", "relative_humidity_percent", "percent"),
        ("wind_speed", "wind_speed_ms", ROOT / "data/fixtures/nea_wind_speed_sample.json", "wind_speed_raw", "m/s"),
        ("wbgt", "official_wbgt_c", ROOT / "data/fixtures/nea_wbgt_sample.json", "official_wbgt_c", "deg C"),
    ]
    frames = []
    for api_name, variable, path, value_col, unit in fixture_specs:
        payload = json.loads(path.read_text())
        payload.setdefault("_openheat_api_name", api_name)
        payload.setdefault("_openheat_api_version", "v2")
        df = normalise_realtime_station_readings(payload, value_col)
        if variable == "wind_speed_ms" and "wind_speed_raw" in df.columns and "wind_speed_ms" not in df.columns:
            # The bundled fixture is already in m/s-like sample values. The live
            # wrapper handles knots -> m/s conversion; fixture mode just tests format.
            df["wind_speed_ms"] = df["wind_speed_raw"]
            value_col = "wind_speed_ms"
        frames.append(station_observations_to_long(df, variable=variable, value_col=value_col, unit=unit))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main():
    parser = argparse.ArgumentParser(description="Archive latest NEA realtime observations for future WBGT calibration")
    parser.add_argument("--mode", choices=["live", "fixture"], default="live")
    parser.add_argument("--archive", default=str(ROOT / "data/archive/nea_realtime_observations.csv"))
    parser.add_argument("--api-version", choices=["v1", "v2"], default="v2", help="data.gov.sg API version; v2 is default in v0.6.4 because WBGT uses the new weather endpoint")
    args = parser.parse_args()

    archive_path = Path(args.archive)
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    if args.mode == "live":
        obs = fetch_latest_nea_observation_long_bundle(api_version=args.api_version)
        source = f"live_{args.api_version}"
    else:
        obs = fixture_long_obs()
        source = "fixture"

    archive_run_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if obs.empty:
        obs = pd.DataFrame([{
            "archive_run_utc": archive_run_utc,
            "archive_source": source,
            "archive_status": "empty_response",
        }])
    else:
        obs["archive_run_utc"] = archive_run_utc
        obs["archive_source"] = source
        obs["archive_status"] = "ok"

    if archive_path.exists():
        old = pd.read_csv(archive_path)
        # v0.6.3 wrote a wide-format archive that could lose WBGT metadata.
        # Mixing that file with v0.6.4 long-format rows would make calibration
        # ambiguous, so keep a timestamped backup and start a clean long archive.
        legacy_wide_cols = {"official_wbgt_c", "air_temperature_c", "relative_humidity_percent", "wind_speed_ms"}
        looks_legacy = ("variable" not in old.columns) or (legacy_wide_cols.intersection(old.columns) and old.get("variable", pd.Series(dtype=object)).isna().all())
        if looks_legacy:
            backup = archive_path.with_name(archive_path.stem + "_legacy_wide_backup_" + archive_run_utc.replace(":", "").replace("+", "Z") + archive_path.suffix)
            old.to_csv(backup, index=False)
            print(f"[WARN] Existing archive looked like legacy wide format; backed it up to {backup}")
            out = obs
        else:
            out = pd.concat([old, obs], ignore_index=True, sort=False)
            # Long-format de-duplication. Multiple fetches within the same 15-minute
            # WBGT interval should not create duplicate calibration rows. Keep the
            # latest archive run in case data.gov.sg later revises a reading.
            subset = [c for c in ["station_id", "timestamp", "variable", "archive_source"] if c in out.columns]
            if subset:
                out = out.drop_duplicates(subset=subset, keep="last")
    else:
        out = obs

    out.to_csv(archive_path, index=False)
    print(f"[OK] archived {len(obs)} long-format observation rows to {archive_path}")
    if not obs.empty and "variable" in obs.columns:
        counts = obs["variable"].value_counts(dropna=False).to_dict()
        print(f"[INFO] variables archived this run: {counts}")


if __name__ == "__main__":
    main()
