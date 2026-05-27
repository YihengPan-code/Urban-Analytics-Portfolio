# B8.5-F3c N24 / 480-Run Report

Generated: 2026-05-27 05:08:25

## Decision

- Status: `N24_STABILITY_REVIEW_READY`
- Stability summary status: `PASS`
- Manifest run count: `480`
- Unique cell count: `24`
- Next action: `Human review of N24 stability evidence; N150 / B9 remains blocked until review passes.`

## Read/Write Boundary

Codex/Python did not run QGIS/SOLWEIG. No rasters were created, copied, moved, opened, written, or committed by the preparation lane. Raster QA reads local `Tmrt_average.tif` contents only after a successful human-run postrun validator. This report is stability evidence only.

## Claim Boundaries

- Not B9.
- Not local WBGT.
- Not risk.
- Not N150.
- Not full AOI.
- No Tmrt-to-WBGT conversion.
- No hazard_score, risk_score, AOI-wide prediction, or System A/B coupling output.
- N150 / B9 remains blocked until N24 execution and stability review pass.

## Cell-Hour Summary Sample

| cell_id | forcing_day_id | hour_sgt | scenario | tmrt_mean_c | tmrt_p50_c | tmrt_p90_c | tmrt_p95_c | tmrt_max_c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 10 | base | 37.907881 | 34.145142 | 45.335340 | 46.096210 | 46.574692 |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 10 | overhead_as_canopy | 37.555015 | 33.950687 | 44.895851 | 45.601213 | 46.552807 |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 12 | base | 50.555146 | 58.243296 | 61.744261 | 62.092192 | 62.319798 |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 12 | overhead_as_canopy | 49.886746 | 57.722231 | 61.596094 | 61.877173 | 62.308121 |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 13 | base | 50.766133 | 57.573914 | 61.598778 | 62.174397 | 62.579208 |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 13 | overhead_as_canopy | 50.102245 | 57.132648 | 61.245582 | 61.816008 | 62.564804 |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 15 | base | 47.501209 | 52.264091 | 59.555224 | 60.227086 | 60.808533 |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 15 | overhead_as_canopy | 46.888578 | 41.186857 | 59.084558 | 59.810430 | 60.807812 |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 16 | base | 41.085257 | 36.815649 | 50.467068 | 51.216184 | 51.817322 |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 16 | overhead_as_canopy | 40.666514 | 36.461889 | 49.993913 | 50.753836 | 51.814468 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 10 | base | 27.123008 | 27.332534 | 28.081336 | 28.508116 | 29.860762 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 10 | overhead_as_canopy | 27.087382 | 27.329103 | 27.957441 | 28.281956 | 29.860762 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 12 | base | 43.372208 | 47.262140 | 51.947747 | 52.861736 | 53.459007 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 12 | overhead_as_canopy | 42.901416 | 46.773626 | 51.416779 | 52.274622 | 53.434177 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 13 | base | 48.003849 | 53.093161 | 58.075171 | 58.936028 | 59.546646 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 13 | overhead_as_canopy | 47.405343 | 52.669868 | 57.567973 | 58.391335 | 59.527508 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 15 | base | 37.146793 | 38.512045 | 42.953761 | 43.761915 | 44.370232 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 15 | overhead_as_canopy | 36.854940 | 34.388357 | 42.484601 | 43.261231 | 44.361141 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 16 | base | 38.338900 | 34.674313 | 46.330681 | 47.057508 | 47.637039 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 16 | overhead_as_canopy | 37.982971 | 34.382612 | 45.872292 | 46.605883 | 47.632957 |
| TP_0059 | FD01_high_shortwave_hot_20260507 | 10 | base | 43.339755 | 45.655106 | 46.255909 | 46.309658 | 46.632217 |
| TP_0059 | FD01_high_shortwave_hot_20260507 | 10 | overhead_as_canopy | 41.118162 | 44.096905 | 46.047962 | 46.185354 | 46.632217 |
| TP_0059 | FD01_high_shortwave_hot_20260507 | 12 | base | 58.654126 | 61.854399 | 62.162001 | 62.210011 | 62.440434 |
| TP_0059 | FD01_high_shortwave_hot_20260507 | 12 | overhead_as_canopy | 54.752831 | 60.785847 | 62.024376 | 62.130527 | 62.359184 |
| TP_0059 | FD01_high_shortwave_hot_20260507 | 13 | base | 58.816689 | 61.928198 | 62.340733 | 62.425648 | 62.624130 |

