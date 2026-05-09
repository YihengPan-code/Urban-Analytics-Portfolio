"""
scripts/v08_clip_buildings_to_aoi.py

Stage 2 + 3 combined:
  - Build AOI = v0.7 grid total bounds + 200m buffer
  - Clip HDB3D buildings to AOI -> hdb3d_buildings_toapayoh.geojson
  - Clip URA buildings to AOI   -> ura_buildings_toapayoh.geojson

Why 200m buffer?
  SVF and shadow at grid-edge cells are influenced by buildings just
  outside the grid. Without buffer, edge SVF is biased high.
"""
from pathlib import Path
import geopandas as gpd
from shapely.geometry import box

# --- inputs ---
GRID_FP    = Path(r"data\grid\toa_payoh_grid_v07_features.geojson")
HDB3D_FP   = Path(r"data\features_3d\hdb3d_raw.geojson")
URA_FP     = Path(r"data\raw\ura_masterplan2019_buildings.geojson")

# --- outputs ---
OUT_DIR    = Path(r"data\features_3d")
HDB3D_OUT  = OUT_DIR / "hdb3d_buildings_toapayoh.geojson"
URA_OUT    = OUT_DIR / "ura_buildings_toapayoh.geojson"
AOI_OUT    = OUT_DIR / "aoi_buffered_200m.geojson"

OUT_DIR.mkdir(parents=True, exist_ok=True)

WORKING_CRS = "EPSG:3414"  # SVY21 / Singapore TM, units = meters
BUFFER_M    = 200

# ---------- Step 1: load grid + build buffered AOI ----------
print("=" * 60)
print("Step 1: Build AOI from v0.7 grid + 200m buffer")
print("=" * 60)
grid = gpd.read_file(GRID_FP)
print(f"  grid: {len(grid):,} cells, CRS={grid.crs}")

# Reproject to working CRS if needed
if grid.crs is None:
    raise RuntimeError("Grid has no CRS — refusing to guess.")
if grid.crs.to_string() != WORKING_CRS:
    grid = grid.to_crs(WORKING_CRS)
    print(f"  reprojected grid -> {WORKING_CRS}")

minx, miny, maxx, maxy = grid.total_bounds
print(f"  grid bounds (m): x=[{minx:.0f}, {maxx:.0f}], y=[{miny:.0f}, {maxy:.0f}]")
print(f"  grid extent: {(maxx-minx)/1000:.2f} km x {(maxy-miny)/1000:.2f} km")

aoi_geom = box(minx - BUFFER_M, miny - BUFFER_M,
               maxx + BUFFER_M, maxy + BUFFER_M)
aoi = gpd.GeoDataFrame({"name": ["aoi_grid_buffer200m"]},
                        geometry=[aoi_geom], crs=WORKING_CRS)
aoi.to_file(AOI_OUT, driver="GeoJSON")
print(f"  AOI: {(aoi_geom.bounds[2]-aoi_geom.bounds[0])/1000:.2f} km x "
      f"{(aoi_geom.bounds[3]-aoi_geom.bounds[1])/1000:.2f} km")
print(f"  wrote {AOI_OUT}")

# ---------- Step 2: clip HDB3D ----------
print("\n" + "=" * 60)
print("Step 2: Clip HDB3D buildings")
print("=" * 60)
hdb = gpd.read_file(HDB3D_FP)
print(f"  HDB3D total: {len(hdb):,}, CRS={hdb.crs}")
if hdb.crs.to_string() != WORKING_CRS:
    hdb = hdb.to_crs(WORKING_CRS)

# Use spatial index via .clip() (intersects-and-clips); for footprints
# we want buildings whose centroid OR geometry touches AOI.
# Use predicate intersects to keep buildings overlapping AOI.
hdb_in = hdb[hdb.intersects(aoi_geom)].copy()
print(f"  HDB3D in AOI: {len(hdb_in):,}")
print(f"  height_m  mean={hdb_in['height_m'].mean():.1f}  "
      f"min={hdb_in['height_m'].min():.1f}  "
      f"max={hdb_in['height_m'].max():.1f}")
hdb_in.to_file(HDB3D_OUT, driver="GeoJSON")
print(f"  wrote {HDB3D_OUT}")

# ---------- Step 3: clip URA ----------
print("\n" + "=" * 60)
print("Step 3: Clip URA Master Plan 2019 buildings")
print("=" * 60)
print(f"  loading {URA_FP} (this may take ~30s, file is 52MB)...")
ura = gpd.read_file(URA_FP)
print(f"  URA total: {len(ura):,}, CRS={ura.crs}")
if ura.crs.to_string() != WORKING_CRS:
    ura = ura.to_crs(WORKING_CRS)
    print(f"  reprojected URA -> {WORKING_CRS}")

ura_in = ura[ura.intersects(aoi_geom)].copy()
print(f"  URA in AOI: {len(ura_in):,}")

# URA columns are unpredictable — print what's there for the next step
print(f"  URA columns: {list(ura_in.columns)}")
ura_in.to_file(URA_OUT, driver="GeoJSON")
print(f"  wrote {URA_OUT}")

# ---------- summary ----------
print("\n" + "=" * 60)
print("DONE — Stage 2 + 3 outputs")
print("=" * 60)
print(f"  AOI         : {AOI_OUT}")
print(f"  HDB3D clip  : {HDB3D_OUT}  ({len(hdb_in):,} buildings)")
print(f"  URA clip    : {URA_OUT}  ({len(ura_in):,} buildings)")
print(f"\nNext: load all three into QGIS to visually verify before Stage 4 (merge).")