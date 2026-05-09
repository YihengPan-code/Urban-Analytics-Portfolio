"""
scripts/v08_merge_buildings_with_height.py  (revised)

3-tier fallback with provenance + QA flags.

Tier 1: HDB3D measured          confidence=high
Tier 2: URA land-use default    confidence=medium
Tier 3: constant 12m            confidence=low

Why no GHSL tier?
  GHSL mean_building_height_m at 100m grid cells in HDB towns is dominated by
  surrounding HDB blocks (~40m). Applying it to non-HDB buildings (typically
  6-18m: shophouses, civic facilities, places of worship) systematically
  overestimates their heights by 2-5x. Even with land-use bounds [8, 60m],
  the bias remains. Land-use defaults are less precise but unbiased.
"""
from pathlib import Path
import geopandas as gpd
import pandas as pd

HDB3D_FP   = Path(r"data\features_3d\hdb3d_buildings_toapayoh.geojson")
URA_FP     = Path(r"data\features_3d\ura_buildings_toapayoh.geojson")
LU_FP      = Path(r"data\raw\ura_masterplan2019_land_use.geojson")
AOI_FP     = Path(r"data\features_3d\aoi_buffered_200m.geojson")

OUT_FP     = Path(r"data\features_3d\merged_buildings_height_v08.geojson")
QA_FP      = Path(r"outputs\v08_non_hdb_fallback_large_buildings_QA.csv")
QA_FP.parent.mkdir(parents=True, exist_ok=True)

WORKING_CRS       = "EPSG:3414"
OVERLAP_THRESHOLD = 0.35
DEFAULT_HEIGHT    = 12.0
LARGE_AREA_THR    = 1000.0  # m^2 — flag for QA

# Land-use → default height. Order matters: most specific first.
LU_HEIGHT_MAP = [
    ("EDUCATIONAL",          12),
    ("RELIGIOUS",            10),
    ("PLACE OF WORSHIP",     10),
    ("HEALTH",               18),
    ("HOSPITAL",             24),
    ("CIVIC",                12),
    ("COMMUNITY",            12),
    ("BUSINESS PARK",        24),
    ("HOTEL",                30),
    ("COMMERCIAL",           18),
    ("RESIDENTIAL",          15),
    ("TRANSPORT",             8),
    ("UTILITY",               8),
    ("SPORTS",                9),
    ("PARK",                  6),
    ("OPEN SPACE",            6),
    ("PLACE",                 9),
]

print("=" * 60)
print("Stage 4 (revised): 3-tier merge with provenance + QA")
print("=" * 60)

# ---------- load ----------
hdb = gpd.read_file(HDB3D_FP).to_crs(WORKING_CRS)
ura = gpd.read_file(URA_FP).to_crs(WORKING_CRS)
print(f"  HDB3D: {len(hdb)}  URA: {len(ura)}")

# ---------- identify non-HDB ----------
hdb_union = hdb.geometry.union_all() if hasattr(hdb.geometry, "union_all") else hdb.unary_union
ura["overlap_frac"] = (ura.geometry.intersection(hdb_union).area /
                       ura.geometry.area.clip(lower=1e-6)).clip(0, 1)
non_hdb = ura[ura["overlap_frac"] < OVERLAP_THRESHOLD].copy().reset_index(drop=True)
non_hdb["building_area_m2"] = non_hdb.geometry.area
print(f"  Non-HDB to add: {len(non_hdb)}")

# ---------- Tier 2: spatial join with land-use ----------
print(f"\n  Loading land-use ({LU_FP.stat().st_size/1e6:.0f} MB) — ~1-2 min ...")
lu = gpd.read_file(LU_FP).to_crs(WORKING_CRS)

# Detect LU description column
lu_desc_col = None
for cand in ["LU_DESC", "LANDUSE", "LU_TEXT", "DESCRIPTION", "TYPE"]:
    if cand in lu.columns:
        lu_desc_col = cand
        break
print(f"  LU columns: {list(lu.columns)}")
print(f"  using land-use column: {lu_desc_col}")

# Pre-clip LU to AOI for speed (LU is huge nationally)
aoi = gpd.read_file(AOI_FP).to_crs(WORKING_CRS)
lu_in_aoi = lu[lu.intersects(aoi.geometry.iloc[0])].copy()
print(f"  LU polygons in AOI: {len(lu_in_aoi):,}")

# representative_point() guarantees the point lies inside the geometry
# (centroid can fall outside L-shaped or annular buildings).
non_hdb["join_point"] = non_hdb.geometry.representative_point()
points = gpd.GeoDataFrame(
    non_hdb[["building_area_m2", "overlap_frac"]].copy(),
    geometry=non_hdb["join_point"], crs=WORKING_CRS
)
points.index = non_hdb.index

