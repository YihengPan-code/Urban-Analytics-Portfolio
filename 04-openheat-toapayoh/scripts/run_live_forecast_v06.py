from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from openheat_forecast.live_pipeline import run_forecast_from_openmeteo, run_offline_sample_forecast


def main():
    parser = argparse.ArgumentParser(description='OpenHeat v0.6 live/sample forecast runner')
    parser.add_argument('--mode', choices=['sample', 'live'], default='sample', help='sample runs offline; live fetches Open-Meteo')
    parser.add_argument('--forecast-days', type=int, default=4)
    parser.add_argument('--grid', default=str(ROOT / 'data/sample/toa_payoh_grid_sample.csv'))
    parser.add_argument('--sample-forecast', default=str(ROOT / 'data/sample/openmeteo_heatwave_forecast_sample.csv'))
    parser.add_argument('--out-dir', default=str(ROOT / 'outputs'))
    args = parser.parse_args()

    if args.mode == 'live':
        try:
            files = run_forecast_from_openmeteo(args.grid, out_dir=args.out_dir, forecast_days=args.forecast_days)
            print('[OK] Live Open-Meteo forecast completed.')
        except Exception as e:
            print('[WARN] Live forecast failed:', repr(e))
            print('[INFO] Falling back to sample forecast so the pipeline still runs.')
            files = run_offline_sample_forecast(args.sample_forecast, args.grid, out_dir=args.out_dir, prefix='v06_fallback')
    else:
        files = run_offline_sample_forecast(args.sample_forecast, args.grid, out_dir=args.out_dir)
        print('[OK] Offline sample forecast completed.')

    for k, v in files.items():
        print(f'{k}: {v}')


if __name__ == '__main__':
    main()
