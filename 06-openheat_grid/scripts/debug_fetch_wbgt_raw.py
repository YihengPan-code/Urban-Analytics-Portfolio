from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from openheat_forecast.live_api import fetch_datagov_realtime_api


def main():
    parser = argparse.ArgumentParser(description='Fetch raw data.gov.sg WBGT payload for debugging parser/schema changes')
    parser.add_argument('--api-version', choices=['v1', 'v2'], default='v2')
    parser.add_argument('--out', default=str(ROOT / 'outputs/debug_wbgt_raw.json'))
    args = parser.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = fetch_datagov_realtime_api('wbgt', api_version=args.api_version)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f'[OK] raw WBGT payload written to {out}')
    if isinstance(payload, dict):
        print(f'[INFO] top-level keys: {list(payload.keys())}')
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        print(f'[INFO] data keys: {list(data.keys()) if isinstance(data, dict) else type(data)}')

if __name__ == '__main__':
    main()
