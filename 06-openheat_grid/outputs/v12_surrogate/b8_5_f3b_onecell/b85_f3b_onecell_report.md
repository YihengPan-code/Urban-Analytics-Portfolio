# B8.5-F3b One-Cell Full-Slice Report

Generated: 2026-05-27 04:00:32

## Decision

- Status: `ONECELL_SLICE_EXECUTED_PASS`
- Raster QA status: `PASS`
- Raster count opened: `20/20`
- Alignment status: `PASS`
- Next action: `Full 480 may be reviewed only after claim-boundary review.`

## Read/Write Boundary

Codex/Python did not run QGIS/SOLWEIG. Raster QA reads local `Tmrt_average.tif` contents only after a successful human-run postrun validator. It writes no raster, image, GeoTIFF, PNG, clipped raster, or large array output. It does not copy/open `svfs.zip`.

## Raster Inventory

| run_id | forcing_day_id | hour_sgt | scenario | exists | file_size_bytes | crs | shape | opened_for_qa |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h10 | FD01_high_shortwave_hot_20260507 | 10 | base | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h10 | FD01_high_shortwave_hot_20260507 | 10 | overhead_as_canopy | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h12 | FD01_high_shortwave_hot_20260507 | 12 | base | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h12 | FD01_high_shortwave_hot_20260507 | 12 | overhead_as_canopy | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h13 | FD01_high_shortwave_hot_20260507 | 13 | base | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h13 | FD01_high_shortwave_hot_20260507 | 13 | overhead_as_canopy | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h15 | FD01_high_shortwave_hot_20260507 | 15 | base | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h15 | FD01_high_shortwave_hot_20260507 | 15 | overhead_as_canopy | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h16 | FD01_high_shortwave_hot_20260507 | 16 | base | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h16 | FD01_high_shortwave_hot_20260507 | 16 | overhead_as_canopy | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h10 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 10 | base | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h10 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 10 | overhead_as_canopy | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h12 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 12 | base | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h12 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 12 | overhead_as_canopy | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 13 | base | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h13 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 13 | overhead_as_canopy | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h15 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 15 | base | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h15 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 15 | overhead_as_canopy | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h16 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 16 | base | yes | 90658 | EPSG:3414 | 150x150 | yes |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h16 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 16 | overhead_as_canopy | yes | 90658 | EPSG:3414 | 150x150 | yes |

## Per-Raster Tmrt Stats

| run_id | valid_pixel_count | nodata_fraction | mean_c | p50_c | p90_c | p95_c | max_c | sanity_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h10 | 22500 | 0.000000 | 37.907881 | 34.145142 | 45.335340 | 46.096210 | 46.574692 | PASS |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h10 | 22500 | 0.000000 | 37.555015 | 33.950687 | 44.895851 | 45.601213 | 46.552807 | PASS |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h12 | 22500 | 0.000000 | 50.555146 | 58.243296 | 61.744261 | 62.092192 | 62.319798 | PASS |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h12 | 22500 | 0.000000 | 49.886746 | 57.722231 | 61.596094 | 61.877173 | 62.308121 | PASS |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h13 | 22500 | 0.000000 | 50.766133 | 57.573914 | 61.598778 | 62.174397 | 62.579208 | PASS |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h13 | 22500 | 0.000000 | 50.102245 | 57.132648 | 61.245582 | 61.816008 | 62.564804 | PASS |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h15 | 22500 | 0.000000 | 47.501209 | 52.264091 | 59.555224 | 60.227086 | 60.808533 | PASS |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h15 | 22500 | 0.000000 | 46.888578 | 41.186857 | 59.084558 | 59.810430 | 60.807812 | PASS |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h16 | 22500 | 0.000000 | 41.085257 | 36.815649 | 50.467068 | 51.216184 | 51.817322 | PASS |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h16 | 22500 | 0.000000 | 40.666514 | 36.461889 | 49.993913 | 50.753836 | 51.814468 | PASS |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h10 | 22500 | 0.000000 | 27.123008 | 27.332534 | 28.081336 | 28.508116 | 29.860762 | PASS |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h10 | 22500 | 0.000000 | 27.087382 | 27.329103 | 27.957441 | 28.281956 | 29.860762 | PASS |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h12 | 22500 | 0.000000 | 43.372208 | 47.262140 | 51.947747 | 52.861736 | 53.459007 | PASS |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h12 | 22500 | 0.000000 | 42.901416 | 46.773626 | 51.416779 | 52.274622 | 53.434177 | PASS |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13 | 22500 | 0.000000 | 48.003849 | 53.093161 | 58.075171 | 58.936028 | 59.546646 | PASS |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h13 | 22500 | 0.000000 | 47.405343 | 52.669868 | 57.567973 | 58.391335 | 59.527508 | PASS |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h15 | 22500 | 0.000000 | 37.146793 | 38.512045 | 42.953761 | 43.761915 | 44.370232 | PASS |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h15 | 22500 | 0.000000 | 36.854940 | 34.388357 | 42.484601 | 43.261231 | 44.361141 | PASS |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h16 | 22500 | 0.000000 | 38.338900 | 34.674313 | 46.330681 | 47.057508 | 47.637039 | PASS |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h16 | 22500 | 0.000000 | 37.982971 | 34.382612 | 45.872292 | 46.605883 | 47.632957 | PASS |

