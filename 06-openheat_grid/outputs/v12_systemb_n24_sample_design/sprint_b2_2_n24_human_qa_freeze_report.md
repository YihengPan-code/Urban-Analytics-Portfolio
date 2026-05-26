# Sprint B2.2 - N24 Human QA Replacement / Selection Freeze

## Status
PASS

## Scope
- apply human QA replacements only
- no SOLWEIG
- no QGIS
- no rasters
- no .tif
- no surrogate
- no hazard/risk/local WBGT
- no System A/B coupling

## Human QA rule
The human QA was a quick map sanity check, not full semantic validation. The goal was to remove clearly unsuitable cells before SOLWEIG execution. No AMBER tier is used. Cells are either KEEP or REPLACE.

## Replacements applied
- TP_0916 -> TP_0575: Human QA replacement. TP_0916 remains an optional v10-epsilon legacy overhead-saturated diagnostic note only and is not in the frozen N24 run matrix.
- TP_0828 -> TP_0301: Human QA replacement.
- TP_0802 -> TP_0773: Human QA replacement.
- TP_0058 -> TP_0141: TP_0058 is almost pure river/water surface. TP_0141 is a better water-edge / blue-green context cell: roughly 30% river and 70% land/grass.
- TP_0675 -> TP_0676: Human QA replacement.

## Frozen N24 selected cells
- TP_0059
- TP_0326
- TP_0366
- TP_0542
- TP_0565
- TP_0627
- TP_0835
- TP_0986
- TP_0088
- TP_0575
- TP_0433
- TP_0857
- TP_0301
- TP_0773
- TP_0492
- TP_0037
- TP_0141
- TP_0409
- TP_0098
- TP_0960
- TP_0115
- TP_0254
- TP_0676
- TP_0154

## Coverage after replacement
- core_continuity: 8 (minimum 8)
- confident_hot_anchor_continuity: 2 (minimum 2)
- overhead_confounded_legacy_diagnostic: 1 (minimum 1)
- shaded_or_canopy_reference: 5 (minimum 2)
- open_paved_hardscape: 5 (minimum 2)
- street_canyon_wall_adjacent: 15 (minimum 2)
- covered_walkway_or_pedestrian_overhead: 14 (minimum 2)
- transport_overhead_or_viaduct: 4 (minimum 2)
- water_edge_or_blue_green: 7 (minimum 2)
- grass_or_open_park: 6 (minimum 2)
- school_gate_bus_stop_waiting_node: 2 (minimum 2)
- p90_p95_disagreement_probe: 6 (minimum 3)
- max_extreme_probe: 6 (minimum 1)
- threshold_area_probe: 10 (minimum 3)
- overhead_sensitivity_probe: 15 (minimum 1)
- pedestrian_relevance_probe: 2 (minimum 2)

Coverage warnings: none.
Coverage delta is written to `n24_b2_2_coverage_delta_vs_b2.csv`.

## Manifest after replacement
- base rows = 120
- overhead rows = 120
- total rows = 240
- no duplicate run_id = true
- no forbidden paths created

## Next recommended action
B3 full N24 SOLWEIG execution using the frozen B2.2 N24 run matrix. Run with resume / skip-completed / failure log / catastrophic-failure stop. No additional manual QA or B3-A smoke is required unless the execution script or QGIS/UMEP setup has changed.

## Boundary confirmation
- no rasters touched
- no .tif touched
- no QGIS
- no SOLWEIG
- no API calls
- no model training
- no surrogate
- no risk map
- no local WBGT
- no System A/B coupling
- no commit/stage
