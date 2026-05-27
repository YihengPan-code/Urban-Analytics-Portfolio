"""Create the B8.6f feature acquisition and engineering roadmap.

Inputs:
    B8.6e feature-gap register and B8.6f config.
Outputs:
    b86f_feature_acquisition_register.csv and
    b86f_feature_acquisition_spec.md.
Saved metrics:
    Feature-family priority, current availability, computability from compact
    tables or existing vector sources without raster I/O, expected benefit,
    failure modes addressed, implementation lane, minimum output schema, and
    caveats. This script does not read, open, copy, create, or write rasters;
    it does not run QGIS or SOLWEIG and does not create AOI-wide, B9, WBGT,
    hazard, risk, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86f_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    input_path,
    load_config,
    output_path,
    read_csv,
    write_csv,
    write_text,
)


@dataclass(frozen=True)
class FeaturePlanResult:
    """Feature acquisition plan result."""

    status: str
    feature_families: int
    high_priority: int


FEATURE_ROWS = [
    {
        "feature_family": "pedestrian-accessible shaded fraction",
        "source_candidate": "Existing walkway/shelter/tree/building vector layers plus compact shade columns.",
        "current_availability": "partial",
        "computable_from_current_compact_tables": "partially",
        "computable_from_existing_vector_without_raster": "yes",
        "requires_new_processing": "yes_vector_overlay_or_network_join",
        "expected_benefit": "high",
        "likely_failure_modes_addressed": "neutral-false-promotion|anchor-underprediction|feature-distribution-shift",
        "implementation_lane": "B8.6g_vector_compact_feature_acquisition",
        "minimum_output_schema": "cell_id|ped_access_shade_frac|ped_access_shade_length_m|ped_access_denominator_m|feature_version",
        "risk_caveat": "Must distinguish pedestrian-accessible shade from any-cell shade; no raster sampling in this lane.",
        "priority": "high",
    },
    {
        "feature_family": "connected shade corridor / shade continuity",
        "source_candidate": "Covered walkway, pedestrian bridge, tree canopy, and footpath graph/vector segments.",
        "current_availability": "not_available",
        "computable_from_current_compact_tables": "no",
        "computable_from_existing_vector_without_raster": "yes_if_network_vectors_available",
        "requires_new_processing": "yes_vector_network_processing",
        "expected_benefit": "high",
        "likely_failure_modes_addressed": "spatial-bin-out-of-domain|anchor-underprediction|sample-support-low",
        "implementation_lane": "B8.6g_vector_compact_feature_acquisition",
        "minimum_output_schema": "cell_id|shade_corridor_continuity_idx|max_connected_shade_length_m|gap_count|feature_version",
        "risk_caveat": "Continuity must not be inferred from coordinate proximity alone.",
        "priority": "high",
    },
    {
        "feature_family": "overhead geometry shape descriptors",
        "source_candidate": "Existing overhead vector footprints and compact overhead area fields.",
        "current_availability": "partial",
        "computable_from_current_compact_tables": "partially",
        "computable_from_existing_vector_without_raster": "yes",
        "requires_new_processing": "yes_vector_geometry_processing",
        "expected_benefit": "medium-high",
        "likely_failure_modes_addressed": "feature-distribution-shift|target-role-mismatch",
        "implementation_lane": "B8.6g_vector_compact_feature_acquisition",
        "minimum_output_schema": "cell_id|overhead_patch_count|overhead_mean_patch_area_m2|overhead_edge_density|feature_version",
        "risk_caveat": "Shape features are diagnostic predictors only, not causal feature importance.",
        "priority": "high",
    },
    {
        "feature_family": "sunlit-hot-pocket area fraction",
        "source_candidate": "Existing compact shade/SVF/open-sky summaries; vector-only proxy where feasible.",
        "current_availability": "partial",
        "computable_from_current_compact_tables": "yes_proxy_only",
        "computable_from_existing_vector_without_raster": "yes_proxy_only",
        "requires_new_processing": "yes_proxy_definition_review",
        "expected_benefit": "high",
        "likely_failure_modes_addressed": "neutral-false-promotion|target-role-mismatch|spatial-bin-out-of-domain",
        "implementation_lane": "B8.6g_vector_compact_feature_acquisition",
        "minimum_output_schema": "cell_id|sunlit_hot_pocket_proxy_frac|open_high_svf_low_shade_frac|proxy_method|feature_version",
        "risk_caveat": "Do not use raster shadow output or SOLWEIG output; proxy must remain compact/vector-only.",
        "priority": "high",
    },
    {
        "feature_family": "local boundary / edge context",
        "source_candidate": "Cell boundary adjacency to water, park, road, open paved, and high-rise contexts.",
        "current_availability": "partial",
        "computable_from_current_compact_tables": "partially",
        "computable_from_existing_vector_without_raster": "yes",
        "requires_new_processing": "yes_vector_adjacency",
        "expected_benefit": "medium",
        "likely_failure_modes_addressed": "east_south_neutral_false_promotion|feature-distribution-shift",
        "implementation_lane": "B8.6g_vector_compact_feature_acquisition",
        "minimum_output_schema": "cell_id|water_edge_contact_frac|park_edge_contact_frac|hardscape_edge_contact_frac|feature_version",
        "risk_caveat": "Edge context must not become exposure/vulnerability or risk scoring.",
        "priority": "medium",
    },
    {
        "feature_family": "neighbourhood-scale context",
        "source_candidate": "Vector summaries in cell buffers or compact neighbourhood tables.",
        "current_availability": "partial",
        "computable_from_current_compact_tables": "partially",
        "computable_from_existing_vector_without_raster": "yes",
        "requires_new_processing": "yes_vector_buffer_aggregation",
        "expected_benefit": "medium",
        "likely_failure_modes_addressed": "spatial-bin-out-of-domain|sample-support-low",
        "implementation_lane": "B8.7-N300-PRE_or_B8.6g",
        "minimum_output_schema": "cell_id|neighbourhood_shade_mean|neighbourhood_overhead_frac|neighbourhood_open_frac|feature_version",
        "risk_caveat": "Neighbourhood context is not an AOI-wide prediction.",
        "priority": "medium",
    },
    {
        "feature_family": "tree/building shadow interaction",
        "source_candidate": "Tree canopy, building footprint/height, and compact shade/SVF fields.",
        "current_availability": "partial",
        "computable_from_current_compact_tables": "yes_proxy_only",
        "computable_from_existing_vector_without_raster": "yes",
        "requires_new_processing": "yes_vector_interaction",
        "expected_benefit": "high",
        "likely_failure_modes_addressed": "anchor-underprediction|feature-distribution-shift",
        "implementation_lane": "B8.6g_vector_compact_feature_acquisition",
        "minimum_output_schema": "cell_id|tree_building_overlap_proxy|tree_near_tall_building_frac|interaction_method|feature_version",
        "risk_caveat": "Do not infer observed cooling; labels remain SOLWEIG-derived Tmrt deltas.",
        "priority": "high",
    },
    {
        "feature_family": "canyon orientation / height roughness",
        "source_candidate": "Building footprint and height vector summaries.",
        "current_availability": "partial",
        "computable_from_current_compact_tables": "partially",
        "computable_from_existing_vector_without_raster": "yes_if_height_vectors_available",
        "requires_new_processing": "yes_vector_geometry_processing",
        "expected_benefit": "medium-high",
        "likely_failure_modes_addressed": "anchor-underprediction|spatial-bin-out-of-domain",
        "implementation_lane": "B8.6g_vector_compact_feature_acquisition",
        "minimum_output_schema": "cell_id|canyon_axis_orientation_deg|height_roughness_iqr_m|height_asymmetry_idx|feature_version",
        "risk_caveat": "Orientation features are model diagnostics, not causal proof.",
        "priority": "high",
    },
    {
        "feature_family": "typology-specific geometry",
        "source_candidate": "Current typology labels plus vector geometry summaries stratified by typology.",
        "current_availability": "partial",
        "computable_from_current_compact_tables": "yes_for_basic_interactions",
        "computable_from_existing_vector_without_raster": "yes",
        "requires_new_processing": "yes_typology_stratified_feature_build",
        "expected_benefit": "medium",
        "likely_failure_modes_addressed": "target-role-mismatch|sample-support-low|feature-distribution-shift",
        "implementation_lane": "B8.6g_or_B8.7-N300-PRE",
        "minimum_output_schema": "cell_id|typology_geometry_class|typology_shade_interaction|typology_support_count|feature_version",
        "risk_caveat": "Do not let typology support counts replace formal holdout evidence.",
        "priority": "medium",
    },
]


def feature_register(config: dict[str, Any]) -> pd.DataFrame:
    """Create the B8.6f feature acquisition register."""
    existing = read_csv(input_path(config, "b86e_feature_gap_register_path"))
    current_map = dict(zip(existing["feature_family"].astype(str), existing["currently_available"].astype(str)))
    rows = []
    for row in FEATURE_ROWS:
        out = row.copy()
        out["b86e_current_availability"] = current_map.get(row["feature_family"], "")
        out["claim_boundary"] = CLAIM_BOUNDARY
        rows.append(out)
    return pd.DataFrame(rows)


def feature_spec_text(register: pd.DataFrame) -> str:
    """Build the Markdown feature acquisition specification."""
    feature_lines = []
    for row in register.itertuples(index=False):
        feature_lines.append(
            f"- `{row.feature_family}`: produce `{row.minimum_output_schema}`; "
            f"priority `{row.priority}`; addresses `{row.likely_failure_modes_addressed}`."
        )
    names = """
