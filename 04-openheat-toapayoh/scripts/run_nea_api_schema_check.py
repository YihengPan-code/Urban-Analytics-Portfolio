from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from openheat_forecast.live_api import (
    fetch_air_temperature,
    fetch_relative_humidity,
    fetch_wind_speed,
    fetch_official_wbgt,
    normalise_realtime_station_readings,
    attach_nearest_station,
)
import pandas as pd


def fixture_obs() -> pd.DataFrame:
    # Keep fixture using v2 sample to verify parser remains backward compatible.
    paths = {
        'air_temperature_c': ROOT / 'data/fixtures/nea_air_temperature_sample.json',
        'relative_humidity_percent': ROOT / 'data/fixtures/nea_relative_humidity_sample.json',
        'wind_speed_raw': ROOT / 'data/fixtures/nea_wind_speed_sample.json',
        'official_wbgt_c': ROOT / 'data/fixtures/nea_wbgt_sample.json',
    }
    frames = []
    for value_name, path in paths.items():
        payload = json.loads(path.read_text())
        frames.append(normalise_realtime_station_readings(payload, value_name))
    out = frames[0]
    for f in frames[1:]:
        drop_meta = [c for c in ['station_name','station_lat','station_lon','device_id'] if c in f.columns and c in out.columns]
        out = out.merge(f.drop(columns=drop_meta, errors='ignore'), on='station_id', how='outer', suffixes=('', '_rhs'))
    for c in [c for c in out.columns if c.endswith('_rhs')]:
        out.drop(columns=[c], inplace=True, errors='ignore')
    if 'wind_speed_raw' in out.columns:
        out['wind_speed_ms'] = out['wind_speed_raw']
    return out


def main():
    parser = argparse.ArgumentParser(description='Check NEA/data.gov.sg API parser schema')
    parser.add_argument('--mode', choices=['fixture', 'live'], default='fixture')
    parser.add_argument('--grid', default=str(ROOT / 'data/sample/toa_payoh_grid_sample.csv'))
    parser.add_argument('--out-dir', default=str(ROOT / 'outputs'))
    parser.add_argument('--api-version', choices=['v1', 'v2'], default='v2', help='v2 is default because current WBGT uses api-open.data.gov.sg weather?api=wbgt')
    args = parser.parse_args()

    if args.mode == 'fixture':
        obs = fixture_obs()
    else:
        obs = fetch_official_wbgt(api_version=args.api_version)
        # Also test that the other wrappers can be called. They are not merged here
        # because station availability can differ by API.
        _ = fetch_air_temperature(api_version=args.api_version)
        _ = fetch_relative_humidity(api_version=args.api_version)
        _ = fetch_wind_speed(api_version=args.api_version)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    obs_file = out_dir / 'v06_1_nea_station_observations_schema_check.csv'
    obs.to_csv(obs_file, index=False)

    grid = pd.read_csv(args.grid)
    nearest_file = out_dir / 'v06_1_grid_nearest_wbgt_station.csv'
    if {'station_lat', 'station_lon'}.issubset(obs.columns) and obs[['station_lat','station_lon']].notna().any().any():
        nearest = attach_nearest_station(grid, obs.dropna(subset=['station_lat','station_lon']))
        nearest.to_csv(nearest_file, index=False)
        print(f'[OK] observations: {obs_file}')
        print(f'[OK] nearest station table: {nearest_file}')
    else:
        # WBGT v2 sometimes returns station readings without station coordinates.
        # Do not fail the whole live check; write a diagnostic table and keep the
        # official WBGT observations for calibration/time-series archiving.
        nearest = grid.copy()
        nearest['nearest_station_id'] = pd.NA
        nearest['nearest_station_name'] = pd.NA
        nearest['nearest_official_wbgt_c'] = pd.NA
        nearest['nearest_station_distance_m'] = pd.NA
        nearest['station_representativeness'] = 'unavailable_station_coordinates'
        nearest['calibration_note'] = (
            'Official WBGT observations were fetched, but this API response did not include station_lat/station_lon. '
            'Hotspot forecast can still run; nearest-station calibration needs a station lookup table or a parser update once raw schema is inspected.'
        )
        nearest.to_csv(nearest_file, index=False)
        print(f'[OK] observations: {obs_file}')
        print(f'[WARN] WBGT response has no station coordinates; wrote diagnostic table: {nearest_file}')
        print('[NEXT] You can still archive observations. For nearest-station calibration, inspect outputs/debug_wbgt_raw.json or provide a station lookup table.')


if __name__ == '__main__':
    main()