joined = gpd.sjoin(points, lu_in_aoi[[lu_desc_col, "geometry"]],
                   how="left", predicate="within")
joined = joined[~joined.index.duplicated(keep="first")]
non_hdb["lu_desc"] = joined[lu_desc_col].astype(str).str.upper()
non_hdb.loc[non_hdb["lu_desc"].isin(["NONE", "NAN", ""]), "lu_desc"] = None
print(f"  matched land-use: {non_hdb['lu_desc'].notna().sum()}/{len(non_hdb)}")

# ---------- assign heights ----------
def lu_to_height(lu_desc):
    if not lu_desc or lu_desc in ("NAN", "NONE"):
        return None, None, None
    s = str(lu_desc).upper()
    for keyword, h in LU_HEIGHT_MAP:
        if keyword in s:
            return float(h), f"lu:{keyword}", "medium"
    return None, None, None

heights, sources, confidences, categories = [], [], [], []
for _, row in non_hdb.iterrows():
    h, src, conf = lu_to_height(row.get("lu_desc"))
    if h is not None:
        heights.append(h); sources.append(src); confidences.append(conf)
        categories.append(src.replace("lu:", ""))
    else:
        heights.append(DEFAULT_HEIGHT)
        sources.append("default_const_12m")
        confidences.append("low")
        categories.append("UNKNOWN")

non_hdb["height_m"]          = heights
non_hdb["height_source"]     = sources
non_hdb["height_confidence"] = confidences
non_hdb["lu_category"]       = categories

# ---------- QA flag: large fallback buildings ----------
suspicious_categories = ["PARK", "OPEN SPACE", "UNKNOWN"]
non_hdb["is_large_fallback"] = (
    (non_hdb["building_area_m2"] >= LARGE_AREA_THR) &
    (non_hdb["lu_category"].isin(suspicious_categories) |
     (non_hdb["height_source"] == "default_const_12m"))
)
n_qa = int(non_hdb["is_large_fallback"].sum())
print(f"\n  Large-fallback QA flags: {n_qa} buildings need visual check")

# ---------- summary ----------
print(f"\n  Non-HDB height_source distribution:")
print(non_hdb["height_source"].value_counts())
print(f"\n  Non-HDB height stats:")
print(non_hdb["height_m"].describe())

# ---------- build merged layer ----------
hdb_out = hdb[["building_id", "height_m", "geometry"]].copy()
hdb_out["source"]            = "hdb3d"
hdb_out["height_source"]     = "hdb3d_measured"
hdb_out["height_confidence"] = "high"
hdb_out["lu_desc"]           = None
hdb_out["lu_category"]       = "HDB"
hdb_out["building_area_m2"]  = hdb_out.geometry.area
hdb_out["is_large_fallback"] = False

non_hdb_out = non_hdb[["height_m", "height_source", "height_confidence",
                       "lu_desc", "lu_category", "building_area_m2",
                       "is_large_fallback", "geometry"]].copy()
non_hdb_out["building_id"]   = ["ura_" + str(i) for i in range(len(non_hdb_out))]
non_hdb_out["source"]        = "ura_non_hdb"

merged = pd.concat([hdb_out, non_hdb_out], ignore_index=True)
merged = gpd.GeoDataFrame(merged, geometry="geometry", crs=WORKING_CRS)

print("\n" + "=" * 60)
print("FINAL MERGED LAYER")
print("=" * 60)
print(f"  total buildings: {len(merged)}")
print(f"  by source:");           print(merged["source"].value_counts())
print(f"  by height_source:");    print(merged["height_source"].value_counts())
print(f"  by height_confidence:");print(merged["height_confidence"].value_counts())
print(f"  height_m stats:");      print(merged["height_m"].describe())
print(f"  null heights: {merged['height_m'].isna().sum()}")
print(f"  large fallback to QA: {n_qa}")

merged.to_file(OUT_FP, driver="GeoJSON")
print(f"\nWrote {OUT_FP}")

# ---------- QA export ----------
if n_qa > 0:
    qa = merged[merged["is_large_fallback"]].copy()
    qa["centroid_x"] = qa.geometry.centroid.x
    qa["centroid_y"] = qa.geometry.centroid.y
    qa[["building_id", "lu_desc", "lu_category", "height_m", "height_source",
        "building_area_m2", "centroid_x", "centroid_y"]].to_csv(QA_FP, index=False)
    print(f"Wrote QA list: {QA_FP}")