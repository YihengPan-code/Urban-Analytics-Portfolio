"""Build B8.6g vector-derived compact feature family tables.

Inputs:
    B8.6g config, N150/N300 cell sets, candidate universe, n150 sampling
    matrix, and existing vector-derived compact overhead summaries where
    available.
Outputs:
    b86g_pedestrian_shade_features.csv,
    b86g_shade_corridor_features.csv,
    b86g_overhead_geometry_features.csv, and
    b86g_edge_context_features.csv.
Saved metrics:
    Pedestrian-accessible shade proxy availability, explicit shade-corridor
    non-availability when no pedestrian network graph exists, vector-derived
    overhead area/count descriptors, and compact boundary/edge context proxies.
    No raster, QGIS, SOLWEIG, AOI-wide, B9, WBGT, hazard/risk, observed-truth,
    causal feature-importance, Tmrt-to-WBGT, or System A/B coupling output is
    created.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86g_cell_geometry import load_cell_sets, load_compact_base
from v12_b86g_source_inventory import DEFAULT_CONFIG, load_config, output_path, read_csv, repo_path, write_csv


@dataclass(frozen=True)
class VectorFeatureResult:
    """Vector-derived compact feature build result."""

    status: str
    rows: int
    computed_families: int


KNOWN_OVERHEAD_TABLES = [
    "outputs/v10_overhead_qa/v10_overhead_per_cell.csv",
    "outputs/v09_gamma_qa/v09_overhead_structures_per_cell.csv",
]


def numeric(frame: pd.DataFrame, column: str, default: float = math.nan) -> pd.Series:
    """Return a numeric column or a default-filled series."""
    if column in frame.columns:
        return pd.to_numeric(frame[column], errors="coerce")
    return pd.Series(default, index=frame.index, dtype="float64")


def first_numeric(frame: pd.DataFrame, columns: list[str], default: float = math.nan) -> pd.Series:
    """Coalesce numeric columns in priority order."""
    result = pd.Series(default, index=frame.index, dtype="float64")
    for column in columns:
        if column in frame.columns:
            values = pd.to_numeric(frame[column], errors="coerce")
            result = result.where(result.notna(), values)
    return result


def clip01(series: pd.Series) -> pd.Series:
    """Clip a numeric series to [0, 1]."""
    return pd.to_numeric(series, errors="coerce").clip(lower=0.0, upper=1.0)


def target_cells_base(config: dict[str, Any]) -> pd.DataFrame:
    """Load compact base rows for the N150/N300 union."""
    n150_cells, n300_cells = load_cell_sets(config)
    wanted = pd.DataFrame({"cell_id": sorted(set(n150_cells).union(n300_cells))})
    base = wanted.merge(load_compact_base(config), on="cell_id", how="left")
    return merge_known_overhead(base)


def merge_known_overhead(base: pd.DataFrame) -> pd.DataFrame:
    """Merge preferred vector-derived overhead summaries if present."""
    out = base.copy()
    for table_path in KNOWN_OVERHEAD_TABLES:
        resolved = repo_path(table_path)
        if not resolved.exists():
            continue
        table = read_csv(resolved).drop_duplicates("cell_id", keep="first")
        rename_map = {
            column: f"ohsrc__{column}"
            for column in table.columns
            if column != "cell_id" and column in out.columns
        }
        table = table.rename(columns=rename_map)
        out = out.merge(table, on="cell_id", how="left")
    return out


def build_pedestrian_shade_features(config: dict[str, Any]) -> pd.DataFrame:
    """Build pedestrian-accessible shade proxy features from vector-derived compact summaries."""
    base = target_cells_base(config)
    feature_version = str(config["output_feature_version"])
    cell_area = first_numeric(base, ["cell_area_m2", "ohsrc__cell_area_m2"], 10000.0).replace(0, np.nan)
    covered_area = first_numeric(
        base,
        [
            "overhead_area_covered_walkway_m2",
            "ohsrc__overhead_area_covered_walkway_m2",
            "cu__overhead_area_covered_walkway_m2",
        ],
    ).fillna(0.0)
    bridge_area = first_numeric(
        base,
        [
            "overhead_area_pedestrian_bridge_m2",
            "ohsrc__overhead_area_pedestrian_bridge_m2",
            "cu__overhead_area_pedestrian_bridge_m2",
        ],
    ).fillna(0.0)
    shelter_fraction = first_numeric(
        base,
        ["pedestrian_shelter_fraction", "ohsrc__pedestrian_shelter_fraction", "cu__pedestrian_shelter_fraction"],
    )
    walkway_fraction = clip01((covered_area + bridge_area) / cell_area)
    proxy = pd.concat([shelter_fraction, walkway_fraction], axis=1).max(axis=1, skipna=True)
    proxy = clip01(proxy)
    has_proxy = proxy.notna()
    # Length is explicitly a proxy from area/type-width assumptions, not a network denominator.
    length_proxy = (covered_area / 3.0) + (bridge_area / 4.0)
    length_proxy = length_proxy.where((covered_area + bridge_area) > 0)
    out = pd.DataFrame(
        {
            "cell_id": base["cell_id"].astype(str),
            "ped_access_shade_frac": np.nan,
            "ped_access_shade_length_m": np.nan,
            "ped_access_denominator_m": np.nan,
            "ped_access_shade_frac_proxy": proxy,
            "ped_access_shade_length_m_proxy": length_proxy,
            "ped_access_source_status": np.where(has_proxy, "COMPACT_VECTOR_DERIVED_PROXY", "NOT_AVAILABLE"),
            "proxy_method": np.where(
                has_proxy,
                "max(pedestrian_shelter_fraction, covered_walkway_or_bridge_area / cell_area); length proxy uses 3m/4m type widths",
                "REQUIRES_PEDESTRIAN_NETWORK_OR_COVERED_WALKWAY_SOURCE",
            ),
            "feature_version": feature_version,
        }
    )
    return out


def build_shade_corridor_features(config: dict[str, Any]) -> pd.DataFrame:
    """Write explicit NOT_AVAILABLE shade-corridor rows without inferring network continuity."""
    base = target_cells_base(config)
    feature_version = str(config["output_feature_version"])
    return pd.DataFrame(
        {
            "cell_id": base["cell_id"].astype(str),
            "shade_corridor_continuity_idx": np.nan,
            "max_connected_shade_length_m": np.nan,
            "shade_gap_count": np.nan,
            "shade_corridor_source_status": "NOT_AVAILABLE_REQUIRES_PEDESTRIAN_SHADE_NETWORK",
            "feature_version": feature_version,
        }
    )


def build_overhead_geometry_features(config: dict[str, Any]) -> pd.DataFrame:
    """Build overhead geometry descriptors from vector-derived per-cell compact summaries."""
    base = target_cells_base(config)
    feature_version = str(config["output_feature_version"])
    cell_area = first_numeric(base, ["cell_area_m2", "ohsrc__cell_area_m2"], 10000.0)
    patch_count = first_numeric(base, ["n_overhead_features", "ohsrc__n_overhead_features", "cu__n_overhead_features"])
    covered = first_numeric(base, ["overhead_area_covered_walkway_m2", "ohsrc__overhead_area_covered_walkway_m2", "cu__overhead_area_covered_walkway_m2"]).fillna(0.0)
    elevated_rail = first_numeric(base, ["overhead_area_elevated_rail_m2", "ohsrc__overhead_area_elevated_rail_m2", "cu__overhead_area_elevated_rail_m2"]).fillna(0.0)
    elevated_road = first_numeric(base, ["overhead_area_elevated_road_m2", "ohsrc__overhead_area_elevated_road_m2", "cu__overhead_area_elevated_road_m2"]).fillna(0.0)
    pedestrian_bridge = first_numeric(base, ["overhead_area_pedestrian_bridge_m2", "ohsrc__overhead_area_pedestrian_bridge_m2", "cu__overhead_area_pedestrian_bridge_m2"]).fillna(0.0)
    viaduct = first_numeric(base, ["overhead_area_viaduct_m2", "ohsrc__overhead_area_viaduct_m2", "cu__overhead_area_viaduct_m2"]).fillna(0.0)
    total_area = first_numeric(base, ["overhead_area_total_m2", "ohsrc__overhead_area_total_m2", "cu__overhead_area_total_m2"])
    total_area = total_area.where(total_area.notna(), covered + elevated_rail + elevated_road + pedestrian_bridge + viaduct)
    overhead_fraction = first_numeric(
        base,
        ["overhead_fraction_total", "ohsrc__overhead_fraction_total", "cu__overhead_fraction_total", "overhead_fraction"],
    )
    total_area_proxy = (overhead_fraction * cell_area).where(total_area.isna() & overhead_fraction.notna())
    total_area = total_area.where(total_area.notna(), total_area_proxy)
    patch_count = patch_count.where(patch_count.notna(), np.where(total_area.fillna(0.0).gt(0), 1.0, 0.0))
    mean_patch_area = total_area / patch_count.replace(0, np.nan)
    has_area = total_area.notna()
    out = pd.DataFrame(
        {
            "cell_id": base["cell_id"].astype(str),
            "overhead_patch_count": patch_count,
            "overhead_total_area_m2": total_area,
            "overhead_mean_patch_area_m2": mean_patch_area,
            "overhead_edge_density": np.nan,
            "overhead_total_area_proxy": total_area_proxy,
            "overhead_shape_source_status": np.where(
                has_area,
                "COMPACT_VECTOR_DERIVED_NO_PERIMETER",
                "NOT_AVAILABLE",
            ),
            "feature_version": feature_version,
        }
    )
    return out


def build_edge_context_features(config: dict[str, Any]) -> pd.DataFrame:
    """Build local boundary/edge compact proxy features."""
    base = target_cells_base(config)
    feature_version = str(config["output_feature_version"])
    water_fraction = first_numeric(base, ["water_fraction", "dynamic_world_water_fraction", "cu__water_fraction", "cu__dynamic_world_water_fraction"])
    distance_to_water = first_numeric(base, ["distance_to_water", "water_distance_m", "cu__distance_to_water", "cu__water_distance_m"])
    water_contact = water_fraction.where(water_fraction.notna(), (1.0 - (distance_to_water / 100.0)).clip(lower=0.0, upper=1.0))
    distance_to_park = first_numeric(base, ["distance_to_park", "park_distance_m", "large_park_distance_m", "cu__distance_to_park", "cu__park_distance_m"])
    grass_fraction = first_numeric(base, ["grass_fraction", "dynamic_world_grass_fraction", "cu__grass_fraction", "cu__dynamic_world_grass_fraction"])
    park_contact = grass_fraction.where(grass_fraction.notna(), (1.0 - (distance_to_park / 100.0)).clip(lower=0.0, upper=1.0))
    hardscape = first_numeric(
        base,
        [
            "road_fraction",
            "road_or_hardscape_fraction",
            "impervious_fraction_vector_component",
            "impervious_fraction",
            "cu__road_fraction",
            "cu__impervious_fraction_vector_component",
        ],
    )
    has_any = water_contact.notna() | park_contact.notna() | hardscape.notna()
    return pd.DataFrame(
        {
            "cell_id": base["cell_id"].astype(str),
            "water_edge_contact_frac": clip01(water_contact),
            "park_edge_contact_frac": clip01(park_contact),
            "hardscape_edge_contact_frac": clip01(hardscape),
            "boundary_edge_source_status": np.where(has_any, "COMPACT_PROXY_ONLY", "NOT_AVAILABLE"),
            "feature_version": feature_version,
        }
    )


def run(config_path: Path = DEFAULT_CONFIG) -> VectorFeatureResult:
    """Run vector-derived compact B8.6g feature builders."""
    config = load_config(config_path)
    pedestrian = build_pedestrian_shade_features(config)
    corridor = build_shade_corridor_features(config)
    overhead = build_overhead_geometry_features(config)
    edge = build_edge_context_features(config)
    write_csv(pedestrian, output_path(config, "pedestrian_shade_features_path"))
    write_csv(corridor, output_path(config, "shade_corridor_features_path"))
    write_csv(overhead, output_path(config, "overhead_geometry_features_path"))
    write_csv(edge, output_path(config, "edge_context_features_path"))
    computed = int(pedestrian["ped_access_shade_frac_proxy"].notna().mean() >= 0.8)
    computed += int(overhead["overhead_total_area_m2"].notna().mean() >= 0.8)
    computed += int(edge[["water_edge_contact_frac", "park_edge_contact_frac", "hardscape_edge_contact_frac"]].notna().any(axis=1).mean() >= 0.8)
    status = "B86G_VECTOR_DERIVED_FEATURES_READY" if computed else "B86G_VECTOR_DERIVED_FEATURES_NOT_AVAILABLE"
    return VectorFeatureResult(status=status, rows=len(pedestrian), computed_families=computed)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build B8.6g vector-derived compact features.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
