"""Build B8.6g compact proxy feature family tables.

Inputs:
    B8.6g config, N150/N300 cell sets, v12 candidate universe, and n150
    sampling feature matrix.
Outputs:
    b86g_hot_pocket_proxy_features.csv,
    b86g_neighbourhood_context_features.csv,
    b86g_tree_building_interaction_features.csv,
    b86g_canyon_orientation_features.csv, and
    b86g_typology_geometry_features.csv.
Saved metrics:
    Compact sunlit-hot-pocket proxies, centroid-distance neighbourhood context,
    tree/building interaction proxies, limited height roughness descriptors,
    and typology-stratified geometry descriptors. These are feature tables for
    future diagnostic retest only; they create no raster, QGIS, SOLWEIG,
    AOI-wide, B9, WBGT, hazard/risk, observed-truth, causal feature-importance,
    Tmrt-to-WBGT, or System A/B coupling output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86g_cell_geometry import load_compact_base
from v12_b86g_source_inventory import DEFAULT_CONFIG, load_config, output_path, write_csv
from v12_b86g_vector_feature_builders import clip01, first_numeric, target_cells_base


@dataclass(frozen=True)
class CompactFeatureResult:
    """Compact feature build result."""

    status: str
    rows: int
    computed_families: int


def build_hot_pocket_proxy_features(config: dict[str, Any]) -> pd.DataFrame:
    """Build compact sunlit-hot-pocket proxy features."""
    base = target_cells_base(config)
    feature_version = str(config["output_feature_version"])
    open_frac = first_numeric(base, ["open_pixel_fraction_v10", "open_pixel_fraction", "cu__open_pixel_fraction_v10", "cu__open_pixel_fraction"])
    svf = first_numeric(base, ["svf", "svf_or_open_sky", "svf_umep_mean_open_v10", "cu__svf_umep_mean_open_v10", "cu__svf"])
    shade = first_numeric(base, ["shade_fraction", "shade_fraction_base_v10", "shade_fraction_umep_10_16_open_v10", "cu__shade_fraction_umep_10_16_open_v10"])
    low_shade = 1.0 - shade
    open_high_svf_low_shade = clip01(open_frac) * clip01(svf) * clip01(low_shade)
    has_proxy = open_high_svf_low_shade.notna()
    return pd.DataFrame(
        {
            "cell_id": base["cell_id"].astype(str),
            "sunlit_hot_pocket_proxy_frac": clip01(open_high_svf_low_shade),
            "open_high_svf_low_shade_frac": clip01(open_high_svf_low_shade),
            "proxy_method": np.where(
                has_proxy,
                "compact open_pixel_fraction * compact svf/open_sky * (1 - compact shade_fraction)",
                "REQUIRES_COMPACT_OPEN_SVF_SHADE_COLUMNS",
            ),
            "feature_version": feature_version,
        }
    )


def build_neighbourhood_context_features(config: dict[str, Any]) -> pd.DataFrame:
    """Build neighbourhood-scale context from compact cell centroids."""
    targets = target_cells_base(config)
    universe = load_compact_base(config)
    feature_version = str(config["output_feature_version"])
    radius = float(config.get("neighbourhood_context_radius_m", 250))
    nearest_k = int(config.get("nearest_k_fallback", 8))
    for frame in (targets, universe):
        frame["centroid_x"] = pd.to_numeric(frame.get("centroid_x"), errors="coerce")
        frame["centroid_y"] = pd.to_numeric(frame.get("centroid_y"), errors="coerce")
    universe_values = pd.DataFrame(
        {
            "cell_id": universe["cell_id"].astype(str),
            "x": universe["centroid_x"],
            "y": universe["centroid_y"],
            "shade": first_numeric(universe, ["shade_fraction", "shade_fraction_base_v10", "cu__shade_fraction"]),
            "overhead": first_numeric(universe, ["overhead_fraction_total", "overhead_fraction", "cu__overhead_fraction_total"]),
            "open": first_numeric(universe, ["open_pixel_fraction_v10", "open_pixel_fraction", "cu__open_pixel_fraction_v10"]),
        }
    )
    rows: list[dict[str, Any]] = []
    xy_all = universe_values[["x", "y"]].to_numpy(dtype=float)
    for _, target in targets.iterrows():
        x = pd.to_numeric(pd.Series([target.get("centroid_x")]), errors="coerce").iloc[0]
        y = pd.to_numeric(pd.Series([target.get("centroid_y")]), errors="coerce").iloc[0]
        if pd.isna(x) or pd.isna(y) or np.isnan(xy_all).any(axis=1).all():
            subset = universe_values.iloc[0:0]
            status = "BLOCKED_GEOMETRY"
        else:
            distances = np.sqrt((xy_all[:, 0] - float(x)) ** 2 + (xy_all[:, 1] - float(y)) ** 2)
            mask = (distances <= radius) & (universe_values["cell_id"].to_numpy() != str(target["cell_id"]))
            if mask.sum() == 0:
                order = np.argsort(distances)
                keep = [idx for idx in order if universe_values.iloc[idx]["cell_id"] != str(target["cell_id"])][:nearest_k]
                subset = universe_values.iloc[keep]
                status = "CENTROID_NEAREST_K_FALLBACK"
            else:
                subset = universe_values.loc[mask]
                status = "CENTROID_RADIUS_CONTEXT"
        rows.append(
            {
                "cell_id": str(target["cell_id"]),
                "neighbourhood_shade_mean": subset["shade"].mean(skipna=True),
                "neighbourhood_overhead_frac": subset["overhead"].mean(skipna=True),
                "neighbourhood_open_frac": subset["open"].mean(skipna=True),
                "neighbourhood_context_radius_m": radius,
                "neighbourhood_context_source_status": status,
                "feature_version": feature_version,
            }
        )
    return pd.DataFrame(rows)


def build_tree_building_interaction_features(config: dict[str, Any]) -> pd.DataFrame:
    """Build compact tree/building interaction proxy features."""
    base = target_cells_base(config)
    feature_version = str(config["output_feature_version"])
    tree = first_numeric(
        base,
        [
            "tree_canopy_fraction",
            "dynamic_world_tree_fraction",
            "tree_or_gvi_fraction",
            "cu__tree_canopy_fraction",
            "cu__dynamic_world_tree_fraction",
        ],
    )
    building_density = first_numeric(base, ["building_density", "building_pixel_fraction_v10", "cu__building_density", "cu__building_pixel_fraction_v10"])
    height = first_numeric(
        base,
        [
            "dsm_building_height_p90_m_v10",
            "building_height_p90",
            "max_building_height_m",
            "cu__dsm_building_height_p90_m_v10",
            "cu__v10_building_height_p90_m",
        ],
    )
    height_norm = (height / 60.0).clip(lower=0.0, upper=1.0)
    overlap_proxy = clip01(tree) * clip01(building_density)
    near_tall_proxy = clip01(tree) * height_norm
    has_proxy = overlap_proxy.notna() | near_tall_proxy.notna()
    return pd.DataFrame(
        {
            "cell_id": base["cell_id"].astype(str),
            "tree_building_overlap_proxy": overlap_proxy,
            "tree_near_tall_building_frac": near_tall_proxy,
            "interaction_method": np.where(
                has_proxy,
                "compact tree fraction times compact building density/height proxy",
                "REQUIRES_TREE_CANOPY_AND_BUILDING_HEIGHT_OR_FOOTPRINT_SOURCE",
            ),
            "feature_version": feature_version,
        }
    )


def build_canyon_orientation_features(config: dict[str, Any]) -> pd.DataFrame:
    """Build limited compact height roughness features; do not invent canyon axis."""
    base = target_cells_base(config)
    feature_version = str(config["output_feature_version"])
    p90 = first_numeric(base, ["dsm_building_height_p90_m_v10", "building_height_p90", "cu__dsm_building_height_p90_m_v10", "cu__v10_building_height_p90_m"])
    p50 = first_numeric(base, ["dsm_building_height_p50_m_v10", "cu__dsm_building_height_p50_m_v10", "cu__v10_building_height_p50_m"])
    mean_height = first_numeric(base, ["dsm_building_height_mean_m_v10", "mean_building_height", "mean_building_height_m", "cu__dsm_building_height_mean_m_v10"])
    roughness = p90 - p50
    roughness = roughness.where(roughness.notna(), p90 - mean_height)
    asymmetry = roughness / (p90.abs() + 0.000001)
    has_height = roughness.notna() | asymmetry.notna()
    return pd.DataFrame(
        {
            "cell_id": base["cell_id"].astype(str),
            "canyon_axis_orientation_deg": np.nan,
            "height_roughness_iqr_m": roughness,
            "height_asymmetry_idx": asymmetry,
            "canyon_source_status": np.where(
                has_height,
                "LIMITED_COMPACT_HEIGHT_PROXY_NO_AXIS",
                "NOT_AVAILABLE_REQUIRES_BUILDING_FOOTPRINT_HEIGHT_VECTOR",
            ),
            "feature_version": feature_version,
        }
    )


def classify_bin(values: pd.Series, low: float, high: float, labels: tuple[str, str, str]) -> pd.Series:
    """Classify numeric values into three compact bins."""
    numeric = pd.to_numeric(values, errors="coerce")
    out = pd.Series("unknown", index=values.index, dtype="object")
    out = out.where(~numeric.lt(low), labels[0])
    out = out.where(~(numeric.ge(low) & numeric.lt(high)), labels[1])
    out = out.where(~numeric.ge(high), labels[2])
    return out


def build_typology_geometry_features(config: dict[str, Any]) -> pd.DataFrame:
    """Build typology-specific compact geometry descriptors."""
    base = target_cells_base(config)
    universe = load_compact_base(config)
    feature_version = str(config["output_feature_version"])
    if "typology_label" not in base.columns and "typology" in base.columns:
        base["typology_label"] = base["typology"]
    if "typology_label" not in universe.columns and "typology" in universe.columns:
        universe["typology_label"] = universe["typology"]
    typology = base.get("typology_label", pd.Series("", index=base.index)).fillna("unknown").astype(str)
    universe_typology = universe.get("typology_label", pd.Series("", index=universe.index)).fillna("unknown").astype(str)
    support = universe_typology.value_counts().to_dict()
    shade = first_numeric(base, ["shade_fraction", "shade_fraction_base_v10", "cu__shade_fraction"])
    overhead = first_numeric(base, ["overhead_fraction_total", "overhead_fraction", "cu__overhead_fraction_total"])
    open_frac = first_numeric(base, ["open_pixel_fraction_v10", "open_pixel_fraction", "cu__open_pixel_fraction_v10"])
    building_density = first_numeric(base, ["building_density", "building_pixel_fraction_v10", "cu__building_density"])
    universe_shade = first_numeric(universe, ["shade_fraction", "shade_fraction_base_v10"])
    typology_median_shade = pd.DataFrame({"typology_label": universe_typology, "shade": universe_shade}).groupby("typology_label")["shade"].median()
    median_lookup = typology.map(typology_median_shade.to_dict())
    shade_interaction = shade - median_lookup
    classes = (
        typology
        + "|shade_"
        + classify_bin(shade, 0.25, 0.6, ("low", "mid", "high"))
        + "|overhead_"
        + classify_bin(overhead, 0.02, 0.12, ("low", "mid", "high"))
        + "|open_"
        + classify_bin(open_frac, 0.35, 0.7, ("low", "mid", "high"))
        + "|built_"
        + classify_bin(building_density, 0.15, 0.45, ("low", "mid", "high"))
    )
    return pd.DataFrame(
        {
            "cell_id": base["cell_id"].astype(str),
            "typology_geometry_class": classes,
            "typology_shade_interaction": shade_interaction,
            "typology_support_count": typology.map(support).fillna(0).astype(int),
            "feature_version": feature_version,
        }
    )


def run(config_path: Path = DEFAULT_CONFIG) -> CompactFeatureResult:
    """Run compact proxy B8.6g feature builders."""
    config = load_config(config_path)
    hot = build_hot_pocket_proxy_features(config)
    neighbourhood = build_neighbourhood_context_features(config)
    tree_building = build_tree_building_interaction_features(config)
    canyon = build_canyon_orientation_features(config)
    typology = build_typology_geometry_features(config)
    write_csv(hot, output_path(config, "hot_pocket_proxy_features_path"))
    write_csv(neighbourhood, output_path(config, "neighbourhood_context_features_path"))
    write_csv(tree_building, output_path(config, "tree_building_interaction_features_path"))
    write_csv(canyon, output_path(config, "canyon_orientation_features_path"))
    write_csv(typology, output_path(config, "typology_geometry_features_path"))
    computed = int(hot["sunlit_hot_pocket_proxy_frac"].notna().mean() >= 0.8)
    computed += int(neighbourhood["neighbourhood_shade_mean"].notna().mean() >= 0.8)
    computed += int(tree_building[["tree_building_overlap_proxy", "tree_near_tall_building_frac"]].notna().any(axis=1).mean() >= 0.8)
    computed += int(canyon[["height_roughness_iqr_m", "height_asymmetry_idx"]].notna().any(axis=1).mean() >= 0.8)
    computed += int(typology["typology_geometry_class"].notna().mean() >= 0.8)
    status = "B86G_COMPACT_FEATURES_READY" if computed else "B86G_COMPACT_FEATURES_NOT_AVAILABLE"
    return CompactFeatureResult(status=status, rows=len(hot), computed_families=computed)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build B8.6g compact proxy features.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
