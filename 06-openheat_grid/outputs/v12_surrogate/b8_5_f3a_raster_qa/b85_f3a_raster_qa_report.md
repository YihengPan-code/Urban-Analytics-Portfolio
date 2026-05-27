# B8.5-F3a Raster Content QA Report

Generated: 2026-05-27 03:37:00

## Decision

- Status: `MICRO_BATCH_RASTER_QA_PASS`
- Raster count opened: `4/4`
- Alignment status: `PASS`
- Per-run p90 range: `57.57-61.60 C`
- Base-vs-overhead delta headline: FD01 mean -0.663888 C (overhead_neutral); FD02 mean -0.598506 C (overhead_neutral)
- FD02-vs-FD01 contrast headline: base mean -2.762285 C, p90 -0.404498 C (plausible_forcing_difference); overhead_as_canopy mean -2.696902 C, p90 -0.382623 C (plausible_forcing_difference)
- Next recommended action: `F3b one-cell full slice`

## Why This Follows F3a POST

B8.5-F3a POST already showed 4/4 run-log success and 4/4 expected `Tmrt_average.tif` files, but it did not open raster contents. This QA lane is the next compact content sanity check for the same four-run micro-batch only.

## Read/Write Boundary

The script read only the four local `Tmrt_average.tif` rasters declared by the F3a manifest. It wrote no raster, image, GeoTIFF, PNG, clipped raster, or large array output. It did not open or copy `svfs.zip`, and it did not run QGIS or SOLWEIG.

## Raster Inventory Summary

| run_id | forcing_day_id | scenario | exists | file_size_bytes | crs | width | height | opened_for_qa |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_base_h13 | FD01_high_shortwave_hot_20260507 | base | yes | 90658 | EPSG:3414 | 150 | 150 | yes |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_overhead_h13 | FD01_high_shortwave_hot_20260507 | overhead_as_canopy | yes | 90658 | EPSG:3414 | 150 | 150 | yes |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13 | FD02_humid_hot_cloudy_or_diffuse_20260508 | base | yes | 90658 | EPSG:3414 | 150 | 150 | yes |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_h13 | FD02_humid_hot_cloudy_or_diffuse_20260508 | overhead_as_canopy | yes | 90658 | EPSG:3414 | 150 | 150 | yes |

## Per-Run Tmrt Stats

| run_id | scenario | valid_pixel_count | nodata_fraction | mean_c | p50_c | p90_c | p95_c | max_c | sanity_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_base_h13 | base | 22500 | 0.000000 | 50.766133 | 57.573914 | 61.598778 | 62.174397 | 62.579208 | PASS |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_overhead_h13 | overhead_as_canopy | 22500 | 0.000000 | 50.102245 | 57.132648 | 61.245582 | 61.816008 | 62.564804 | PASS |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13 | base | 22500 | 0.000000 | 48.003849 | 53.093161 | 58.075171 | 58.936028 | 59.546646 | PASS |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_h13 | overhead_as_canopy | 22500 | 0.000000 | 47.405343 | 52.669868 | 57.567973 | 58.391335 | 59.527508 | PASS |

## Base-vs-Overhead_As_Canopy Delta

Delta is `overhead_as_canopy - base`. This is an overhead-as-canopy sensitivity check, not exact real-world overhead physics.

| forcing_day_id | mean_delta_c | p50_delta_c | p90_delta_c | p95_delta_c | min_delta_c | max_delta_c | delta_direction_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FD01_high_shortwave_hot_20260507 | -0.663888 | 0.000000 | 0.000000 | 0.000000 | -26.959572 | 0.057655 | overhead_neutral |
| FD02_humid_hot_cloudy_or_diffuse_20260508 | -0.598506 | 0.000000 | 0.000000 | 0.000000 | -24.135750 | 0.013489 | overhead_neutral |

## FD01-vs-FD02 Contrast

| scenario | contrast_direction | mean_difference_c | p90_difference_c | valid_overlap_pixels | qualitative_status |
| --- | --- | --- | --- | --- | --- |
| base | FD02_minus_FD01 | -2.762285 | -0.404498 | 22500 | plausible_forcing_difference |
| overhead_as_canopy | FD02_minus_FD01 | -2.696902 | -0.382623 | 22500 | plausible_forcing_difference |

## Alignment And Nodata Sanity

| check_name | status | value | details |
| --- | --- | --- | --- |
| all_4_rasters_have_same_shape | PASS | 150x150 | Shape comparison uses height x width. |
| all_4_rasters_have_same_crs | PASS | EPSG:3414 | CRS must match before pixelwise deltas. |
| all_4_rasters_have_same_transform | PASS | (29300.0, 2.0, 0.0, 34500.0, 0.0, -2.0) | Transform must match before pixelwise deltas. |
| all_4_rasters_have_same_nodata_dtype | PASS | -9999.0/float32 | Nodata and dtype should be consistent across the micro-batch. |
| expected_pixel_count_consistency | PASS | 22500 | Pixel count should be identical for the four local rasters. |
| output_path_outside_git_worktree | PASS | C:/OpenHeat-local/solweig/b85_f1_tiles | Local SOLWEIG raster paths should remain outside the Git worktree and under local_output_root. |
| no_raster_output_written | PASS | False | QA writes only CSV/Markdown control artifacts. |

