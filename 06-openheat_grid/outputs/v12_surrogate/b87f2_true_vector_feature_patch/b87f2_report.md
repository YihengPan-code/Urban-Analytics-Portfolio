# B87F2 True-Vector Feature Patch Report

Generated: 2026-05-28 15:06:41

Status: `B87F2_FEATURE_PATCH_PARTIAL_NO_AOI`

## 1. Why B87F2 Was Run

B87F showed that tuning alone did not supersede the B87E extra-trees candidate. B87F2 tests whether compact local true-vector/proxy features can improve transfer and ranking before any AOI preflight is considered.

## 2. Sources Found And Missing

Found sources: `building_canyon, compact_grid_feature, overhead_geometry, pedestrian_network, tree_building_interaction, water_park_road_edge`. Missing or unresolved sources: `connected_shade_corridor, tree_building_interaction`. See `b87f2_source_inventory.csv`, `b87f2_source_readiness_matrix.csv`, and `b87f2_feature_gap_resolution_matrix.csv`.

## 3. New Features Built

B87F2 built centroid-buffer features for overhead/covered-walkway geometry, local OSM-derived pedestrian-network proxies, building-vector morphology, water-edge proxies, and compact tree-building/overhead/pedestrian/water interactions. Where true tree/canopy or connected shade-corridor sources were missing, features are explicitly marked as proxies.

## 4. Metrics After Patch

Patched matrix shape: `3000 x 468`. Best GroupKFold: `b87f2_pruned_best_effort / extra_trees MAE=0.137744`. Best old-to-new: `b87f2_pruned_best_effort / extra_trees MAE=0.201257`. Best rank Spearman: `0.800468`.

## 5. Direct Comparison To B87E/B87F

Improvement summary: `group_mae_gain=0.012632; old_to_new_gain=0.012647; rank_gain=0.031247`. See `b87f2_prior_b87e_b87f_comparison.csv` and `b87f2_feature_gain_attribution.csv`.

## 6. Transfer And Rank

Transfer diagnostics are in `b87f2_transfer_generalization_matrix.csv`; rank/top-k diagnostics are in `b87f2_rank_topk_matrix.csv`. These are prioritisation diagnostics only, not hazard or risk claims.

## 7. Error Strata

Error strata after the patch are in `b87f2_error_strata_after_patch.csv` for the selected candidate.

## 8. AOI Preflight Gate

AOI gate: `BLOCKED_SOURCE_GAPS_REMAIN`. No AOI/B9 output was created. Connected shade corridor, pedestrian-network completeness, and tree/canopy-building source gaps remain blocking unless the gate table says otherwise.

## 9. Stop-Or-Continue Recommendation

Stop-or-continue: `CONTINUE_FEATURE_ACQUISITION`. Recommended next lane: `STOP_MODEL_TUNING_OR_EXTERNAL_TRUE_VECTOR_ACQUISITION`.

## 10. Claim Boundaries

- No observed truth claim.
- No WBGT conversion.
- No AOI-wide prediction or B9 output.
- No hazard/risk/exposure/vulnerability output.
- No causal feature-importance claim.
- This remains a surrogate/emulator of SOLWEIG simulated Tmrt deltas.
