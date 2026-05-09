"""
scripts/v08_diagnose_ura_vs_hdb3d.py
Quick check: how many URA buildings are NOT covered by HDB3D?
"""
from pathlib import Path
import geopandas as gpd

hdb = gpd.read_file(r"data\features_3d\hdb3d_buildings_toapayoh.geojson")
ura = gpd.read_file(r"data\features_3d\ura_buildings_toapayoh.geojson")

print(f"HDB3D: {len(hdb)}, URA: {len(ura)}")
print(f"\nURA BLDG_TYPE distribution:")
print(ura["BLDG_TYPE"].value_counts(dropna=False))

# Spatial: which URA buildings overlap HDB3D significantly?
hdb_union = hdb.geometry.union_all() if hasattr(hdb.geometry, "union_all") else hdb.unary_union

ura["overlap_area"] = ura.geometry.intersection(hdb_union).area
ura["own_area"]     = ura.geometry.area
ura["overlap_frac"] = (ura["overlap_area"] / ura["own_area"]).clip(0, 1)

# A URA building is "covered by HDB3D" if >= 35% of its area overlaps any HDB3D building
covered = ura[ura["overlap_frac"] >= 0.35]
not_covered = ura[ura["overlap_frac"] < 0.35]

print(f"\nURA covered by HDB3D (overlap >= 35%): {len(covered)}")
print(f"URA NOT covered (i.e. non-HDB buildings to add): {len(not_covered)}")
print(f"\nNon-HDB BLDG_TYPE distribution:")
print(not_covered["BLDG_TYPE"].value_counts(dropna=False))
print(f"\nNon-HDB area stats (m²):")
print(not_covered["own_area"].describe())