# B8.6f Feature Acquisition Specification

This specification is for a future B8.6g vector/compact feature acquisition
lane. It is not an AOI-wide prediction, B9 output, WBGT conversion, hazard or
risk score, observed-truth claim, causal feature-importance claim, raster
operation, QGIS/SOLWEIG operation, or System A/B coupling.

## Feature Names


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


## Definitions And Minimum Schemas

- `pedestrian-accessible shaded fraction`: produce `cell_id|ped_access_shade_frac|ped_access_shade_length_m|ped_access_denominator_m|feature_version`; priority `high`; addresses `neutral-false-promotion|anchor-underprediction|feature-distribution-shift`.
- `connected shade corridor / shade continuity`: produce `cell_id|shade_corridor_continuity_idx|max_connected_shade_length_m|gap_count|feature_version`; priority `high`; addresses `spatial-bin-out-of-domain|anchor-underprediction|sample-support-low`.
- `overhead geometry shape descriptors`: produce `cell_id|overhead_patch_count|overhead_mean_patch_area_m2|overhead_edge_density|feature_version`; priority `high`; addresses `feature-distribution-shift|target-role-mismatch`.
- `sunlit-hot-pocket area fraction`: produce `cell_id|sunlit_hot_pocket_proxy_frac|open_high_svf_low_shade_frac|proxy_method|feature_version`; priority `high`; addresses `neutral-false-promotion|target-role-mismatch|spatial-bin-out-of-domain`.
- `local boundary / edge context`: produce `cell_id|water_edge_contact_frac|park_edge_contact_frac|hardscape_edge_contact_frac|feature_version`; priority `medium`; addresses `east_south_neutral_false_promotion|feature-distribution-shift`.
- `neighbourhood-scale context`: produce `cell_id|neighbourhood_shade_mean|neighbourhood_overhead_frac|neighbourhood_open_frac|feature_version`; priority `medium`; addresses `spatial-bin-out-of-domain|sample-support-low`.
- `tree/building shadow interaction`: produce `cell_id|tree_building_overlap_proxy|tree_near_tall_building_frac|interaction_method|feature_version`; priority `high`; addresses `anchor-underprediction|feature-distribution-shift`.
- `canyon orientation / height roughness`: produce `cell_id|canyon_axis_orientation_deg|height_roughness_iqr_m|height_asymmetry_idx|feature_version`; priority `high`; addresses `anchor-underprediction|spatial-bin-out-of-domain`.
- `typology-specific geometry`: produce `cell_id|typology_geometry_class|typology_shade_interaction|typology_support_count|feature_version`; priority `medium`; addresses `target-role-mismatch|sample-support-low|feature-distribution-shift`.

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
