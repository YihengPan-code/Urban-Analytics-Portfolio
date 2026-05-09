"""
scripts/v08_zonal_umep_to_grid.py  (final, self-checked)
"""
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds

GRID_FP    = Path(r"data\grid\toa_payoh_grid_v07_features.geojson")
DSM_FP     = Path(r"data\rasters\v08\dsm_buildings_2m_toapayoh.tif")
SVF_FP     = Path(r"data\rasters\v08\umep_svf\SkyViewFactor.tif")
SHADOW_DIR = Path(r"data\rasters\v08\umep_shadow")
OUT_FP     = Path(r"data\grid\toa_payoh_grid_v08_umep_morphology.csv")
OUT_FP.parent.mkdir(parents=True, exist_ok=True)

WORKING_CRS     = "EPSG:3414"
SHADOW_DATE_TAG = "20260320"
HOURS_TO_USE    = [10, 11, 12, 13, 14, 15, 16]
PEAK_HOURS      = [13, 14, 15]

print("=" * 60)
print("Stage 8: UMEP zonal stats -> 100m grid")
print("=" * 60)

# Load grid
grid = gpd.read_file(GRID_FP).to_crs(WORKING_CRS)
print(f"  grid cells: {len(grid)}")
cell_id_col = next((c for c in ["cell_id", "id", "fid", "FID", "OBJECTID"]
                    if c in grid.columns), None)
if cell_id_col is None:
    grid["cell_id"] = range(len(grid))
    cell_id_col = "cell_id"
print(f"  cell ID column: {cell_id_col}")

# Load rasters
print("\n  loading rasters ...")
with rasterio.open(DSM_FP) as src:
    dsm = src.read(1)
    dsm_transform = src.transform
    dsm_shape = dsm.shape
print(f"    DSM: {dsm_shape}")

with rasterio.open(SVF_FP) as src:
    svf = src.read(1)
    if svf.shape != dsm_shape:
        raise RuntimeError(f"SVF {svf.shape} != DSM {dsm_shape}")

shadow_arrs = {}
for h in HOURS_TO_USE:
    fp = SHADOW_DIR / f"Shadow_{SHADOW_DATE_TAG}_{h:02d}00_LST.tif"
    if not fp.exists():
        fp = SHADOW_DIR / f"Shadow_{SHADOW_DATE_TAG}_{h}00_LST.tif"
    if not fp.exists():
        raise FileNotFoundError(fp)
    with rasterio.open(fp) as src:
        arr = src.read(1).astype(np.float32)
        if arr.shape != dsm_shape:
            raise RuntimeError(f"Shadow {h}h shape mismatch")
        shadow_arrs[h] = arr
print(f"  loaded {len(shadow_arrs)} shadow hours")

# UMEP: 0=shadow, 1=sunlit -> shade = 1 - sunlit
shade_arrs   = {h: (1.0 - arr) for h, arr in shadow_arrs.items()}
shade_stack  = np.stack([shade_arrs[h] for h in HOURS_TO_USE], axis=0)
shade_peak_s = np.stack([shade_arrs[h] for h in PEAK_HOURS],   axis=0)
shade_10_16  = shade_stack.mean(axis=0)
shade_13_15  = shade_peak_s.mean(axis=0)
shade_max_hr = shade_stack.max(axis=0)

# Helpers
def cell_to_window(cell_geom, transform, raster_shape):
    minx, miny, maxx, maxy = cell_geom.bounds
    win = from_bounds(minx, miny, maxx, maxy, transform)
    r0 = max(int(np.floor(win.row_off)), 0)
    c0 = max(int(np.floor(win.col_off)), 0)
    r1 = min(int(np.ceil(win.row_off + win.height)), raster_shape[0])
    c1 = min(int(np.ceil(win.col_off + win.width)),  raster_shape[1])
    return r0, r1, c0, c1

def pixel_centers_in_window(r0, r1, c0, c1, transform):
    rows = np.arange(r0, r1) + 0.5
    cols = np.arange(c0, c1) + 0.5
    cc, rr = np.meshgrid(cols, rows)
    xs = transform.a * cc + transform.b * rr + transform.c
    ys = transform.d * cc + transform.e * rr + transform.f
    return xs, ys

EMPTY_KEYS = (["open_pixel_fraction", "building_pixel_fraction",
               "n_total_pixels", "n_open_pixels",
               "svf_umep_mean_open", "svf_umep_p10_open", "svf_umep_p90_open",
               "svf_umep_mean_all",
               "shade_fraction_umep_10_16_open",
               "shade_fraction_umep_13_15_open",
               "shade_fraction_umep_peak_open",
               "dsm_mean_height_all", "dsm_max_height",
               "dsm_mean_height_buildings_only"]
              + [f"shade_fraction_umep_{h:02d}00_open" for h in HOURS_TO_USE])

def empty_rec(base):
    out = dict(base)
    out.update({k: np.nan for k in EMPTY_KEYS})
    return out

try:
    from shapely.vectorized import contains as v_contains
    HAVE_VECTORIZED = True
