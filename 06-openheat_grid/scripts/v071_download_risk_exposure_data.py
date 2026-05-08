from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]

# Stable data.gov.sg dataset IDs verified for v0.7.1.
DATASETS: dict[str, dict[str, Any]] = {
    "census_age_subzone": {
        "kind": "datastore_csv",
        "dataset_id": "d_d95ae740c0f8961a0b10435836660ce0",
        "out": "data/raw/demographics/singstat_subzone_age_2020.csv",
        "description": "Resident Population by Planning Area/Subzone of Residence, Age Group and Sex (Census 2020)",
    },
    "subzone_boundary": {
        "kind": "poll_download_geojson",
        "dataset_id": "d_8594ae9ff96d0c708bc2af633048edfb",
        "out": "data/raw/boundaries/ura_mp19_subzone_no_sea.geojson",
        "description": "URA Master Plan 2019 Subzone Boundary (No Sea)",
    },
    "bus_stops": {
        "kind": "poll_download_geojson",
        "dataset_id": "d_3f172c6feb3f4f92a2f47d93eed2908a",
        "out": "data/raw/poi/lta_bus_stops.geojson",
        "description": "LTA Bus Stop",
    },
    "mrt_exits": {
        "kind": "poll_download_geojson",
        "dataset_id": "d_b39d3a0871985372d7e1637193335da5",
        "out": "data/raw/poi/lta_mrt_exits.geojson",
        "description": "LTA MRT Station Exit",
    },
    "hawker_centres": {
        "kind": "poll_download_geojson",
        "dataset_id": "d_4a086da0a5553be1d89383cd90d07ecd",
        "out": "data/raw/poi/nea_hawker_centres.geojson",
        "description": "NEA Hawker Centres",
    },
    "sport_facilities": {
        "kind": "poll_download_geojson",
        "dataset_id": "d_9b87bab59d036a60fad2a91530e10773",
        "out": "data/raw/poi/sportsg_facilities.geojson",
        "description": "SportSG Sport Facilities",
    },
    "preschools": {
        "kind": "poll_download_geojson",
        "dataset_id": "d_61eefab99958fd70e6aab17320a71f1c",
        "out": "data/raw/poi/ecda_preschools.geojson",
        "description": "ECDA Pre-Schools Location",
    },
    "eldercare_services": {
        "kind": "collection_geojson",
        "collection_id": 714,
        "out": "data/raw/poi/moh_eldercare_services.geojson",
        "description": "MOH Eldercare Services GEOJSON collection resource",
        "manual_url": "https://data.gov.sg/dataset/eldercare-services",
    },
}


def _request_json(url: str, timeout: int = 60) -> dict[str, Any]:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def poll_download_url(dataset_id: str) -> str:
    url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
    data = _request_json(url)
    if data.get("code") != 0:
        raise RuntimeError(f"poll-download failed for {dataset_id}: {data}")
    download_url = data.get("data", {}).get("url")
    if not download_url:
        raise RuntimeError(f"No download URL returned for {dataset_id}: {data}")
    return str(download_url)


def download_binary(url: str, out_path: Path, timeout: int = 120) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, timeout=timeout, stream=True) as r:
        r.raise_for_status()
        with out_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def download_datastore_csv(dataset_id: str, out_path: Path, limit: int = 10000) -> None:
    url = "https://data.gov.sg/api/action/datastore_search"
    params = {"resource_id": dataset_id, "limit": limit}
    data = _request_json(url + "?" + requests.compat.urlencode(params))
    if not data.get("success", False):
        raise RuntimeError(f"datastore_search failed for {dataset_id}: {data}")
    records = data.get("result", {}).get("records", [])
    if not records:
        raise RuntimeError(f"No records returned for {dataset_id}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame.from_records(records).to_csv(out_path, index=False)


def find_geojson_resource_from_collection(collection_id: int) -> str | None:
    """Best-effort downloader for data.gov.sg collection metadata resources.

    This is intentionally defensive because collection metadata schema has changed
    across data.gov.sg API versions. If it cannot find a direct GEOJSON URL, the
    script prints a manual-download instruction rather than failing silently.
    """
    url = f"https://api-production.data.gov.sg/v2/public/api/collections/{collection_id}/metadata"
    data = _request_json(url)

    # Search recursively for likely download URL entries that mention geojson.
    candidates: list[str] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            text_blob = " ".join(str(v).lower() for v in obj.values() if isinstance(v, (str, int, float)))
            url_value = None
            for key in ("downloadUrl", "download_url", "url", "fileUrl", "file_url"):
                if key in obj and isinstance(obj[key], str):
                    url_value = obj[key]
            if url_value and ("geojson" in text_blob or url_value.lower().endswith(".geojson")):
                candidates.append(url_value)
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return candidates[0] if candidates else None


def download_one(key: str, force: bool = False) -> Path:
    if key not in DATASETS:
        raise KeyError(f"Unknown dataset key: {key}. Available: {sorted(DATASETS)}")
    meta = DATASETS[key]
    out = ROOT / meta["out"]
    if out.exists() and not force:
        print(f"[SKIP] {key}: exists -> {out}")
        return out

    print(f"[DOWNLOAD] {key}: {meta['description']}")
    kind = meta["kind"]
    if kind == "datastore_csv":
        download_datastore_csv(meta["dataset_id"], out)
    elif kind == "poll_download_geojson":
        download_url = poll_download_url(meta["dataset_id"])
        download_binary(download_url, out)
    elif kind == "collection_geojson":
        download_url = find_geojson_resource_from_collection(int(meta["collection_id"]))
        if not download_url:
            print(f"[WARN] Could not automatically locate GEOJSON URL for {key}.")
            print(f"       Please manually download from: {meta.get('manual_url')}")
            print(f"       Save it as: {out}")
            return out
        download_binary(download_url, out)
    else:
        raise ValueError(f"Unsupported kind: {kind}")

    print(f"[OK] {key}: {out} ({out.stat().st_size:,} bytes)")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Download v0.7.1 risk/exposure open datasets")
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=[
            "census_age_subzone",
            "subzone_boundary",
            "bus_stops",
            "mrt_exits",
            "hawker_centres",
            "sport_facilities",
            "preschools",
            "eldercare_services",
        ],
        help="Dataset keys to download. Use --list to see all keys.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--list", action="store_true", help="List dataset keys and exit")
    args = parser.parse_args()

    if args.list:
        print(json.dumps(DATASETS, indent=2, ensure_ascii=False))
        return

    for key in args.datasets:
        try:
            download_one(key, force=args.force)
        except Exception as e:
            print(f"[ERROR] {key}: {e}", file=sys.stderr)
            if key == "eldercare_services":
                print("[INFO] Eldercare is optional for v0.7.1-alpha; continue after manual download if needed.")
            else:
                raise


if __name__ == "__main__":
    main()
