"""
scripts/v08_hdb3d_to_geojson.py
Extract HDB3D building ground footprints + heights from CityJSON.
Tested against hdb.json: v1.0, EPSG:3414, no transform block, LoD 1, ground z=0.
"""
import json
from pathlib import Path
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon

INPUT  = Path(r"data\raw\hdb3d\hdb3d-data\hdb.json")
OUTPUT = Path(r"data\features_3d\hdb3d_raw.geojson")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

print(f"Loading {INPUT} ...")
with open(INPUT, "r", encoding="utf-8") as f:
    cm = json.load(f)

# --- vertices: handle both compressed (with transform) and absolute ---
verts = np.array(cm["vertices"], dtype=float)
if "transform" in cm:
    scale = np.array(cm["transform"]["scale"])
    translate = np.array(cm["transform"]["translate"])
    verts = verts * scale + translate
    print("  applied transform")
else:
    print("  vertices are absolute coords")

print(f"  vertex bounds: x=[{verts[:,0].min():.0f}, {verts[:,0].max():.0f}], "
      f"y=[{verts[:,1].min():.0f}, {verts[:,1].max():.0f}], "
      f"z=[{verts[:,2].min():.1f}, {verts[:,2].max():.1f}]")
print(f"  CityObjects: {len(cm['CityObjects']):,}")

records = []
skipped_reasons = {"not_building": 0, "no_geom": 0, "not_solid": 0,
                   "no_ground_face": 0, "bad_polygon": 0}

for bid, bobj in cm["CityObjects"].items():
    if bobj.get("type") != "Building":
        skipped_reasons["not_building"] += 1
        continue

    attrs = bobj.get("attributes", {})
    height = attrs.get("height")
    osm_levels = attrs.get("osm_building:levels")
    hdb_max_floor = attrs.get("hdb_max_floor_lvl")
    osm_building = attrs.get("osm_building")
    hdb_blk_no = attrs.get("hdb_blk_no")
    hdb_street = attrs.get("hdb_street")
    year = attrs.get("hdb_year_completed")

    geom_list = bobj.get("geometry", [])
    if not geom_list:
        skipped_reasons["no_geom"] += 1
        continue

    g = geom_list[0]
    if g.get("type") != "Solid":
        skipped_reasons["not_solid"] += 1
        continue

    # Solid.boundaries[0] = outer shell = list of faces
    # each face = [outer_ring_indices, inner_ring1_indices, ...]
    shell_faces = g["boundaries"][0]

    # Find ground face: z values nearly identical AND z closest to ground
    # (HDB3D has terrain=0, so ground faces will have z ≈ 0)
    ground_face = None
    ground_z    = float("inf")
    ground_area_proxy = -1  # prefer the LARGER ground face if there are ties

    for face in shell_faces:
        outer_ring_idx = face[0]
        if len(outer_ring_idx) < 3:
            continue
        zs = verts[outer_ring_idx, 2]
        z_range = zs.max() - zs.min()
        if z_range > 0.5:   # not a horizontal face
            continue
        z_mean = float(zs.mean())
        # crude area proxy: ring length (more vertices ≈ larger ground for HDB)
        ring_size = len(outer_ring_idx)
        # pick the lowest horizontal face; tie-break by ring size
        if z_mean < ground_z - 0.1 or (abs(z_mean - ground_z) < 0.1 and ring_size > ground_area_proxy):
            ground_z = z_mean
            ground_area_proxy = ring_size
            ground_face = face

    if ground_face is None:
        skipped_reasons["no_ground_face"] += 1
        continue

    outer_ring = [tuple(verts[i, :2]) for i in ground_face[0]]
    try:
        poly = Polygon(outer_ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty or poly.area < 1.0:
            skipped_reasons["bad_polygon"] += 1
            continue
    except Exception:
        skipped_reasons["bad_polygon"] += 1
        continue

    records.append({
        "building_id": bid,
        "height_m": float(height) if height is not None else None,
        "osm_levels": int(osm_levels) if osm_levels and str(osm_levels).isdigit() else None,
        "hdb_max_floor": int(hdb_max_floor) if hdb_max_floor and str(hdb_max_floor).isdigit() else None,
        "osm_building": osm_building,
        "hdb_blk_no": hdb_blk_no,
        "hdb_street": hdb_street,
        "year_completed": int(year) if year and str(year).isdigit() else None,
        "ground_z": float(ground_z),
        "source": "hdb3d",
        "geometry": poly,
    })

print(f"\n  extracted: {len(records):,}")
print(f"  skipped breakdown: {skipped_reasons}")

gdf = gpd.GeoDataFrame(records, crs="EPSG:3414")
gdf.to_file(OUTPUT, driver="GeoJSON")
print(f"\nWrote {OUTPUT}")
print(f"\n--- height_m stats ---")
print(gdf["height_m"].describe())
print(f"\n  null heights: {gdf['height_m'].isna().sum()}")
print(f"\n--- bounds ---")
print(f"  {gdf.total_bounds}")
print(f"\n--- preview ---")
print(gdf[["building_id", "height_m", "osm_building", "hdb_blk_no", "hdb_street"]].head())