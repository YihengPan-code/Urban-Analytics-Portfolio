"""Write the explicit B8.6g feature schema.

Inputs:
    B8.6g config and hard-coded feature-family definitions derived from the
    B8.6f acquisition register/spec.
Outputs:
    b86g_feature_schema.csv.
Saved metrics:
    Feature name, family, type, units, source type, exact definition, null
    policy, proxy flag, production-candidate flag, diagnostic-only flag,
    leakage risk, claim boundary, and feature version. The schema contains no
    target-derived predictor, raster, QGIS/SOLWEIG, AOI-wide, B9, WBGT,
    hazard/risk, observed-truth, causal feature-importance, Tmrt-to-WBGT, or
    System A/B coupling claim.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86g_source_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, load_config, output_path, write_csv


@dataclass(frozen=True)
class FeatureSchemaResult:
    """Feature schema write result."""

    status: str
    features: int
    proxy_features: int


def row(
    name: str,
    family: str,
    dtype: str,
    units: str,
    source: str,
    definition: str,
    null_policy: str,
    proxy: bool,
    production: bool,
    diagnostic: bool,
    leakage: str = "low",
) -> dict[str, Any]:
    """Create one feature schema row."""
    return {
        "feature_name": name,
        "feature_family": family,
        "type": dtype,
        "units": units,
        "source_type": source,
        "exact_definition": definition,
        "null_policy": null_policy,
        "proxy_flag": proxy,
        "production_candidate": "yes" if production else "no",
        "diagnostic_only": "yes" if diagnostic else "no",
        "leakage_risk": leakage,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def build_schema(config: dict[str, Any]) -> pd.DataFrame:
    """Build the B8.6g feature schema rows."""
    version = str(config["output_feature_version"])
    rows = [
        row("ped_access_shade_frac", "pedestrian-accessible shaded fraction", "float", "fraction", "vector_network", "True pedestrian-accessible shaded length divided by pedestrian-accessible denominator length, reserved for future network overlay.", "null when no pedestrian network/vector denominator exists", False, True, False),
        row("ped_access_shade_length_m", "pedestrian-accessible shaded fraction", "float", "m", "vector_network", "True shaded pedestrian-accessible segment length within the cell.", "null when no pedestrian network/vector denominator exists", False, True, False),
        row("ped_access_denominator_m", "pedestrian-accessible shaded fraction", "float", "m", "vector_network", "True pedestrian-accessible denominator segment length within the cell.", "null when no pedestrian network/vector denominator exists", False, True, False),
        row("ped_access_shade_frac_proxy", "pedestrian-accessible shaded fraction", "float", "fraction", "compact_vector_derived", "max(pedestrian_shelter_fraction, covered walkway plus pedestrian bridge area divided by cell area).", "null if shelter/overhead compact summaries are missing", True, True, False, "medium_proxy"),
        row("ped_access_shade_length_m_proxy", "pedestrian-accessible shaded fraction", "float", "m", "compact_vector_derived", "covered walkway area divided by 3 m plus pedestrian bridge area divided by 4 m; not a network continuity measure.", "null if overhead area summaries are missing", True, False, True, "medium_proxy"),
        row("shade_corridor_continuity_idx", "connected shade corridor / shade continuity", "float", "index", "vector_network", "Connected shaded pedestrian-network length divided by total shaded candidate network length.", "null until a pedestrian shade network exists", False, True, False),
        row("max_connected_shade_length_m", "connected shade corridor / shade continuity", "float", "m", "vector_network", "Maximum connected shaded pedestrian-network component length in the cell/local context.", "null until a pedestrian shade network exists", False, True, False),
        row("shade_gap_count", "connected shade corridor / shade continuity", "float", "count", "vector_network", "Count of gaps between shaded pedestrian-network components.", "null until a pedestrian shade network exists", False, True, False),
        row("overhead_patch_count", "overhead geometry shape descriptors", "float", "count", "compact_vector_derived", "Vector-derived count of overhead structures intersecting the cell.", "0 if compact source reports zero overhead structures; null if source missing", False, True, False),
        row("overhead_total_area_m2", "overhead geometry shape descriptors", "float", "m2", "compact_vector_derived", "Vector-derived overhead structure area intersecting the cell.", "0 if compact source reports zero overhead area; null if source missing", False, True, False),
        row("overhead_mean_patch_area_m2", "overhead geometry shape descriptors", "float", "m2", "compact_vector_derived", "overhead_total_area_m2 divided by overhead_patch_count when count is positive.", "null when patch count is zero or missing", False, True, False),
        row("overhead_edge_density", "overhead geometry shape descriptors", "float", "m_per_m2", "vector_polygon", "Overhead polygon perimeter divided by cell area, reserved for future polygon geometry processing.", "null because perimeter is not available in compact source", False, True, False),
        row("overhead_total_area_proxy", "overhead geometry shape descriptors", "float", "m2", "compact_proxy", "overhead fraction times cell area when direct vector-derived area is missing.", "null when direct overhead area exists or fraction is missing", True, False, True, "medium_proxy"),
        row("sunlit_hot_pocket_proxy_frac", "sunlit-hot-pocket area fraction", "float", "fraction", "compact_proxy", "compact open fraction times compact SVF/open-sky times one minus compact shade fraction.", "null if open, SVF/open-sky, or shade columns are missing", True, True, False, "medium_proxy"),
        row("open_high_svf_low_shade_frac", "sunlit-hot-pocket area fraction", "float", "fraction", "compact_proxy", "same compact open-high-SVF-low-shade product used to derive sunlit_hot_pocket_proxy_frac.", "null if source columns are missing", True, True, False, "medium_proxy"),
        row("water_edge_contact_frac", "local boundary / edge context", "float", "fraction", "compact_proxy", "water fraction where present, otherwise inverse distance-to-water within 100 m clipped to [0, 1].", "null if water fraction and distance are missing", True, True, False, "medium_proxy"),
        row("park_edge_contact_frac", "local boundary / edge context", "float", "fraction", "compact_proxy", "grass/park fraction where present, otherwise inverse distance-to-park within 100 m clipped to [0, 1].", "null if green fraction and distance are missing", True, True, False, "medium_proxy"),
        row("hardscape_edge_contact_frac", "local boundary / edge context", "float", "fraction", "compact_proxy", "road, hardscape, or impervious compact fraction clipped to [0, 1].", "null if hardscape compact columns are missing", True, True, False, "medium_proxy"),
        row("neighbourhood_shade_mean", "neighbourhood-scale context", "float", "fraction", "compact_cell_context", "mean compact shade fraction among neighbouring cells within configured centroid radius.", "null if centroids or shade columns are missing", True, True, False, "low_context_no_target"),
        row("neighbourhood_overhead_frac", "neighbourhood-scale context", "float", "fraction", "compact_cell_context", "mean compact overhead fraction among neighbouring cells within configured centroid radius.", "null if centroids or overhead columns are missing", True, True, False, "low_context_no_target"),
        row("neighbourhood_open_frac", "neighbourhood-scale context", "float", "fraction", "compact_cell_context", "mean compact open fraction among neighbouring cells within configured centroid radius.", "null if centroids or open columns are missing", True, True, False, "low_context_no_target"),
        row("tree_building_overlap_proxy", "tree/building shadow interaction", "float", "fraction_product", "compact_proxy", "compact tree fraction times compact building-density proxy.", "null if tree or building-density columns are missing", True, True, False, "medium_proxy"),
        row("tree_near_tall_building_frac", "tree/building shadow interaction", "float", "fraction_product", "compact_proxy", "compact tree fraction times clipped compact tall-building-height proxy.", "null if tree or height columns are missing", True, True, False, "medium_proxy"),
        row("canyon_axis_orientation_deg", "canyon orientation / height roughness", "float", "degrees", "building_vector", "Dominant canyon/building axis orientation, reserved for future footprint geometry processing.", "null without building-footprint geometry engine/source", False, True, False),
        row("height_roughness_iqr_m", "canyon orientation / height roughness", "float", "m", "compact_height_proxy", "building p90 height minus p50 height, falling back to p90 minus mean height.", "null if height quantile/mean columns are missing", True, True, False, "medium_proxy"),
        row("height_asymmetry_idx", "canyon orientation / height roughness", "float", "ratio", "compact_height_proxy", "height_roughness_iqr_m divided by absolute p90 height plus epsilon.", "null if height roughness or p90 height is missing", True, True, False, "medium_proxy"),
        row("typology_geometry_class", "typology-specific geometry", "category", "class", "compact_typology_proxy", "typology label crossed with low/mid/high compact shade, overhead, open, and built-density bins.", "unknown bins used where source values are missing", True, True, False, "low_no_target"),
        row("typology_shade_interaction", "typology-specific geometry", "float", "fraction_delta", "compact_typology_proxy", "cell shade fraction minus candidate-universe median shade fraction for the same typology.", "null if shade or typology support is missing", True, True, False, "low_no_target"),
        row("typology_support_count", "typology-specific geometry", "integer", "count", "compact_typology_proxy", "count of candidate-universe cells with the same typology label.", "0 if typology is missing", True, False, True, "low_no_target"),
    ]
    schema = pd.DataFrame(rows)
    schema["feature_version"] = version
    return schema


def run(config_path: Path = DEFAULT_CONFIG) -> FeatureSchemaResult:
    """Write B8.6g feature schema."""
    config = load_config(config_path)
    schema = build_schema(config)
    write_csv(schema, output_path(config, "feature_schema_path"))
    return FeatureSchemaResult(
        status="B86G_FEATURE_SCHEMA_READY",
        features=len(schema),
        proxy_features=int(schema["proxy_flag"].astype(bool).sum()),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Write B8.6g feature schema.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
