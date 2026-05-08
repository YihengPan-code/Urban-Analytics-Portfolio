from __future__ import annotations

import argparse
from pathlib import Path
import sys
import requests

ROOT = Path(__file__).resolve().parents[1]

DATASETS = {
    "ura_buildings": {
        "id": "d_e8e3249d4433845bdd8034ae44329d9e",
        "filename": "ura_masterplan2019_buildings.geojson",
    },
    "ura_land_use": {
        "id": "d_90d86daa5bfaa371668b84fa5f01424f",
        "filename": "ura_masterplan2019_land_use.geojson",
    },
    "nparks_parks": {
        "id": "d_77d7ec97be83d44f61b85454f844382f",
        "filename": "nparks_parks_nature_reserves.geojson",
    },
}


def poll_download_url(dataset_id: str) -> str:
    url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    js = r.json()
    if js.get("code") != 0:
        raise RuntimeError(js)
    return js["data"]["url"]


def download(name: str, out_dir: Path) -> Path:
    meta = DATASETS[name]
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / meta["filename"]
    url = poll_download_url(meta["id"])
    print(f"[INFO] Downloading {name} -> {out}")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with out.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    print(f"[OK] saved {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return out


def main():
    parser = argparse.ArgumentParser(description="Download official Singapore geodata via data.gov.sg poll-download API")
    parser.add_argument("--out-dir", default=str(ROOT / "data/raw"))
    parser.add_argument("--datasets", nargs="+", default=list(DATASETS.keys()), choices=list(DATASETS.keys()))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    for name in args.datasets:
        download(name, out_dir)


if __name__ == "__main__":
    main()
