# Sprint B2 - N=24 System B Sample Design + SOLWEIG Manifest Preflight

## Status
PASS

## Scope
- sample design + manifest preflight only
- no SOLWEIG execution
- no QGIS
- no rasters
- no surrogate
- no hazard map
- no risk map
- no local WBGT
- no System A/B coupling

## Inputs inspected
- outputs/v12_systemb_target_robustness/systemb_target_robustness_report.md: rows=98
- outputs/v12_systemb_target_robustness/systemb_target_decision_matrix.csv: rows=11
- outputs/v12_systemb_target_robustness/normalized_tmrt_targets_long.csv: rows=80
- outputs/v12_systemb_target_robustness/normalized_modifier_targets_long.csv: rows=80
- outputs/v12_systemb_target_robustness/target_rank_correlation.csv: rows=210
- outputs/v12_systemb_target_robustness/target_topk_overlap.csv: rows=210
- outputs/v12_systemb_target_robustness/base_vs_overhead_sensitivity_summary.csv: rows=42
- outputs/v12_systemb_target_robustness/hour_stability_rank_correlation.csv: rows=140
- outputs/v12_systemb_target_robustness/hour_stability_consistent_cells.csv: rows=14
- outputs/v12_systemb_target_robustness/typology_interpretability_audit.csv: rows=16
- outputs/v12_solweig_typology_pilot/core8_base_summary/tmrt_cell_summary_long.csv: rows=40
- outputs/v12_solweig_typology_pilot/core8_base_summary/modifier_targets_long.csv: rows=40
- outputs/v12_solweig_typology_pilot/core8_base_summary/modifier_reference_table.csv: rows=5
- outputs/v12_solweig_typology_pilot/core8_overhead_summary/tmrt_cell_summary_long.csv: rows=40
- outputs/v12_solweig_typology_pilot/core8_overhead_summary/modifier_targets_long.csv: rows=40
- outputs/v12_solweig_typology_pilot/core8_overhead_summary/core8_base_vs_overhead_delta.csv: rows=40
- outputs/v12_solweig_typology_pilot/core8_overhead_summary/core8_base_vs_overhead_delta_by_cell.csv: rows=8
- outputs/v12_solweig_typology_pilot/wave1_base_summary/v12_solweig_typology_aggregation_report.md: rows=18
- outputs/v12_solweig_typology_pilot/overhead_smoke_summary/overhead_smoke_vs_base_h13.md: rows=17
- configs/v12/v12_solweig_core8_base_manifest.csv: rows=40
- configs/v12/v12_solweig_core8_overhead_manifest.csv: rows=40
- configs/v12/v12_solweig_overhead_smoke_h13_manifest.csv: rows=3
- configs/v12/v12_solweig_typology_config.example.json: rows=1
- data/grid/v12/solweig_typology_cell_candidates.csv: rows=12
- data/grid/v10/toa_payoh_grid_v10_features_overhead_sensitivity.csv: rows=986
- data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.csv: rows=986
- data/grid/v10/toa_payoh_grid_v10_umep_morphology_with_veg.csv: rows=986
- docs/v12/OpenHeat_SystemB_product_taxonomy_CN.md: rows=85
- docs/v12/OpenHeat_SystemB_target_robustness_protocol_CN.md: rows=68
- docs/v12/OpenHeat_modifier_target_spec_CN.md: rows=544
- docs/v12/OpenHeat_v12_SOLWEIG_typology_pilot_interim_findings_CN.md: rows=217
- docs/v10/V10_EPSILON_SOLWEIG_final_findings_report_CN.md: rows=1028

## B1 continuity
B1/B1.1/B1.2 conclusion is preserved: `tmrt_p90_c` is a provisional primary System B target candidate, not canonical. Companion metrics are required, including mean, p75, p95, max, delta p90, m_rad_pct, and future threshold-area metrics. N=24 validation is required.

## Candidate pool
Candidate pool rows: 986. Non-raster feature columns available include SVF, shade, building density, tree/GVI, grass, water, road, and overhead proxies where present.

## N=24 selected sample
Core 8 retained: 8. New/added cells: 13. Legacy diagnostics: 3. Alternates: 12.

