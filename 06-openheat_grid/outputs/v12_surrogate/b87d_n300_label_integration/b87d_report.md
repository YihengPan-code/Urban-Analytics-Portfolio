# B87D N300 Label Integration Report

Generated: 2026-05-28 13:19:23

Status: `B87D_N300_LABEL_INTEGRATION_PASS`

## 1. B87C Full 150 Execution Summary

B87C full_150 execution is consumed from the completed local run log. Only `status=success` rows feed extraction; dry-run and skipped-completed rows are audit context only.

## 2. Tmrt Extraction Convention

Recovered convention: `F5_FULL_150X150_VALID_NON_NODATA_TMRT_AVERAGE_TIF_V1` / `full_tile_valid_non_nodata`. Final F5 labels came from `b85_f5_raster_stats.csv`, whose raster inventory shape is 150x150 and whose valid pixel count is 22500 for full 2 m tiles. B87D therefore uses finite non-nodata pixels over the full `Tmrt_average.tif` tile and does not crop to a 100 m focus mask.

## 3. Tmrt Stats Summary

- Stats rows: `3000`
- Saved stats: mean, median, p90, p95, max, valid/nodata counts, raster shape and CRS.

## 4. Pairwise Delta Construction

B87C pairwise labels are `overhead_as_canopy - base` by `cell_id x forcing_day_id x date x hour_sgt`. Negative values generally indicate lower simulated Tmrt under overhead-as-canopy, not WBGT reduction.

## 5. F5 Schema Alignment

F5 `delta_tmrt_p50_c` is carried as `delta_tmrt_median_c`; F5 `delta_tmrt_max_c` is derived from the final F5 cell-hour summary using the same overhead-minus-base formula. This is schema alignment, not retroactive recalibration.

## 6. N300 Integrated Label Summary

- N300 rows: `3000`
- N300 unique cells: `300`
- Old/new overlap count: `0`

## 7. QA And Blockers

Blockers: `none`.

## 8. Claim Boundaries

SOLWEIG Tmrt simulated radiative output only; delta is overhead_as_canopy - base; not observed truth, not WBGT, not AOI/B9 prediction, not hazard map, not risk map, and not causal evidence.
