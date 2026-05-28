# B87E Status

Generated: 2026-05-28 13:19:37

Status: `B87E_SURROGATE_BENCHMARK_PASS_NO_PROMOTION`

## Key Results

- Feature matrix shape: `3000 x 377`
- Main/supporting split count: `12`
- Best GroupKFold model by MAE: `extra_trees` (`0.150376`)
- Best old-to-new MAE model: `random_forest` (`0.218676`)
- Best GroupKFold rank Spearman: `0.749701`
- Promotion decision: `B87E_EXTRA_TREES_REMAINS_CANDIDATE`
- Recommended next lane: `B87F_surrogate_patch_stronger_features_before_any_AOI_preflight`
- Blockers: `none`

## Claim Boundary

Surrogate/emulator of SOLWEIG-derived delta Tmrt/Tmrt features only; not observed truth, not WBGT calibration, not AOI/B9 inference, not hazard or risk mapping, not exposure/vulnerability output, and not causal feature importance.
