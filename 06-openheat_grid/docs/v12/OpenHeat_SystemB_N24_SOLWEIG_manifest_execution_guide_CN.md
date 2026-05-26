# OpenHeat System B N24 SOLWEIG Manifest Execution Guide

This is a future execution guide, not execution evidence. Sprint B2 did not run QGIS or SOLWEIG.

## Future human execution outline
1. Review the N=24 selected cells and alternates.
2. In QGIS Python Console, prepare wall-height, wall-aspect, and SVF preprocessing inputs for the approved cells and scenarios.
3. Run the SOLWEIG loop from `configs/v12/v12_solweig_n24_run_matrix.csv` only after human approval.
4. Expect 240 main SOLWEIG runs: 24 cells x 2 scenarios x 5 hours.
5. Use resume / skip-completed behavior keyed by `run_id` and `expected_summary_row_key`.
6. Write failure logs for missing preprocess outputs, failed SOLWEIG runs, and incomplete summaries.
7. Aggregate Tmrt after execution to produce mean, p75, p90, p95, max, delta p90, m_rad_pct, and threshold-area metrics where available.

## Stop conditions before execution
- Any selected cell lacks human map QA.
- Any manifest path points to raw output intended for commit.
- Any required preprocessing output is missing.
- Any script would read existing rasters during this design sprint.
- Any output would imply local WBGT, risk, or System A/B coupling.

## Never commit
Raw SOLWEIG outputs, raster files, `.tif` / `.tiff` files, raw API dumps, `data/solweig/`, and `data/rasters/` must not be committed.