## Hourly Profile

| forcing_day_id | scenario | hour_sgt | mean_c | p50_c | p90_c | p95_c | max_c |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FD01_high_shortwave_hot_20260507 | base | 10 | 37.907881 | 34.145142 | 45.335340 | 46.096210 | 46.574692 |
| FD01_high_shortwave_hot_20260507 | base | 12 | 50.555146 | 58.243296 | 61.744261 | 62.092192 | 62.319798 |
| FD01_high_shortwave_hot_20260507 | base | 13 | 50.766133 | 57.573914 | 61.598778 | 62.174397 | 62.579208 |
| FD01_high_shortwave_hot_20260507 | base | 15 | 47.501209 | 52.264091 | 59.555224 | 60.227086 | 60.808533 |
| FD01_high_shortwave_hot_20260507 | base | 16 | 41.085257 | 36.815649 | 50.467068 | 51.216184 | 51.817322 |
| FD01_high_shortwave_hot_20260507 | overhead_as_canopy | 10 | 37.555015 | 33.950687 | 44.895851 | 45.601213 | 46.552807 |
| FD01_high_shortwave_hot_20260507 | overhead_as_canopy | 12 | 49.886746 | 57.722231 | 61.596094 | 61.877173 | 62.308121 |
| FD01_high_shortwave_hot_20260507 | overhead_as_canopy | 13 | 50.102245 | 57.132648 | 61.245582 | 61.816008 | 62.564804 |
| FD01_high_shortwave_hot_20260507 | overhead_as_canopy | 15 | 46.888578 | 41.186857 | 59.084558 | 59.810430 | 60.807812 |
| FD01_high_shortwave_hot_20260507 | overhead_as_canopy | 16 | 40.666514 | 36.461889 | 49.993913 | 50.753836 | 51.814468 |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | base | 10 | 27.123008 | 27.332534 | 28.081336 | 28.508116 | 29.860762 |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | base | 12 | 43.372208 | 47.262140 | 51.947747 | 52.861736 | 53.459007 |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | base | 13 | 48.003849 | 53.093161 | 58.075171 | 58.936028 | 59.546646 |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | base | 15 | 37.146793 | 38.512045 | 42.953761 | 43.761915 | 44.370232 |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | base | 16 | 38.338900 | 34.674313 | 46.330681 | 47.057508 | 47.637039 |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | overhead_as_canopy | 10 | 27.087382 | 27.329103 | 27.957441 | 28.281956 | 29.860762 |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | overhead_as_canopy | 12 | 42.901416 | 46.773626 | 51.416779 | 52.274622 | 53.434177 |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | overhead_as_canopy | 13 | 47.405343 | 52.669868 | 57.567973 | 58.391335 | 59.527508 |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | overhead_as_canopy | 15 | 36.854940 | 34.388357 | 42.484601 | 43.261231 | 44.361141 |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | overhead_as_canopy | 16 | 37.982971 | 34.382612 | 45.872292 | 46.605883 | 47.632957 |

## Base-vs-Overhead Delta By Hour

Delta is `overhead_as_canopy - base`; this is a Tmrt sensitivity check, not WBGT.

| forcing_day_id | hour_sgt | mean_delta_c | p50_delta_c | p90_delta_c | p95_delta_c | pct_pixels_delta_lt_minus_1 | pct_pixels_delta_gt_1 | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FD01_high_shortwave_hot_20260507 | 10 | -0.352866 | 0.000000 | 0.000000 | 0.000000 | 2.782222 | 0.000000 | overhead_neutral |
| FD01_high_shortwave_hot_20260507 | 12 | -0.668400 | 0.000000 | 0.000000 | 0.000000 | 2.835556 | 0.000000 | overhead_neutral |
| FD01_high_shortwave_hot_20260507 | 13 | -0.663888 | 0.000000 | 0.000000 | 0.000000 | 2.728889 | 0.000000 | overhead_neutral |
| FD01_high_shortwave_hot_20260507 | 15 | -0.612630 | 0.000000 | 0.000000 | 0.000000 | 2.715556 | 0.000000 | overhead_neutral |
| FD01_high_shortwave_hot_20260507 | 16 | -0.418743 | 0.000000 | 0.000000 | 0.000000 | 2.551111 | 0.000000 | overhead_neutral |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | 10 | -0.035626 | 0.000000 | 0.000000 | 0.032559 | 2.133333 | 0.044444 | overhead_neutral |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | 12 | -0.470792 | 0.000000 | 0.000000 | 0.000000 | 2.688889 | 0.000000 | overhead_neutral |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | 13 | -0.598506 | 0.000000 | 0.000000 | 0.000000 | 2.720000 | 0.000000 | overhead_neutral |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | 15 | -0.291853 | 0.000000 | 0.000000 | 0.000000 | 2.662222 | 0.000000 | overhead_neutral |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | 16 | -0.355929 | 0.000000 | 0.000000 | 0.000000 | 2.533333 | 0.000000 | overhead_neutral |