## Base-vs-Overhead Delta Sample

Delta is `overhead_as_canopy - base`; this is Tmrt stability evidence, not WBGT.

| cell_id | forcing_day_id | hour_sgt | delta_tmrt_p90_c | within_slice_rank | rank_direction |
| --- | --- | --- | --- | --- | --- |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 10 | -0.439489 | 5 | most_negative_delta_rank_1 |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 12 | -0.148167 | 10 | most_negative_delta_rank_1 |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 13 | -0.353196 | 7 | most_negative_delta_rank_1 |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 15 | -0.470666 | 6 | most_negative_delta_rank_1 |
| TP_0037 | FD01_high_shortwave_hot_20260507 | 16 | -0.473155 | 5 | most_negative_delta_rank_1 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 10 | -0.123895 | 7 | most_negative_delta_rank_1 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 12 | -0.530968 | 5 | most_negative_delta_rank_1 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 13 | -0.507198 | 5 | most_negative_delta_rank_1 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 15 | -0.469160 | 5 | most_negative_delta_rank_1 |
| TP_0037 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 16 | -0.458389 | 5 | most_negative_delta_rank_1 |
| TP_0059 | FD01_high_shortwave_hot_20260507 | 10 | -0.207947 | 11 | most_negative_delta_rank_1 |
| TP_0059 | FD01_high_shortwave_hot_20260507 | 12 | -0.137625 | 11 | most_negative_delta_rank_1 |
| TP_0059 | FD01_high_shortwave_hot_20260507 | 13 | -0.189520 | 12 | most_negative_delta_rank_1 |
| TP_0059 | FD01_high_shortwave_hot_20260507 | 15 | -0.227618 | 11 | most_negative_delta_rank_1 |
| TP_0059 | FD01_high_shortwave_hot_20260507 | 16 | -0.230591 | 11 | most_negative_delta_rank_1 |
| TP_0059 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 10 | -0.139517 | 5 | most_negative_delta_rank_1 |
| TP_0059 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 12 | -0.255928 | 10 | most_negative_delta_rank_1 |
| TP_0059 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 13 | -0.261890 | 11 | most_negative_delta_rank_1 |
| TP_0059 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 15 | -0.237782 | 9 | most_negative_delta_rank_1 |
| TP_0059 | FD02_humid_hot_cloudy_or_diffuse_20260508 | 16 | -0.223701 | 10 | most_negative_delta_rank_1 |
| TP_0088 | FD01_high_shortwave_hot_20260507 | 10 | -0.227787 | 10 | most_negative_delta_rank_1 |
| TP_0088 | FD01_high_shortwave_hot_20260507 | 12 | -0.152488 | 9 | most_negative_delta_rank_1 |
| TP_0088 | FD01_high_shortwave_hot_20260507 | 13 | -0.206166 | 11 | most_negative_delta_rank_1 |
| TP_0088 | FD01_high_shortwave_hot_20260507 | 15 | -0.213756 | 13 | most_negative_delta_rank_1 |
| TP_0088 | FD01_high_shortwave_hot_20260507 | 16 | -0.220947 | 13 | most_negative_delta_rank_1 |

## Forcing-Day Contrast Sample

Contrast is `FD02 - FD01` for the same cell/hour/scenario.

