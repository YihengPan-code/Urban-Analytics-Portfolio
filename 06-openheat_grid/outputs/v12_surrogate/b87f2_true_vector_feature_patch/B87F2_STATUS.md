# B87F2 Status

Generated: 2026-05-28 15:06:41

Status: `B87F2_FEATURE_PATCH_PARTIAL_NO_AOI`

## Key Results

- Sources found: `building_canyon, compact_grid_feature, overhead_geometry, pedestrian_network, tree_building_interaction, water_park_road_edge`
- Sources missing: `connected_shade_corridor, tree_building_interaction`
- Patched feature matrix shape: `3000 x 468`
- Best GroupKFold: `b87f2_pruned_best_effort / extra_trees MAE=0.137744`
- Best old-to-new: `b87f2_pruned_best_effort / extra_trees MAE=0.201257`
- Best rank Spearman: `0.800468`
- Improvement over B87F: `group_mae_gain=0.012632; old_to_new_gain=0.012647; rank_gain=0.031247`
- Promotion decision: `NO_AOI_PREFLIGHT_SOURCE_GAPS_REMAIN`
- AOI gate: `BLOCKED_SOURCE_GAPS_REMAIN`
- Stop-or-continue: `CONTINUE_FEATURE_ACQUISITION`
- Recommended next lane: `STOP_MODEL_TUNING_OR_EXTERNAL_TRUE_VECTOR_ACQUISITION`
- Main blockers: `connected_shade_corridor, tree_building_interaction`
- QGIS/SOLWEIG executed by Codex: `no`
- Raster read/write/copy/move: `no`
- AOI/B9/WBGT/risk output: `no`

## Claim Boundary

Surrogate/emulator of SOLWEIG simulated Tmrt deltas only; not observed truth, not WBGT, not AOI/B9 inference, not hazard or risk mapping, not exposure/vulnerability output, and not causal feature-importance evidence.
