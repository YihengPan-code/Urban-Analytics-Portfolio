# B8.7 N300 Manual QA Guide

This guide supports human review of the B8.6f N300 v2 candidate design after
B8.6g2. It is not an execution package, not a SOLWEIG manifest, and not a QGIS
runner.

## QA Inputs

- Candidate checklist: `outputs/v12_surrogate/b8_7_n300_pre/b87_n300_manual_qa_checklist.csv`
- Candidate rows: 150
- High-priority QA rows: 114
- Non-keep recommended actions: 142
- Source-review flags: connected_shade_corridor, pedestrian_network, tree_building_interaction, water_park_road_hardscape_edge

## Inspect Top Priority Candidates

Start with rows where `qa_priority=high`, then inspect rows where
`recommended_action` is `needs_source_before_execution`, `review`, or
`replace_candidate`. Confirm the candidate is absent from current N150 labels,
the role rationale is still sensible, and sparse-feature-space cases are
intentional rather than accidental outliers.

## Check Role Balance

Use the role, spatial, typology, anchor, neutral, sparse, and control audit CSVs
in the same output folder. Treat exact role quotas as fixed. Treat west_south,
TP_0037, TP_0433, neutral-group diversity, park_open_space/commercial
undercoverage, and residential/transport concentration as manual-review items.

## Check Connected Shade Corridor Source

Do not infer corridor continuity from centroid distance, nearest-cell distance,
or generic shade fraction. A valid future source must be pedestrian/covered
walkway/shade-network line or polygon geometry, or an equivalent vector-derived
compact connectivity table whose source is explicit.

## What Not To Do

- Do not run QGIS.
- Do not run SOLWEIG.
- Do not read, copy, create, or write raster files.
- Do not create an N300 execution manifest.
- Do not create AOI-wide prediction or B9 outputs.
- Do not create local WBGT, hazard_score, risk_score, exposure/vulnerability
  score, observed-truth, causal feature-importance, Tmrt-to-WBGT conversion, or
  System A/B coupling outputs.