| cell_id | hour_sgt | scenario | p90_difference_c | contrast_direction |
| --- | --- | --- | --- | --- |
| TP_0037 | 10 | base | -17.254004 | FD02_minus_FD01 |
| TP_0037 | 10 | overhead_as_canopy | -16.938410 | FD02_minus_FD01 |
| TP_0037 | 12 | base | -9.796514 | FD02_minus_FD01 |
| TP_0037 | 12 | overhead_as_canopy | -10.179315 | FD02_minus_FD01 |
| TP_0037 | 13 | base | -3.523607 | FD02_minus_FD01 |
| TP_0037 | 13 | overhead_as_canopy | -3.677609 | FD02_minus_FD01 |
| TP_0037 | 15 | base | -16.601463 | FD02_minus_FD01 |
| TP_0037 | 15 | overhead_as_canopy | -16.599957 | FD02_minus_FD01 |
| TP_0037 | 16 | base | -4.136387 | FD02_minus_FD01 |
| TP_0037 | 16 | overhead_as_canopy | -4.121621 | FD02_minus_FD01 |
| TP_0059 | 10 | base | -17.697744 | FD02_minus_FD01 |
| TP_0059 | 10 | overhead_as_canopy | -17.629314 | FD02_minus_FD01 |
| TP_0059 | 12 | base | -9.086996 | FD02_minus_FD01 |
| TP_0059 | 12 | overhead_as_canopy | -9.205299 | FD02_minus_FD01 |
| TP_0059 | 13 | base | -3.158425 | FD02_minus_FD01 |
| TP_0059 | 13 | overhead_as_canopy | -3.230795 | FD02_minus_FD01 |
| TP_0059 | 15 | base | -16.501331 | FD02_minus_FD01 |
| TP_0059 | 15 | overhead_as_canopy | -16.511495 | FD02_minus_FD01 |
| TP_0059 | 16 | base | -4.176716 | FD02_minus_FD01 |
| TP_0059 | 16 | overhead_as_canopy | -4.169826 | FD02_minus_FD01 |
| TP_0088 | 10 | base | -17.651219 | FD02_minus_FD01 |
| TP_0088 | 10 | overhead_as_canopy | -17.540802 | FD02_minus_FD01 |
| TP_0088 | 12 | base | -9.111961 | FD02_minus_FD01 |
| TP_0088 | 12 | overhead_as_canopy | -9.192828 | FD02_minus_FD01 |
| TP_0088 | 13 | base | -3.182907 | FD02_minus_FD01 |

## Stability Metrics Sample

