# B8.5-F4 Status

Generated: 2026-05-27 16:12:41

## Status

`F4_N24_DECISION_PASS`

## Branch

`codex/b85-f4-n24-decision-matrix`

## Scope

N24 stability decision matrix, target-card gate, N150 readiness recommendation, and surrogate role decision from compact F3c evidence only.

## Key Results

- Core-hour stability headline: h12/h13/h15/h16 are core-stable across FD01/FD02 for delta_tmrt_p90_c ranking.
- h10 caveat headline: h10 is weaker and remains caveated; it is not anchor evidence.
- Robust priority cell count: `5`
- Neutral-boundary cell count: `9`
- Unstable-review cell count: `6`
- N150 recommendation: `ALLOW_N150_CONTROLLED_EXECUTION_AFTER_PRECHECK`
- Surrogate role decision: `SURROGATE_PROTOCOL_READY_N24_STRESS_VALIDATION_NO_TRAINING_IN_F4`
- B9 status: `BLOCKED_F4_IS_NOT_B9`
- QGIS/SOLWEIG executed by Codex: `no`
- Raster read/write/copy in F4: `no`

## Evidence Notes

- F3c status is N24_STABILITY_REVIEW_READY.
- Postrun validation is 480/480 PASS.
- Cell-hour and pairwise compact summaries have the expected N24/F3c shape.
- F3c raster/alignment QA compact evidence is PASS; F4 did not open rasters.

## Blockers

- none

## Files Created / Modified

- `configs/v12/systemb_b85_f4_n24_decision.yaml`
- `scripts/v12_b85_f4_n24_decision_matrix.py`
- `scripts/v12_b85_run_f4_n24_decision_matrix.py`
- `docs/v12/OpenHeat_SystemB_B8_5_F4_N24_decision_matrix_CN.md`
- `outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_hourly_stability_summary.csv`
- `outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_cell_stability_scorecard.csv`
- `outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_robust_priority_cells.csv`
- `outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_neutral_boundary_cells.csv`
- `outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_unstable_priority_cells.csv`
- `outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_target_card_delta_tmrt_p90.md`
- `outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_n150_readiness_recommendation.md`
- `outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_surrogate_role_decision.md`
- `outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_geometry_uncertainty_register.csv`
- `outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_decision_matrix.csv`
- `outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_report.md`
- `outputs/v12_surrogate/b8_5_f4_n24_decision/B8_5_F4_STATUS.md`

## Commands To Verify

- `python -m compileall scripts/v12_b85_f4_n24_decision_matrix.py scripts/v12_b85_run_f4_n24_decision_matrix.py`
- `python scripts/v12_b85_run_f4_n24_decision_matrix.py --config configs/v12/systemb_b85_f4_n24_decision.yaml`
- Python mojibake check on `docs/v12/OpenHeat_SystemB_B8_5_F4_N24_decision_matrix_CN.md`
- `git status --short -- .`
- forbidden-file check

## Safe To Commit

Only compact config, scripts, docs, CSV, and Markdown artifacts listed above after review.

## Not Safe To Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, `data/solweig/`, `data/rasters/`, raw archives, patch zip packages, and large forecast CSV files.