Proposed exact feature names:

- `ped_access_shade_frac`, `ped_access_shade_length_m`, `ped_access_denominator_m`
- `shade_corridor_continuity_idx`, `max_connected_shade_length_m`, `shade_gap_count`
- `overhead_patch_count`, `overhead_mean_patch_area_m2`, `overhead_edge_density`
- `sunlit_hot_pocket_proxy_frac`, `open_high_svf_low_shade_frac`
- `water_edge_contact_frac`, `park_edge_contact_frac`, `hardscape_edge_contact_frac`
- `neighbourhood_shade_mean`, `neighbourhood_overhead_frac`, `neighbourhood_open_frac`
- `tree_building_overlap_proxy`, `tree_near_tall_building_frac`
- `canyon_axis_orientation_deg`, `height_roughness_iqr_m`, `height_asymmetry_idx`
- `typology_geometry_class`, `typology_shade_interaction`, `typology_support_count`
"""
    return f"""# B8.6f Feature Acquisition Specification

This specification is for a future B8.6g vector/compact feature acquisition
lane. It is not an AOI-wide prediction, B9 output, WBGT conversion, hazard or
risk score, observed-truth claim, causal feature-importance claim, raster
operation, QGIS/SOLWEIG operation, or System A/B coupling.

## Feature Names