| record_type | cell_id | hour_sgt | metric | value | status | details |
| --- | --- | --- | --- | --- | --- | --- |
| spearman_by_hour |  | 10 | spearman_delta_tmrt_p90_fd01_fd02 | 0.657072 | PASS | Spearman correlation between FD01 and FD02 delta_tmrt_p90_c ranks by hour. |
| rank_drift_by_cell_hour | TP_0037 | 10 | rank_drift | 2 | PASS | FD01_rank=5; FD02_rank=7; sign_stable=True |
| rank_drift_by_cell_hour | TP_0059 | 10 | rank_drift | 6 | WARN | FD01_rank=11; FD02_rank=5; sign_stable=True |
| rank_drift_by_cell_hour | TP_0088 | 10 | rank_drift | 2 | PASS | FD01_rank=10; FD02_rank=8; sign_stable=True |
| rank_drift_by_cell_hour | TP_0098 | 10 | rank_drift | 14 | WARN | FD01_rank=9; FD02_rank=23; sign_stable=False |
| rank_drift_by_cell_hour | TP_0115 | 10 | rank_drift | 2 | PASS | FD01_rank=20; FD02_rank=18; sign_stable=True |
| rank_drift_by_cell_hour | TP_0141 | 10 | rank_drift | 3 | PASS | FD01_rank=3; FD02_rank=6; sign_stable=True |
| rank_drift_by_cell_hour | TP_0154 | 10 | rank_drift | 2 | PASS | FD01_rank=13; FD02_rank=15; sign_stable=True |
| rank_drift_by_cell_hour | TP_0254 | 10 | rank_drift | 2 | PASS | FD01_rank=14; FD02_rank=16; sign_stable=True |
| rank_drift_by_cell_hour | TP_0301 | 10 | rank_drift | 2 | PASS | FD01_rank=20; FD02_rank=18; sign_stable=True |
| rank_drift_by_cell_hour | TP_0326 | 10 | rank_drift | 2 | PASS | FD01_rank=20; FD02_rank=22; sign_stable=False |
| rank_drift_by_cell_hour | TP_0366 | 10 | rank_drift | 4 | PASS | FD01_rank=17; FD02_rank=13; sign_stable=True |
| rank_drift_by_cell_hour | TP_0409 | 10 | rank_drift | 16 | WARN | FD01_rank=8; FD02_rank=24; sign_stable=False |
| rank_drift_by_cell_hour | TP_0433 | 10 | rank_drift | 8 | WARN | FD01_rank=2; FD02_rank=10; sign_stable=True |
| rank_drift_by_cell_hour | TP_0492 | 10 | rank_drift | 2 | PASS | FD01_rank=20; FD02_rank=18; sign_stable=True |
| rank_drift_by_cell_hour | TP_0542 | 10 | rank_drift | 1 | PASS | FD01_rank=4; FD02_rank=3; sign_stable=True |
| rank_drift_by_cell_hour | TP_0565 | 10 | rank_drift | 4 | PASS | FD01_rank=18; FD02_rank=14; sign_stable=True |
| rank_drift_by_cell_hour | TP_0575 | 10 | rank_drift | 3 | PASS | FD01_rank=7; FD02_rank=4; sign_stable=True |
| rank_drift_by_cell_hour | TP_0627 | 10 | rank_drift | 4 | PASS | FD01_rank=15; FD02_rank=11; sign_stable=True |
| rank_drift_by_cell_hour | TP_0676 | 10 | rank_drift | 4 | PASS | FD01_rank=16; FD02_rank=12; sign_stable=True |
| rank_drift_by_cell_hour | TP_0773 | 10 | rank_drift | 4 | PASS | FD01_rank=6; FD02_rank=2; sign_stable=True |
| rank_drift_by_cell_hour | TP_0835 | 10 | rank_drift | 3 | PASS | FD01_rank=12; FD02_rank=9; sign_stable=True |
| rank_drift_by_cell_hour | TP_0857 | 10 | rank_drift | 0 | PASS | FD01_rank=1; FD02_rank=1; sign_stable=True |
| rank_drift_by_cell_hour | TP_0960 | 10 | rank_drift | 2 | PASS | FD01_rank=19; FD02_rank=17; sign_stable=True |
| rank_drift_by_cell_hour | TP_0986 | 10 | rank_drift | 2 | PASS | FD01_rank=20; FD02_rank=18; sign_stable=True |
| sign_stability_by_hour |  | 10 | sign_stability_fraction | 0.875000 | WARN | 21/24 cells have stable delta sign. |
| top_k_overlap_by_hour |  | 10 | top5 | 0.400000 | WARN | overlap=2/5; FD01_top=TP_0037;TP_0141;TP_0433;TP_0542;TP_0857; FD02_top=TP_0059;TP_0542;TP_0575;TP_0773;TP_0857 |
| top_k_overlap_by_hour |  | 10 | top10pct | 0.333333 | WARN | overlap=1/3; FD01_top=TP_0141;TP_0433;TP_0857; FD02_top=TP_0542;TP_0773;TP_0857 |
| top_k_overlap_by_hour |  | 10 | top20pct | 0.400000 | WARN | overlap=2/5; FD01_top=TP_0037;TP_0141;TP_0433;TP_0542;TP_0857; FD02_top=TP_0059;TP_0542;TP_0575;TP_0773;TP_0857 |
| spearman_by_hour |  | 12 | spearman_delta_tmrt_p90_fd01_fd02 | 0.920276 | PASS | Spearman correlation between FD01 and FD02 delta_tmrt_p90_c ranks by hour. |
| rank_drift_by_cell_hour | TP_0037 | 12 | rank_drift | 5 | PASS | FD01_rank=10; FD02_rank=5; sign_stable=True |
| rank_drift_by_cell_hour | TP_0059 | 12 | rank_drift | 1 | PASS | FD01_rank=11; FD02_rank=10; sign_stable=True |
| rank_drift_by_cell_hour | TP_0088 | 12 | rank_drift | 2 | PASS | FD01_rank=9; FD02_rank=11; sign_stable=True |
| rank_drift_by_cell_hour | TP_0098 | 12 | rank_drift | 0 | PASS | FD01_rank=8; FD02_rank=8; sign_stable=True |
| rank_drift_by_cell_hour | TP_0115 | 12 | rank_drift | 0 | PASS | FD01_rank=20; FD02_rank=20; sign_stable=True |
| rank_drift_by_cell_hour | TP_0141 | 12 | rank_drift | 1 | PASS | FD01_rank=2; FD02_rank=3; sign_stable=True |
| rank_drift_by_cell_hour | TP_0154 | 12 | rank_drift | 7 | WARN | FD01_rank=6; FD02_rank=13; sign_stable=True |
| rank_drift_by_cell_hour | TP_0254 | 12 | rank_drift | 1 | PASS | FD01_rank=15; FD02_rank=14; sign_stable=True |
| rank_drift_by_cell_hour | TP_0301 | 12 | rank_drift | 0 | PASS | FD01_rank=20; FD02_rank=20; sign_stable=True |
| rank_drift_by_cell_hour | TP_0326 | 12 | rank_drift | 0 | PASS | FD01_rank=20; FD02_rank=20; sign_stable=True |

