# B8.5-F3a Raster QA Status

Generated: 2026-05-27 03:37:00

## Status

`MICRO_BATCH_RASTER_QA_PASS`

## Branch

`codex/b85-f3a-raster-qa`

## Scope

Content sanity QA for the four local F3a micro-batch `Tmrt_average.tif` rasters only. QGIS/SOLWEIG were not executed; no raster, image, or large array outputs were written.

## Key Results

- Raster count opened: `4`
- Alignment status: `PASS`
- Per-run p90 range: `57.57-61.60 C`
- Base-vs-overhead delta: FD01 mean -0.663888 C (overhead_neutral); FD02 mean -0.598506 C (overhead_neutral)
- FD02-vs-FD01 contrast: base mean -2.762285 C, p90 -0.404498 C (plausible_forcing_difference); overhead_as_canopy mean -2.696902 C, p90 -0.382623 C (plausible_forcing_difference)
- Next recommended action: `F3b one-cell full slice`
- QGIS/SOLWEIG executed: `no`
- Raster outputs written: `no`

## Files Created / Modified

- `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/configs/v12/systemb_b85_f3a_raster_qa.yaml`
- `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/scripts/v12_b85_f3a_raster_qa.py`
- `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/scripts/v12_b85_run_f3a_raster_qa.py`
- `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/docs/v12/OpenHeat_SystemB_B8_5_F3a_raster_QA_CN.md`
- `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_raster_inventory.csv`
- `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_raster_stats.csv`
- `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_pairwise_delta_summary.csv`
- `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_forcing_day_contrast_summary.csv`
- `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_alignment_qa.csv`
- `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_sanity_checks.csv`
- `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_raster_qa_report.md`
- `C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/outputs/v12_surrogate/b8_5_f3a_raster_qa/B8_5_F3A_QA_STATUS.md`

## Commands To Verify

- `python -m compileall scripts/v12_b85_f3a_raster_qa.py scripts/v12_b85_run_f3a_raster_qa.py`
- `python scripts/v12_b85_run_f3a_raster_qa.py --config configs/v12/systemb_b85_f3a_raster_qa.yaml`
- Python mojibake check on `docs/v12/OpenHeat_SystemB_B8_5_F3a_raster_QA_CN.md`
- `git status --short -- .`
- forbidden-file check

## Safe To Commit

Only compact config, scripts, docs, CSV, and Markdown control artifacts listed above after review.

## Not Safe To Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, `data/solweig/`, `data/rasters/`, raw archives, patch zip packages, and large forecast CSV files.