## Sanity Checks

| check_name | status | value | details |
| --- | --- | --- | --- |
| all_rasters_opened_successfully | PASS | 4/4 | All expected Tmrt_average.tif files must open for content QA. |
| expected_run_count | PASS | 4/4 | Manifest row count must match expected_run_count. |
| postrun_validation_passed | PASS | true | F3a POST should already show 4/4 output validation. |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_base_h13:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_base_h13:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_base_h13:min_max_plausible | PASS | 34.893349..62.579208 | Configured plausible range is 15-80 C. |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_base_h13:p90_ge_p50 | PASS | p50=57.573914, p90=61.598778 | Percentile ordering sanity check. |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_base_h13:p95_ge_p90 | PASS | p90=61.598778, p95=62.174397 | Percentile ordering sanity check. |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_base_h13:parent_folder_hour_matches_expected | PASS | 13 | Uses parent-folder hour parsing because Tmrt_average.tif does not encode hour. |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_overhead_h13:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_overhead_h13:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_overhead_h13:min_max_plausible | PASS | 34.893349..62.564804 | Configured plausible range is 15-80 C. |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_overhead_h13:p90_ge_p50 | PASS | p50=57.132648, p90=61.245582 | Percentile ordering sanity check. |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_overhead_h13:p95_ge_p90 | PASS | p90=61.245582, p95=61.816008 | Percentile ordering sanity check. |
| b85_f3a_FD01_high_shortwave_hot_20260507_TP_0037_overhead_h13:parent_folder_hour_matches_expected | PASS | 13 | Uses parent-folder hour parsing because Tmrt_average.tif does not encode hour. |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13:min_max_plausible | PASS | 34.764782..59.546646 | Configured plausible range is 15-80 C. |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13:p90_ge_p50 | PASS | p50=53.093161, p90=58.075171 | Percentile ordering sanity check. |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13:p95_ge_p90 | PASS | p90=58.075171, p95=58.936028 | Percentile ordering sanity check. |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_base_h13:parent_folder_hour_matches_expected | PASS | 13 | Uses parent-folder hour parsing because Tmrt_average.tif does not encode hour. |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_h13:valid_pixel_count_gt_0 | PASS | 22500 | Raster must contain at least one valid Tmrt pixel. |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_h13:nodata_fraction_lt_0_5 | PASS | 0.000000 | Nodata fraction should remain below 0.5. |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_h13:min_max_plausible | PASS | 34.764782..59.527508 | Configured plausible range is 15-80 C. |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_h13:p90_ge_p50 | PASS | p50=52.669868, p90=57.567973 | Percentile ordering sanity check. |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_h13:p95_ge_p90 | PASS | p90=57.567973, p95=58.391335 | Percentile ordering sanity check. |
| b85_f3a_FD02_humid_hot_cloudy_or_diffuse_20260508_TP_0037_overhead_h13:parent_folder_hour_matches_expected | PASS | 13 | Uses parent-folder hour parsing because Tmrt_average.tif does not encode hour. |
| FD01_high_shortwave_hot_20260507:overhead_delta_not_nan | PASS | 22500 | overhead_as_canopy - base delta must have valid overlap pixels. |
| FD02_humid_hot_cloudy_or_diffuse_20260508:overhead_delta_not_nan | PASS | 22500 | overhead_as_canopy - base delta must have valid overlap pixels. |
| FD01_high_shortwave_hot_20260507:base_and_overhead_paths_distinct | PASS | true | Base and overhead_as_canopy raster paths must not alias. |
| FD02_humid_hot_cloudy_or_diffuse_20260508:base_and_overhead_paths_distinct | PASS | true | Base and overhead_as_canopy raster paths must not alias. |
| base:fd01_and_fd02_paths_distinct | PASS | true | FD01 and FD02 raster paths must not alias within scenario. |
| overhead_as_canopy:fd01_and_fd02_paths_distinct | PASS | true | FD01 and FD02 raster paths must not alias within scenario. |
| no_forbidden_repo_files_changed | PASS |  | Forbidden rasters, svfs.zip, raw archives, and large forecast CSVs must remain untouched. |
| no_qgis_or_solweig_execution | PASS | False | This lane is read-only raster content QA. |
| no_raster_image_or_array_output_written | PASS | False | No GeoTIFF, PNG, image, or large array output is written. |

## Claim Boundaries

- This is not B9.
- This is not local WBGT.
- This is not risk.
- This is not full multi-forcing stability.
- No Tmrt-to-WBGT conversion was performed.
- No raster was committed or written by this QA lane.