{names}

## Definitions And Minimum Schemas

{chr(10).join(feature_lines)}

## Required Inputs

- Current compact cell IDs and typology labels.
- Existing vector footprints or compact vector-derived tables for covered
  walkways, pedestrian bridges, tree canopy, building footprints/heights,
  water/park/road edges, and footpath/network segments where available.
- Existing B8.6d/B8.6e failure diagnostics for prioritising validation checks.

## Allowed Sources

- Compact CSV tables already present in the project.
- Existing vector or vector-derived compact tables that can be read without
  raster I/O and without launching QGIS or SOLWEIG.
- Hand-reviewed schema notes and deterministic feature definitions.

## Forbidden Sources

- Raster files, `.tif`, `.tiff`, `svfs.zip`, `data/solweig/`, raw SOLWEIG
  outputs, raw archive dumps, QGIS runners, SOLWEIG runs, AOI-wide prediction
  tables, local WBGT, hazard_score, risk_score, exposure/vulnerability scoring,
  observed-truth labels, and System A/B coupling outputs.

## Expected Output Schema

Every future feature table should include:

`cell_id`, one or more feature columns, `feature_version`, `source_summary`,
`processing_notes`, `claim_boundary`.

Each feature column must have a short definition, units where relevant, null
handling, and a compact validation summary. The lane should write a
machine-readable CSV plus a short Markdown summary.

## No-Raster / Vector-Only Options

- Use vector intersections, lengths, areas, adjacency, and network continuity
  where vector sources exist.
- Use current compact shade/SVF/open/overhead summaries only as proxies when
  the proxy limitation is named.
- Do not sample, convert, copy, or open raster files.

## Future Lane Prompt Outline

Ask Codex to run B8.6g vector/compact feature acquisition using this spec,
write compact feature tables and a schema audit, preserve all B8.6f claim
boundaries, and stop if a requested source would require raster, QGIS, SOLWEIG,
AOI-wide prediction, B9, WBGT, hazard/risk scoring, observed truth, or System
A/B coupling.
"""


def run(config_path: Path = DEFAULT_CONFIG) -> FeaturePlanResult:
    """Write the B8.6f feature acquisition register and spec."""
    config = load_config(config_path)
    register = feature_register(config)
    write_csv(register, output_path(config, "feature_acquisition_register"))
    write_text(feature_spec_text(register), output_path(config, "feature_acquisition_spec"))
    return FeaturePlanResult(
        status="B86F_FEATURE_ACQUISITION_PLAN_READY",
        feature_families=len(register),
        high_priority=int(register["priority"].astype(str).eq("high").sum()),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Create the B8.6f feature acquisition register and spec.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
