# B8.3 System B Surrogate Model-Card Decision Report

Generated: 2026-05-26 22:02:12

## Decision

- Candidate model: `extra_trees`.
- Candidate for internal model-card review: yes.
- Approved for final AOI-wide inference: no.
- Recommended next gate: B8.5-F0 N24 x 2-3 forcing days.
- Optional hardening: B8.3b if reviewers request report or checklist tightening.

## Purpose Boundary

- Surrogate/emulator for SOLWEIG-derived local radiative modifier labels.
- Not observed WBGT calibration, not local 100m WBGT, not a risk map, and not a final AOI inference product.

## Inputs And Feature Contract

- N150 label-feature matrix rows: 1500; cells: 150; scenarios: base, overhead_as_canopy; hours: 10, 12, 13, 15, 16.
- Headline physical-core features: 115.
- Spatial diagnostic columns available but excluded from headline features: 4.
- Prohibited nonphysical/social token hits in headline features: 0.
- Target-leakage token hits in headline features: 0.
- Coordinate headline features: 0.

## B8.2 Primary Evidence

- `cell_grouped_holdout`: candidate `extra_trees` MAE=0.940, Spearman=0.723, featureless MAE improvement=1.908, cell top-10 overlap=0.400; best by MAE=`extra_trees`.
- `spatial_holdout`: candidate `extra_trees` MAE=0.989, Spearman=0.728, featureless MAE improvement=1.858, cell top-10 overlap=0.500; best by MAE=`extra_trees`.
- `feature_bin_holdout`: candidate `extra_trees` MAE=2.230, Spearman=0.663, featureless MAE improvement=1.862, cell top-10 overlap=0.458; best by MAE=`extra_trees`.
- `hour_holdout`: candidate `extra_trees` MAE=0.759, Spearman=0.963, featureless MAE improvement=2.067, cell top-10 overlap=0.827; best by MAE=`random_forest`.
- `scenario_holdout`: candidate `extra_trees` MAE=0.736, Spearman=0.895, featureless MAE improvement=2.089, cell top-10 overlap=0.833; best by MAE=`random_forest`.

Required best-by-MAE checks: cell_grouped_holdout=extra_trees, spatial_holdout=extra_trees.
Mean cell/spatial Spearman for `delta_tmrt_p90_c`: 0.726.
Mean cell-level top-10% overlap for `delta_tmrt_p90_c` across cell/spatial holdouts: 0.444.

## Secondary Target

`tmrt_p90_c` performance is weaker and remains secondary. Absolute Tmrt is not the main B8 product; the current model-card decision centers on `delta_tmrt_p90_c`.

## Promotion Gate Summary

- Gate counts: FAIL=1, NOT_TESTED=1, PARTIAL=3, PASS=7.
- Gate checklist: `outputs/v12_surrogate/b8_model_card/promotion_gate_checklist.csv`.
- Split-family decision matrix: `outputs/v12_surrogate/b8_model_card/split_family_decision_matrix.csv`.

## Blockers Before B9

- Multi-forcing stability is not tested.
- Feature-bin / typology extrapolation remains partial evidence.
- Top-k prioritisation is diagnostic rather than final promotion evidence.
- No full AOI-wide inference readiness is established.

## Next Steps

- Run B8.5-F0 N24 x 2-3 forcing days if the lane moves toward stability evidence.
- Use B8.3b only if reviewers require a harder model-card review packet.
- Defer B9 full AOI inference until multi-forcing and model-card gates accept it.