Selected cells:
- TP_0059: open_paved_hardscape_parking_lot (core_continuity)
- TP_0326: stable_high_rise_residential_estate (core_continuity)
- TP_0366: school_gate_bus_stop_waiting_node (core_continuity)
- TP_0542: river_edge_shaded_walkway (core_continuity)
- TP_0565: school_gate_road_edge_hot_anchor (core_continuity)
- TP_0627: street_canyon_wall_adjacent_low_svf (core_continuity)
- TP_0835: grass_park_green_mixed (core_continuity)
- TP_0986: low_rise_residential_null_control (core_continuity)
- TP_0088: overhead_confounded_transport_deck (overhead_confounded_legacy_diagnostic)
- TP_0916: overhead_saturated (overhead_confounded_legacy_diagnostic)
- TP_0433: tree_shaded_reference (shaded_or_canopy_reference)
- TP_0857: hdb_canyon (street_canyon_wall_adjacent)
- TP_0828: wall_adjacent (street_canyon_wall_adjacent)
- TP_0802: near_water (covered_walkway_or_pedestrian_overhead)
- TP_0492: dense_shaded_low_svf (shaded_or_canopy_reference)
- TP_0037: other (street_canyon_wall_adjacent)
- TP_0058: water (water_edge_or_blue_green)
- TP_0409: civic_institutional (street_canyon_wall_adjacent)
- TP_0098: civic_institutional (covered_walkway_or_pedestrian_overhead)
- TP_0960: park_open_space (open_paved_hardscape)
- TP_0115: water (water_edge_or_blue_green)
- TP_0254: residential (street_canyon_wall_adjacent)
- TP_0675: civic_institutional (covered_walkway_or_pedestrian_overhead)
- TP_0154: park_open_space (street_canyon_wall_adjacent)

Alternates:
- TP_0831: replaces TP_0088; transport_overhead_or_viaduct
- TP_0803: replaces TP_0088; transport_overhead_or_viaduct
- TP_0859: replaces TP_0088; transport_overhead_or_viaduct
- TP_0887: replaces TP_0088; transport_overhead_or_viaduct
- TP_0945: replaces TP_0088; transport_overhead_or_viaduct
- TP_0431: replaces TP_0088; transport_overhead_or_viaduct
- TP_0460: replaces TP_0088; transport_overhead_or_viaduct
- TP_0572: replaces TP_0088; transport_overhead_or_viaduct
- TP_0888: replaces TP_0088; transport_overhead_or_viaduct
- TP_0746: replaces TP_0088; transport_overhead_or_viaduct
- TP_0860: replaces TP_0088; transport_overhead_or_viaduct
- TP_0944: replaces TP_0088; transport_overhead_or_viaduct

## Coverage
- confident_hot_anchor_continuity: 2
- core_continuity: 8
- covered_walkway_or_pedestrian_overhead: 14
- grass_or_open_park: 5
- max_extreme_probe: 6
- open_paved_hardscape: 5
- overhead_confounded_legacy_diagnostic: 2
- overhead_sensitivity_probe: 15
- p90_p95_disagreement_probe: 6
- pedestrian_relevance_probe: 2
- school_gate_bus_stop_waiting_node: 2
- shaded_or_canopy_reference: 5
- street_canyon_wall_adjacent: 12
- threshold_area_probe: 10
- transport_overhead_or_viaduct: 5
- water_edge_or_blue_green: 8

Required roles missing: none

## Why these cells
The N=24 design keeps Core 8 continuity while adding legacy overhead diagnostics, shaded/canopy references, exposed hardscape, low-SVF canyon/wall-adjacent cells, water/green contexts, pedestrian-sensitive waiting nodes, and probes for p90/p95/max disagreement. Threshold-area probe cells are included so future `pct_pixels_tmrt_ge_40/45/50/55` metrics can be evaluated after the next aggregation pass.

## SOLWEIG manifest preflight
Expected future main runs: 14 preflight checks over 240 manifest rows. Base rows = 120, overhead rows = 120, total rows = 240. The manifest uses future template strings only and marks raw outputs do_not_commit.

## Caveats
- design only
- N=24 still not full-domain validation
- no pedestrian-accessible mask unless present
- threshold-area metrics may require future aggregator changes
- no local WBGT
- no risk
- no System A/B coupling

## Next recommended action
1. Human review of N=24 design.

## Boundary confirmation
- no rasters touched
- no .tif touched
- no SOLWEIG rerun
- no QGIS
- no model training
- no surrogate
- no hazard map
- no risk map
- no local WBGT
- no System A/B coupling performed
- no commit/stage performed
