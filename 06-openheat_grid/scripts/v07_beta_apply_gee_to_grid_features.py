"""Apply Google Earth Engine height/vegetation exports to OpenHeat v0.7 grid features.

This is a v0.7-beta post-merge helper. It keeps the vector-derived features
(building_density, land_use_hint, park_distance, road_fraction, etc.) from the
base grid feature table, replaces/adds GHSL/Dynamic World/Sentinel-2 features,
and recomputes screening-level gvi_percent, svf and shade_fraction.

Example:
    python scripts/v07_beta_apply_gee_to_grid_features.py ^
      --base data/grid/toa_payoh_grid_v07_features.csv ^
      --gee data/raw/gee_height_vegetation_by_grid.csv ^
      --out data/grid/toa_payoh_grid_v07_features_beta_gee.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

REQUIRED_GEE_COLUMNS = [
    "cell_id",
    "mean_building_height_m",
    "tree_canopy_fraction",
    "grass_fraction",
    "water_fraction",
    "built_up_fraction",
    "ndvi_mean",
]


def _clip01(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").clip(0, 1)


def validate_gee(gee: pd.DataFrame) -> list[str]:
    problems: list[str] = []
    missing = [c for c in REQUIRED_GEE_COLUMNS if c not in gee.columns]
    if missing:
        problems.append(f"Missing required GEE columns: {missing}")
        return problems
    if gee["cell_id"].duplicated().any():
        dup = gee.loc[gee["cell_id"].duplicated(), "cell_id"].head(10).tolist()
        problems.append(f"Duplicate cell_id values in GEE CSV, examples: {dup}")
    for c in REQUIRED_GEE_COLUMNS[1:]:
        vals = pd.to_numeric(gee[c], errors="coerce")
        if vals.isna().any():
            problems.append(f"Column {c} has {int(vals.isna().sum())} missing/non-numeric values")
    for c in ["tree_canopy_fraction", "grass_fraction", "water_fraction", "built_up_fraction"]:
        vals = pd.to_numeric(gee[c], errors="coerce")
        bad = ((vals < -1e-6) | (vals > 1 + 1e-6)).sum()
        if bad:
            problems.append(f"Column {c} has {int(bad)} values outside [0,1]")
    return problems


def derive_beta_greenery(gee: pd.DataFrame) -> pd.DataFrame:
    """Create beta greenery variables from Dynamic World + Sentinel-2 NDVI.

    Dynamic World tree fraction is often sparse in dense urban cells because only
    dominant tree pixels count as trees. NDVI captures mixed/linear vegetation
    better. For the forecast engine's `gvi_percent` input we therefore use a
    documented screening proxy that blends tree, grass and NDVI information.
    This is not a real street-view GVI.
    """
    out = gee.copy()
    tree = _clip01(out["tree_canopy_fraction"])
    grass = _clip01(out["grass_fraction"])
    water = _clip01(out["water_fraction"])
    built = _clip01(out["built_up_fraction"])
    ndvi = pd.to_numeric(out["ndvi_mean"], errors="coerce").clip(-1, 1)

    # NDVI normalisation chosen for tropical/subtropical urban areas:
    # <0.12 is very low vegetation; ~0.72+ is lush vegetation.
    ndvi_norm = ((ndvi - 0.12) / 0.60).clip(0, 1)

    # A conservative pedestrian greenery proxy. Tree canopy dominates where it
    # exists; NDVI/grass provide non-zero signal for mixed roadside vegetation.
    greenery_fraction_beta = np.maximum.reduce([
        tree.to_numpy(),
        (0.55 * grass).to_numpy(),
        (0.45 * ndvi_norm).to_numpy(),
    ])
    greenery_fraction_beta = pd.Series(greenery_fraction_beta, index=out.index).clip(0, 1)

    out["dynamic_world_tree_fraction"] = tree
    out["dynamic_world_grass_fraction"] = grass
    out["dynamic_world_water_fraction"] = water
    out["dynamic_world_built_up_fraction"] = built
    out["ndvi_norm_for_greenery_proxy"] = ndvi_norm
    out["greenery_fraction_beta"] = greenery_fraction_beta
    out["gvi_percent"] = (60.0 * greenery_fraction_beta).clip(0, 70)
    out["gvi_source"] = "v07_beta_proxy_from_DynamicWorld_tree_grass_and_Sentinel2_NDVI_not_streetview_GVI"
    return out


def recompute_morphology(df: pd.DataFrame, cell_size_m: float = 100.0) -> pd.DataFrame:
    """Recompute screening-level svf, shade_fraction and impervious_fraction."""
    out = df.copy()
    bd = pd.to_numeric(out.get("building_density", 0), errors="coerce").fillna(0).clip(0, 1)
    road = pd.to_numeric(out.get("road_fraction", 0), errors="coerce").fillna(0).clip(0, 1)
    h = pd.to_numeric(out.get("mean_building_height_m", 10), errors="coerce").fillna(10).clip(0, 80)
    tree = pd.to_numeric(out.get("tree_canopy_fraction", 0), errors="coerce").fillna(0).clip(0, 1)
    gfrac = pd.to_numeric(out.get("greenery_fraction_beta", tree), errors="coerce").fillna(tree).clip(0, 1)
    built_dw = pd.to_numeric(out.get("built_up_fraction", np.nan), errors="coerce")
    water_dw = pd.to_numeric(out.get("water_fraction", 0), errors="coerce").fillna(0).clip(0, 1)

    height_term = h / max(cell_size_m, 1)
    svf = 1.0 / (1.0 + 0.55 * height_term + 1.8 * bd)
    svf += 0.10 * road
    out["svf"] = np.clip(svf, 0.18, 0.98)

    # Shade proxy: buildings + height + greenery/tree contribute; roads reduce.
    shade = 0.08 + 0.55 * bd + 0.28 * np.clip(h / 40.0, 0, 1) + 0.25 * gfrac - 0.15 * road
    out["shade_fraction"] = np.clip(shade, 0.04, 0.90)

    # Impervious combines local vector features and Dynamic World built-up. Water
    # is removed where present so reservoirs/lakes do not become impervious.
    vector_imperv = (bd + road).clip(0, 1)
    if built_dw.notna().any():
        imperv = np.maximum(vector_imperv.to_numpy(), built_dw.fillna(0).clip(0, 1).to_numpy())
    else:
        imperv = vector_imperv.to_numpy()
    imperv = pd.Series(imperv, index=out.index)
    imperv = (imperv - 0.35 * gfrac - 0.75 * water_dw).clip(0, 1)
    out["impervious_fraction"] = imperv

    out["svf_source"] = "v07_beta_screening_proxy_from_building_density_GHSL_height_road_fraction"
    out["shade_fraction_source"] = "v07_beta_screening_proxy_from_building_density_GHSL_height_greenery_road"
    out["impervious_source"] = "v07_beta_proxy_from_vector_building_road_and_DynamicWorld_built_up_water"
    return out


def make_report(df: pd.DataFrame, gee: pd.DataFrame, unmatched_base: set[str], unmatched_gee: set[str], out_path: Path) -> None:
    lines: list[str] = []
    lines.append("# OpenHeat v0.7-beta GEE integration QA")
    lines.append("")
    lines.append(f"Base grid rows after merge: **{len(df)}**")
    lines.append(f"GEE rows: **{len(gee)}**")
    lines.append(f"Base cells missing from GEE: **{len(unmatched_base)}**")
    lines.append(f"GEE cells not in base grid: **{len(unmatched_gee)}**")
    lines.append("")
    for col in [
        "mean_building_height_m", "dynamic_world_tree_fraction", "dynamic_world_grass_fraction",
        "dynamic_world_water_fraction", "dynamic_world_built_up_fraction", "ndvi_mean",
        "gvi_percent", "svf", "shade_fraction", "impervious_fraction",
    ]:
        if col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce")
            lines.append(f"- `{col}`: missing={int(s.isna().sum())}, min={s.min():.3f}, mean={s.mean():.3f}, p50={s.median():.3f}, max={s.max():.3f}")
    lines.append("")
    lines.append("## Notes")
    lines.append("- `gvi_percent` is a v0.7-beta screening proxy derived from Dynamic World tree/grass and Sentinel-2 NDVI. It is **not** true street-view GVI.")
    lines.append("- `svf` and `shade_fraction` remain morphology proxies, not UMEP/SOLWEIG outputs.")
    lines.append("- Use this output as a real-grid forecast input, then upgrade SVF/shade/GVI in later versions.")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="data/grid/toa_payoh_grid_v07_features.csv", help="v0.7-alpha base grid feature CSV")
    ap.add_argument("--gee", default="data/raw/gee_height_vegetation_by_grid.csv", help="GEE export CSV")
    ap.add_argument("--out", default="data/grid/toa_payoh_grid_v07_features_beta_gee.csv", help="Output beta grid CSV")
    ap.add_argument("--report", default="outputs/v07_beta_gee_integration_QA_report.md", help="QA report path")
    ap.add_argument("--cell-size-m", type=float, default=100.0)
    args = ap.parse_args()

    base_path = Path(args.base)
    gee_path = Path(args.gee)
    if not base_path.exists():
        raise FileNotFoundError(f"Base grid feature CSV not found: {base_path}. Run v07_build_grid_features.py first.")
    if not gee_path.exists():
        raise FileNotFoundError(f"GEE CSV not found: {gee_path}. Put your GEE export in data/raw/ first.")

    base = pd.read_csv(base_path)
    gee = pd.read_csv(gee_path)
    problems = validate_gee(gee)
    if problems:
        raise ValueError("GEE CSV validation failed:\n" + "\n".join(f"- {p}" for p in problems))

    base_ids = set(base["cell_id"].astype(str))
    gee_ids = set(gee["cell_id"].astype(str))
    unmatched_base = base_ids - gee_ids
    unmatched_gee = gee_ids - base_ids
    if unmatched_base:
        print(f"[WARNING] {len(unmatched_base)} base cells are missing from GEE CSV. They will retain existing/proxy values where possible.")
    if unmatched_gee:
        print(f"[WARNING] {len(unmatched_gee)} GEE cells are not in the base grid and will be ignored.")

    gee2 = derive_beta_greenery(gee)
    keep = [
        "cell_id", "mean_building_height_m", "tree_canopy_fraction", "grass_fraction", "water_fraction",
        "built_up_fraction", "ndvi_mean", "dynamic_world_tree_fraction", "dynamic_world_grass_fraction",
        "dynamic_world_water_fraction", "dynamic_world_built_up_fraction", "ndvi_norm_for_greenery_proxy",
        "greenery_fraction_beta", "gvi_percent", "gvi_source",
    ]
    keep = [c for c in keep if c in gee2.columns]

    # Drop columns that will be replaced, preserving base vector features.
    replace_cols = [c for c in keep if c != "cell_id"] + [
        "svf", "shade_fraction", "impervious_fraction", "height_source", "tree_canopy_source",
        "svf_source", "shade_fraction_source", "impervious_source",
    ]
    base2 = base.drop(columns=[c for c in replace_cols if c in base.columns], errors="ignore")
    merged = base2.merge(gee2[keep], on="cell_id", how="left")

    # If some GEE values are missing, fall back to existing base values where available.
    if unmatched_base:
        for c in ["mean_building_height_m", "tree_canopy_fraction", "gvi_percent"]:
            if c in base.columns and c in merged.columns:
                merged[c] = merged[c].fillna(base[c])

    if "max_building_height_m" not in merged.columns:
        merged["max_building_height_m"] = pd.to_numeric(merged["mean_building_height_m"], errors="coerce").fillna(10) * 1.65
    merged["height_source"] = "GHSL_GHS_BUILT_H_2018_100m_from_GEE"
    merged["tree_canopy_source"] = "DynamicWorld_via_GEE"
    merged["ndvi_source"] = "Sentinel2_composite_via_GEE"

    merged = recompute_morphology(merged, cell_size_m=args.cell_size_m)
    merged["forecast_spatial_note"] = "Open-Meteo supplies background meteorology; v0.7-beta intra-neighbourhood variation uses vector features plus GEE GHSL/DynamicWorld/Sentinel-2 proxies."

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_path, index=False)
    make_report(merged, gee, unmatched_base, unmatched_gee, Path(args.report))
    print(f"[OK] Wrote beta grid features: {out_path}")
    print(f"[OK] Wrote QA report: {args.report}")
    print("[SUMMARY]")
    for col in ["mean_building_height_m", "tree_canopy_fraction", "ndvi_mean", "gvi_percent", "svf", "shade_fraction", "impervious_fraction"]:
        if col in merged.columns:
            s = pd.to_numeric(merged[col], errors="coerce")
            print(f"  {col}: min={s.min():.3f}, mean={s.mean():.3f}, max={s.max():.3f}")


if __name__ == "__main__":
    main()