## Unstable Cell Inventory Sample

| cell_id | hour_sgt | instability_reason | severity | details |
| --- | --- | --- | --- | --- |
| TP_0037 | 10 | top_k_disagreement | REVIEW | FD01_rank=5; FD02_rank=7; rank_drift=2; FD01_delta=-0.439489; FD02_delta=-0.123895 |
| TP_0059 | 10 | high_rank_drift;top_k_disagreement | REVIEW | FD01_rank=11; FD02_rank=5; rank_drift=6; FD01_delta=-0.207947; FD02_delta=-0.139517 |
| TP_0098 | 10 | high_rank_drift;sign_flip | HIGH | FD01_rank=9; FD02_rank=23; rank_drift=14; FD01_delta=-0.288849; FD02_delta=0.009154 |
| TP_0141 | 10 | top_k_disagreement | REVIEW | FD01_rank=3; FD02_rank=6; rank_drift=3; FD01_delta=-0.784488; FD02_delta=-0.130893 |
| TP_0326 | 10 | sign_flip | HIGH | FD01_rank=20; FD02_rank=22; rank_drift=2; FD01_delta=0.000000; FD02_delta=0.002966 |
| TP_0409 | 10 | high_rank_drift;sign_flip | HIGH | FD01_rank=8; FD02_rank=24; rank_drift=16; FD01_delta=-0.318773; FD02_delta=0.010121 |
| TP_0433 | 10 | high_rank_drift;top_k_disagreement | REVIEW | FD01_rank=2; FD02_rank=10; rank_drift=8; FD01_delta=-0.792708; FD02_delta=-0.074098 |
| TP_0575 | 10 | top_k_disagreement | REVIEW | FD01_rank=7; FD02_rank=4; rank_drift=3; FD01_delta=-0.407164; FD02_delta=-0.228634 |
| TP_0773 | 10 | top_k_disagreement | REVIEW | FD01_rank=6; FD02_rank=2; rank_drift=4; FD01_delta=-0.413436; FD02_delta=-0.282356 |
| TP_0037 | 12 | top_k_disagreement | REVIEW | FD01_rank=10; FD02_rank=5; rank_drift=5; FD01_delta=-0.148167; FD02_delta=-0.530968 |
| TP_0154 | 12 | high_rank_drift | REVIEW | FD01_rank=6; FD02_rank=13; rank_drift=7; FD01_delta=-0.268623; FD02_delta=-0.216909 |
| TP_0409 | 12 | top_k_disagreement | REVIEW | FD01_rank=4; FD02_rank=9; rank_drift=5; FD01_delta=-0.456961; FD02_delta=-0.286667 |
| TP_0575 | 12 | high_rank_drift | REVIEW | FD01_rank=13; FD02_rank=7; rank_drift=6; FD01_delta=-0.106363; FD02_delta=-0.476241 |
| TP_0037 | 13 | top_k_disagreement | REVIEW | FD01_rank=7; FD02_rank=5; rank_drift=2; FD01_delta=-0.353196; FD02_delta=-0.507198 |
| TP_0409 | 13 | top_k_disagreement | REVIEW | FD01_rank=5; FD02_rank=8; rank_drift=3; FD01_delta=-0.407042; FD02_delta=-0.418423 |
| TP_0037 | 15 | top_k_disagreement | REVIEW | FD01_rank=6; FD02_rank=5; rank_drift=1; FD01_delta=-0.470666; FD02_delta=-0.469160 |
| TP_0409 | 15 | high_rank_drift;top_k_disagreement | REVIEW | FD01_rank=4; FD02_rank=12; rank_drift=8; FD01_delta=-0.543750; FD02_delta=-0.189654 |