## Forcing-Day Contrast By Hour

Contrast is `FD02 - FD01` for the same scenario/hour.

| scenario | hour_sgt | mean_difference_c | p50_difference_c | p90_difference_c | p95_difference_c | qualitative_status |
| --- | --- | --- | --- | --- | --- | --- |
| base | 10 | -10.784873 | -8.230028 | -5.386356 | -5.176759 | plausible_forcing_difference |
| base | 12 | -7.182938 | -9.319586 | -2.034658 | -1.787340 | plausible_forcing_difference |
| base | 13 | -2.762285 | -3.460007 | -0.404498 | -0.287707 | plausible_forcing_difference |
| base | 15 | -10.354415 | -13.660334 | -3.386505 | -3.183327 | plausible_forcing_difference |
| base | 16 | -2.746357 | -2.197313 | -1.559211 | -1.534099 | plausible_forcing_difference |
| overhead_as_canopy | 10 | -10.467633 | -7.982586 | -5.386248 | -5.176759 | plausible_forcing_difference |
| overhead_as_canopy | 12 | -6.985330 | -9.312593 | -1.984998 | -1.747931 | plausible_forcing_difference |
| overhead_as_canopy | 13 | -2.696902 | -3.470991 | -0.382623 | -0.268942 | plausible_forcing_difference |
| overhead_as_canopy | 15 | -10.033638 | -6.967737 | -3.328874 | -3.141675 | plausible_forcing_difference |
| overhead_as_canopy | 16 | -2.683543 | -2.140207 | -1.555694 | -1.533698 | plausible_forcing_difference |

## One-Cell Summary

| forcing_day_id | scenario | five_hour_mean_p90_c | hour_of_max_p90 | max_p90_c |
| --- | --- | --- | --- | --- |
| FD01_high_shortwave_hot_20260507 | base | 55.740134 | 12 | 61.744261 |
| FD01_high_shortwave_hot_20260507 | overhead_as_canopy | 55.363200 | 12 | 61.596094 |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | base | 45.477739 | 13 | 58.075171 |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | overhead_as_canopy | 45.059817 | 13 | 57.567973 |

## Five-Hour Mean Delta P90

| forcing_day_id | five_hour_mean_delta_p90_c | hours_included |
| --- | --- | --- |
| FD01_high_shortwave_hot_20260507 | 0.000000 | 5 |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | 0.000000 | 5 |

## F3a Hour-13 Anchor

| forcing_day_id | scenario | f3a_h13_p90_c | f3b_h13_p90_c | difference_c | status |
| --- | --- | --- | --- | --- | --- |
| FD01_high_shortwave_hot_20260507 | base | 61.598778 | 61.598778 | 0.000000 | consistent_anchor |
| FD01_high_shortwave_hot_20260507 | overhead_as_canopy | 61.245582 | 61.245582 | 0.000000 | consistent_anchor |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | base | 58.075171 | 58.075171 | 0.000000 | consistent_anchor |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | overhead_as_canopy | 57.567973 | 57.567973 | 0.000000 | consistent_anchor |

## Alignment QA

| check_name | status | value | details |
| --- | --- | --- | --- |
| all_20_rasters_opened | PASS | 20/20 | All expected local Tmrt rasters must open for content QA. |
| all_rasters_same_crs | PASS | EPSG:3414 | All rasters must have the same CRS before pixelwise deltas. |
| all_rasters_same_shape | PASS | 150x150 | All rasters must have the same shape before pixelwise deltas. |
| all_rasters_same_transform | PASS | (29300.0, 2.0, 0.0, 34500.0, 0.0, -2.0) | All rasters must have the same transform before pixelwise deltas. |
| all_rasters_same_nodata | PASS | -9999.0 | All rasters must have the same nodata before pixelwise deltas. |
| all_rasters_same_dtype | PASS | float32 | All rasters must have the same dtype before pixelwise deltas. |
| expected_pixel_count_consistency | PASS | 22500 | Pixel count should be identical for all 20 rasters. |
| output_path_outside_git_worktree | PASS | C:/OpenHeat-local/solweig/b85_f1_tiles | Expected output paths must remain local-only and outside Git. |
| no_raster_output_written_by_qa | PASS | no | QA writes only compact CSV/Markdown artifacts. |

