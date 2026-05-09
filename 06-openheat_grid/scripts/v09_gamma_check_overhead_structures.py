"""
OpenHeat v0.9-gamma QA: detect overhead transport structures within SOLWEIG tile
buffers using the Overpass API directly (no osmnx dependency).

v2 hotfix:
- Adds explicit User-Agent header (Overpass main instance now rejects default
  python-requests UA with HTTP 406)
- Adds explicit Accept header
- Multi-endpoint fallback: tries main + 3 mirrors

Outputs:
  outputs/v09_gamma_qa/v09_overhead_structures_per_tile.csv  per-tile counts
  outputs/v09_gamma_qa/v09_overhead_structures.geojson       all detected features

Usage:
  python scripts/v09_gamma_check_overhead_structures.py
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import LineString, Polygon

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
]

REQUEST_HEADERS = {
    "User-Agent": "OpenHeat-ToaPayoh-research/0.9 (Singapore urban heat-stress study)",
    "Accept": "application/json",
}

OVERPASS_QUERY = """
[out:json][timeout:90];
(
  way["bridge"~"^(yes|viaduct|covered|movable)$"]({bbox});
  way["highway"]["layer"~"^[1-9]$"]({bbox});
  way["railway"~"^(subway|rail|light_rail|monorail)$"]["tunnel"!~"^(yes|true)$"]({bbox});
  way["covered"="yes"]({bbox});
);
out geom;
"""


def fetch_overpass(bbox_4326: tuple[float, float, float, float]) -> dict:
    south, west, north, east = bbox_4326
    bbox_str = f"{south},{west},{north},{east}"
    query = OVERPASS_QUERY.format(bbox=bbox_str)
    print(f"[INFO] Overpass bbox (S,W,N,E): {bbox_str}")

    last_err = None
    for url in OVERPASS_ENDPOINTS:
        try:
            print(f"[INFO] trying {url}")
            t0 = time.time()
            r = requests.post(
                url,
                data={"data": query},
                headers=REQUEST_HEADERS,
                timeout=180,
            )
            elapsed = time.time() - t0
            print(f"[INFO] response in {elapsed:.1f}s, status={r.status_code}")

            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 504, 503, 502, 500):
                print(f"[WARN] {url} returned {r.status_code}, trying next endpoint ...")
                last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                continue
            # Other 4xx: retry on next mirror but record reason
            print(f"[WARN] {url} returned {r.status_code}: {r.text[:200]}")
            last_err = f"HTTP {r.status_code}: {r.text[:200]}"
        except requests.exceptions.RequestException as e:
            print(f"[WARN] {url} request failed: {e!r}")
            last_err = repr(e)
            continue

    raise RuntimeError(
        f"All Overpass endpoints failed. Last error: {last_err}\n"
        "If all are returning 406, the Overpass servers may have changed their UA policy. "
        "If all timing out, the AOI might be too large or the servers are under load."
    )


def features_to_gdf(payload: dict) -> gpd.GeoDataFrame:
    rows = []
    for el in payload.get("elements", []):
        if el.get("type") != "way":
            continue
        geom_pts = el.get("geometry", [])
        if len(geom_pts) < 2:
            continue
        coords = [(p["lon"], p["lat"]) for p in geom_pts]
        if coords[0] == coords[-1] and len(coords) >= 4:
            geom = Polygon(coords)
        else:
            geom = LineString(coords)
        tags = el.get("tags", {})
        rows.append({
            "osm_id": el["id"],
            "bridge": tags.get("bridge"),
            "highway": tags.get("highway"),
            "railway": tags.get("railway"),
            "layer": tags.get("layer"),
            "covered": tags.get("covered"),
            "name": tags.get("name"),
            "ref": tags.get("ref"),
            "geometry": geom,
        })
    if not rows:
        cols = ["osm_id", "bridge", "highway", "railway", "layer", "covered", "name", "ref", "geometry"]
        return gpd.GeoDataFrame(columns=cols, crs="EPSG:4326")
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


def categorize(row) -> str:
    bridge = row.get("bridge")
    highway = row.get("highway")
    railway = row.get("railway")
    layer = row.get("layer")
    covered = row.get("covered")

    if railway in ("subway", "rail", "light_rail", "monorail"):
        return "elevated_rail"
    if bridge == "viaduct":
        return "viaduct"
    if bridge in ("yes", "movable") and highway in ("footway", "pedestrian", "path", "steps"):
        return "pedestrian_bridge"
    if bridge in ("yes", "movable") and highway in ("motorway", "trunk", "primary", "secondary"):
        return "elevated_road"
    if bridge in ("yes", "covered", "movable"):
        return "bridge_other"
    try:
        layer_int = int(layer) if layer is not None else 0
    except (ValueError, TypeError):
        layer_int = 0
    if layer_int > 0 and highway:
        return "elevated_road_layered"
    if covered == "yes":
        return "covered_walkway"
    return "other"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiles", default="data/solweig/v09_tiles/v09_solweig_tiles_buffered.geojson")
    parser.add_argument("--out-csv", default="outputs/v09_gamma_qa/v09_overhead_structures_per_tile.csv")
    parser.add_argument("--out-features", default="outputs/v09_gamma_qa/v09_overhead_structures.geojson")
    args = parser.parse_args()

    tiles_fp = Path(args.tiles)
    if not tiles_fp.exists():
        raise FileNotFoundError(f"Tiles buffered GeoJSON not found: {tiles_fp}")

    tiles = gpd.read_file(tiles_fp)
    print(f"[INFO] {len(tiles)} tiles loaded from {tiles_fp}")

    tiles_4326 = tiles.to_crs("EPSG:4326")
    minx, miny, maxx, maxy = tiles_4326.total_bounds
    bbox = (miny, minx, maxy, maxx)

    payload = fetch_overpass(bbox)
    osm = features_to_gdf(payload)
    print(f"[INFO] {len(osm)} OSM features returned in AOI bbox")

    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)

    if osm.empty:
        print("[WARN] No overhead structures found.")
        pd.DataFrame(columns=["tile_id", "n_overhead_structures"]).to_csv(args.out_csv, index=False)
        return

    osm["category"] = osm.apply(categorize, axis=1)
    osm = osm.to_crs("EPSG:3414")

    Path(args.out_features).parent.mkdir(parents=True, exist_ok=True)
    osm.to_file(args.out_features, driver="GeoJSON")

    rows = []
    for _, t in tiles.iterrows():
        inter = osm[osm.intersects(t.geometry)]
        cats = inter["category"].value_counts().to_dict()
        names = [n for n in inter["name"].dropna().unique() if str(n).strip()]
        refs = [n for n in inter["ref"].dropna().unique() if str(n).strip()]
        rows.append({
            "tile_id": t["tile_id"],
            "tile_type": t.get("tile_type", ""),
            "focus_cell_id": t.get("focus_cell_id", ""),
            "n_overhead_structures": len(inter),
            "n_elevated_rail": cats.get("elevated_rail", 0),
            "n_viaduct": cats.get("viaduct", 0),
            "n_pedestrian_bridge": cats.get("pedestrian_bridge", 0),
            "n_elevated_road": cats.get("elevated_road", 0) + cats.get("elevated_road_layered", 0),
            "n_bridge_other": cats.get("bridge_other", 0),
            "n_covered_walkway": cats.get("covered_walkway", 0),
            "structure_names": "; ".join(names[:5]) if names else "",
            "structure_refs": "; ".join(refs[:5]) if refs else "",
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(args.out_csv, index=False)

    print()
    print("=" * 80)
    print("Overhead structures within each SOLWEIG tile (700m buffered)")
    print("=" * 80)
    show_cols = ["tile_id", "tile_type", "n_overhead_structures", "n_elevated_rail", "n_viaduct", "n_pedestrian_bridge", "n_elevated_road", "n_covered_walkway"]
    print(summary[show_cols].to_string(index=False))
    print()
    print(f"[OK] per-tile summary: {args.out_csv}")
    print(f"[OK] features GeoJSON: {args.out_features}")

    affected = summary[summary["n_overhead_structures"] > 0]
    if affected.empty:
        print("\n[CONCLUSION] No tiles intersect overhead structures. SOLWEIG can proceed without flag.")
    else:
        print(f"\n[CONCLUSION] {len(affected)} of {len(summary)} tiles intersect overhead structures.")
        print("These tiles' SOLWEIG Tmrt is potentially overstated where pixels are under overhead infrastructure.")
        print("Document in v0.9 limitations; consider transport DSM for v1.0.")
        print()
        for _, r in affected.iterrows():
            names = r["structure_names"][:80] if r["structure_names"] else ""
            refs = r["structure_refs"][:30] if r["structure_refs"] else ""
            extra = f"  examples: {names} {refs}".strip() if (names or refs) else ""
            print(f"  - {r['tile_id']} ({r['tile_type']}): {r['n_overhead_structures']} structures")
            if extra:
                print(extra)


if __name__ == "__main__":
    main()