except ImportError:
    from shapely.geometry import Point
    HAVE_VECTORIZED = False
    print("  (shapely.vectorized not available; falling back to per-point)")

# Iterate
print("\n  computing zonal stats per cell ...")
records = []
empty_cells = 0
all_building_cells = 0

for idx, row in grid.iterrows():
    rec = {"cell_id": row[cell_id_col]}
    geom = row.geometry

    r0, r1, c0, c1 = cell_to_window(geom, dsm_transform, dsm_shape)
    if r1 <= r0 or c1 <= c0:
        empty_cells += 1
        records.append(empty_rec(rec))
        continue

    dsm_w  = dsm[r0:r1, c0:c1]
    svf_w  = svf[r0:r1, c0:c1]
    s10_16 = shade_10_16[r0:r1, c0:c1]
    s13_15 = shade_13_15[r0:r1, c0:c1]
    s_max  = shade_max_hr[r0:r1, c0:c1]
    per_hr = {h: shade_arrs[h][r0:r1, c0:c1] for h in HOURS_TO_USE}

    xs, ys = pixel_centers_in_window(r0, r1, c0, c1, dsm_transform)
    if HAVE_VECTORIZED:
        in_cell = v_contains(geom, xs.ravel(), ys.ravel()).reshape(xs.shape)
    else:
        in_cell = np.array([geom.contains(Point(x, y))
                            for x, y in zip(xs.ravel(), ys.ravel())]).reshape(xs.shape)

    n_total = int(in_cell.sum())
    if n_total == 0:
        empty_cells += 1
        records.append(empty_rec(rec))
        continue

    open_in_cell = in_cell & (dsm_w == 0)
    n_open = int(open_in_cell.sum())

    rec["open_pixel_fraction"]     = n_open / n_total
    rec["building_pixel_fraction"] = 1.0 - rec["open_pixel_fraction"]
    rec["n_total_pixels"]          = n_total
    rec["n_open_pixels"]           = n_open

    if n_open > 0:
        svf_open = svf_w[open_in_cell]
        rec["svf_umep_mean_open"] = float(svf_open.mean())
        rec["svf_umep_p10_open"]  = float(np.percentile(svf_open, 10))
        rec["svf_umep_p90_open"]  = float(np.percentile(svf_open, 90))
        rec["shade_fraction_umep_10_16_open"] = float(s10_16[open_in_cell].mean())
        rec["shade_fraction_umep_13_15_open"] = float(s13_15[open_in_cell].mean())
        rec["shade_fraction_umep_peak_open"]  = float(s_max[open_in_cell].mean())
        for h in HOURS_TO_USE:
            rec[f"shade_fraction_umep_{h:02d}00_open"] = float(per_hr[h][open_in_cell].mean())
    else:
        all_building_cells += 1
        for k in ["svf_umep_mean_open", "svf_umep_p10_open", "svf_umep_p90_open",
                  "shade_fraction_umep_10_16_open",
                  "shade_fraction_umep_13_15_open",
                  "shade_fraction_umep_peak_open"]:
            rec[k] = np.nan
        for h in HOURS_TO_USE:
            rec[f"shade_fraction_umep_{h:02d}00_open"] = np.nan

    rec["svf_umep_mean_all"] = float(svf_w[in_cell].mean())

    dsm_in = dsm_w[in_cell]
    rec["dsm_mean_height_all"] = float(dsm_in.mean())
    rec["dsm_max_height"]      = float(dsm_in.max())
    bldg_pix = dsm_in[dsm_in > 0]
    rec["dsm_mean_height_buildings_only"] = float(bldg_pix.mean()) if len(bldg_pix) > 0 else 0.0

    records.append(rec)

print(f"\n  cells processed: {len(records)}")
print(f"  empty cells: {empty_cells}")
print(f"  fully-building cells: {all_building_cells}")

df = pd.DataFrame(records)
df["umep_dsm_resolution_m"]   = 2
df["umep_shadow_date"]        = SHADOW_DATE_TAG
df["umep_shadow_time_window"] = "10:00-16:00 LST (UTC+8)"

print("\n  summary stats:")
print(df[["open_pixel_fraction",
         "svf_umep_mean_open", "svf_umep_mean_all",
         "shade_fraction_umep_10_16_open",
         "shade_fraction_umep_13_15_open",
         "dsm_mean_height_buildings_only"]].describe())

print(f"\n  null count:")
for c in ["svf_umep_mean_open", "shade_fraction_umep_10_16_open"]:
    print(f"    {c}: {df[c].isna().sum()}")

diff = (df["svf_umep_mean_all"] - df["svf_umep_mean_open"]).dropna()
print(f"\n  SVF (all - open) diagnostic:")
print(f"    mean diff:   {diff.mean():+.4f}  (expected positive ~0.02-0.10)")
print(f"    median diff: {diff.median():+.4f}")

df.to_csv(OUT_FP, index=False)
print(f"\nWrote {OUT_FP}")
print(f"  {len(df)} rows, {len(df.columns)} columns")