## Sanity Checks

| check_name | status | value | details |
| --- | --- | --- | --- |
| expected_run_count | PASS | 20/20 | F3b manifest must remain exactly 20 rows. |
| no_qgis_or_solweig_execution_by_codex | PASS | no | Codex/Python did not run QGIS/SOLWEIG. |
| no_raster_image_or_array_output_written | PASS | no | No raster, image, or large-array outputs are written. |
| no_forbidden_repo_files_changed | PASS | none | Forbidden rasters, svfs.zip, raw archives, and large forecast CSVs must remain untouched. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h10:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h10:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h10:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h10:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h10:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h10:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h12:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h12:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h12:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h12:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h12:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h12:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h13:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h13:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h13:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h13:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h13:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h13:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h15:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h15:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h15:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h15:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h15:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h15:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h16:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h16:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_base_h16:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h16:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h16:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD01_high_shortwave_hot_20260507_TP_0037_overhead_as_canopy_h16:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h10:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h10:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h10:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h10:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h10:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h10:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h12:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h12:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h12:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h12:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h12:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h12:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h13:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h13:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h13:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h15:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h15:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h15:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h15:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h15:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h15:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h16:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h16:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h16:per_raster_sanity_status | PASS | PASS | none |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h16:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h16:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3b_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_as_canopy_h16:per_raster_sanity_status | PASS | PASS | none |
| FD01_high_shortwave_hot_20260507:h10:overhead_delta_status | PASS | overhead_neutral | overhead_as_canopy - base delta; warning status requires manual review. |
| FD01_high_shortwave_hot_20260507:h12:overhead_delta_status | PASS | overhead_neutral | overhead_as_canopy - base delta; warning status requires manual review. |
| FD01_high_shortwave_hot_20260507:h13:overhead_delta_status | PASS | overhead_neutral | overhead_as_canopy - base delta; warning status requires manual review. |
| FD01_high_shortwave_hot_20260507:h15:overhead_delta_status | PASS | overhead_neutral | overhead_as_canopy - base delta; warning status requires manual review. |
| FD01_high_shortwave_hot_20260507:h16:overhead_delta_status | PASS | overhead_neutral | overhead_as_canopy - base delta; warning status requires manual review. |
| FD02_humid_hot_cloudy_or_diffuse_20260508:h10:overhead_delta_status | PASS | overhead_neutral | overhead_as_canopy - base delta; warning status requires manual review. |
| FD02_humid_hot_cloudy_or_diffuse_20260508:h12:overhead_delta_status | PASS | overhead_neutral | overhead_as_canopy - base delta; warning status requires manual review. |
| FD02_humid_hot_cloudy_or_diffuse_20260508:h13:overhead_delta_status | PASS | overhead_neutral | overhead_as_canopy - base delta; warning status requires manual review. |
| FD02_humid_hot_cloudy_or_diffuse_20260508:h15:overhead_delta_status | PASS | overhead_neutral | overhead_as_canopy - base delta; warning status requires manual review. |
| FD02_humid_hot_cloudy_or_diffuse_20260508:h16:overhead_delta_status | PASS | overhead_neutral | overhead_as_canopy - base delta; warning status requires manual review. |
| base:h10:forcing_day_contrast_status | PASS | plausible_forcing_difference | FD02 - FD01 Tmrt contrast by scenario/hour. |
| base:h12:forcing_day_contrast_status | PASS | plausible_forcing_difference | FD02 - FD01 Tmrt contrast by scenario/hour. |
| base:h13:forcing_day_contrast_status | PASS | plausible_forcing_difference | FD02 - FD01 Tmrt contrast by scenario/hour. |
| base:h15:forcing_day_contrast_status | PASS | plausible_forcing_difference | FD02 - FD01 Tmrt contrast by scenario/hour. |
| base:h16:forcing_day_contrast_status | PASS | plausible_forcing_difference | FD02 - FD01 Tmrt contrast by scenario/hour. |
| overhead_as_canopy:h10:forcing_day_contrast_status | PASS | plausible_forcing_difference | FD02 - FD01 Tmrt contrast by scenario/hour. |

## Claim Boundaries

- This is not B9.
- This is not local WBGT.
- This is not risk.
- This is not full 480.
- No Tmrt-to-WBGT conversion was performed.
- Full 480 remains blocked until this one-cell full slice passes.
