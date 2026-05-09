# OpenHeat v0.8-beta UMEP with vegetation merge QA

Base grid: `data\grid\toa_payoh_grid_v07_features_beta_final_v071_risk.csv`
UMEP morphology: `data\grid\toa_payoh_grid_v08_umep_morphology_with_veg.csv`
Output grid: `data\grid\toa_payoh_grid_v08_features_umep_with_veg.csv`

Rows: base=986, UMEP=986, output=986
Missing UMEP rows after merge: **0**

## Selected replacement columns
- `svf` ← `svf_umep_mean_open_with_veg`
- `shade_fraction` ← `shade_fraction_umep_10_16_open_with_veg`

## Feature summaries
- `svf_proxy_v07`: missing=0, min=0.3998, mean=0.8621, median=0.9145, p75=0.9531, p95=0.9800, max=0.9800
- `svf`: missing=0, min=0.0242, mean=0.4906, median=0.4778, p75=0.7127, p95=0.9580, max=0.9978
- `delta_svf_v08_minus_proxy`: missing=0, min=-0.9501, mean=-0.3715, median=-0.3604, p75=-0.1627, p95=0.0224, max=0.1313
- `shade_fraction_proxy_v07`: missing=0, min=0.0400, mean=0.2504, median=0.2364, p75=0.3108, p95=0.4338, max=0.6367
- `shade_fraction`: missing=0, min=0.0000, mean=0.4225, median=0.3988, p75=0.6352, p95=0.9253, max=0.9712
- `delta_shade_v08_minus_proxy`: missing=0, min=-0.4497, mean=0.1721, median=0.1446, p75=0.3647, p95=0.6437, max=0.8187
- `open_pixel_fraction`: missing=0, min=0.0936, mean=0.9254, median=1.0000, p75=1.0000, p95=1.0000, max=1.0000
- `building_pixel_fraction`: missing=0, min=0.0000, mean=0.0746, median=0.0000, p75=0.1187, p95=0.3378, max=0.9064

## Counts
- svf_ge_0_95: 57
- svf_le_0_10: 83
- shade_ge_0_70: 175
- shade_eq_0: 26
- fallback_svf_rows: 0
- fallback_shade_rows: 0

## Interpretation notes
- This is the v0.8-beta building + canopy UMEP morphology layer.
- `shade_fraction` is UMEP building + vegetation shadow over open pixels for the chosen date/time window.
- `svf` also includes vegetation obstruction, so it is lower than building-only SVF and should be interpreted as canopy-aware open-pixel SVF.
- v0.7 proxy columns are retained as `svf_proxy_v07` and `shade_fraction_proxy_v07` for comparison.
- This remains morphology/radiation screening, not full SOLWEIG Tmrt simulation.