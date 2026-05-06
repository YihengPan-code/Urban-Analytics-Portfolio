from __future__ import annotations

import argparse
from pathlib import Path
import sys
from datetime import datetime, timezone

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from openheat_forecast.live_pipeline import fetch_latest_nea_observation_bundle
from run_nea_api_schema_check import fixture_obs


def main():
    parser = argparse.ArgumentParser(description='Archive latest NEA realtime observations for future WBGT calibration')
    parser.add_argument('--mode', choices=['live', 'fixture'], default='live')
    parser.add_argument('--archive', default=str(ROOT / 'data/archive/nea_realtime_observations.csv'))
    parser.add_argument('--api-version', choices=['v1', 'v2'], default='v1', help='data.gov.sg API version; v1 is default in v0.6.1')
    args = parser.parse_args()

    archive_path = Path(args.archive)
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    if args.mode == 'live':
        obs = fetch_latest_nea_observation_bundle(api_version=args.api_version)
        source = f'live_{args.api_version}'
    else:
        obs = fixture_obs()
        source = 'fixture'

    archive_run_utc = datetime.now(timezone.utc).isoformat(timespec='seconds')
    if obs.empty:
        obs = pd.DataFrame([{
            'archive_run_utc': archive_run_utc,
            'archive_source': source,
            'archive_status': 'empty_response',
        }])
    else:
        obs['archive_run_utc'] = archive_run_utc
        obs['archive_source'] = source
        obs['archive_status'] = 'ok'

    if archive_path.exists():
        old = pd.read_csv(archive_path)
        out = pd.concat([old, obs], ignore_index=True)
        subset = [c for c in ['station_id', 'timestamp', 'api_name', 'archive_source'] if c in out.columns]
        if subset:
            out = out.drop_duplicates(subset=subset, keep='last')
    else:
        out = obs
    out.to_csv(archive_path, index=False)
    print(f'[OK] archived {len(obs)} station/heartbeat rows to {archive_path}')


if __name__ == '__main__':
    main()
