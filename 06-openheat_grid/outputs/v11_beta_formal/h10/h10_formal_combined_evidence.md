# H10 formal combined evidence
Status: **PASS**
Decimal criterion: `6`

## Summary
### all_stations
- Dataset status: **PASS**
- Metrics pass: `True`
- OOF pass: `True`
- OOF rows per model: `{'M5_v10_morphology_ridge': 40389, 'M6_v10_overhead_ridge': 40389, 'M7_compact_weather_ridge': 40389}`

Metric rounded values:

- `mae`: pass=True, values={'M5_v10_morphology_ridge': 0.935606, 'M6_v10_overhead_ridge': 0.935606, 'M7_compact_weather_ridge': 0.935606}
- `rmse`: pass=True, values={'M5_v10_morphology_ridge': 1.288906, 'M6_v10_overhead_ridge': 1.288906, 'M7_compact_weather_ridge': 1.288906}
- `bias`: pass=True, values={'M5_v10_morphology_ridge': 0.003504, 'M6_v10_overhead_ridge': 0.003504, 'M7_compact_weather_ridge': 0.003504}
- `r2`: pass=True, values={'M5_v10_morphology_ridge': 0.636005, 'M6_v10_overhead_ridge': 0.636005, 'M7_compact_weather_ridge': 0.636005}

OOF prediction comparisons:

- `M5_v10_morphology_ridge vs M6_v10_overhead_ridge`: max_abs_diff=1.86126669632e-11, nonzero_after_round6=0
- `M5_v10_morphology_ridge vs M7_compact_weather_ridge`: max_abs_diff=9.75930447566e-12, nonzero_after_round6=0
- `M6_v10_overhead_ridge vs M7_compact_weather_ridge`: max_abs_diff=1.50528478571e-11, nonzero_after_round6=0

### no_S142
- Dataset status: **PASS**
- Metrics pass: `True`
- OOF pass: `True`
- OOF rows per model: `{'M5_v10_morphology_ridge': 38893, 'M6_v10_overhead_ridge': 38893, 'M7_compact_weather_ridge': 38893}`

Metric rounded values:

- `mae`: pass=True, values={'M5_v10_morphology_ridge': 0.926656, 'M6_v10_overhead_ridge': 0.926656, 'M7_compact_weather_ridge': 0.926656}
- `rmse`: pass=True, values={'M5_v10_morphology_ridge': 1.270739, 'M6_v10_overhead_ridge': 1.270739, 'M7_compact_weather_ridge': 1.270739}
- `bias`: pass=True, values={'M5_v10_morphology_ridge': 0.003555, 'M6_v10_overhead_ridge': 0.003555, 'M7_compact_weather_ridge': 0.003555}
- `r2`: pass=True, values={'M5_v10_morphology_ridge': 0.637972, 'M6_v10_overhead_ridge': 0.637972, 'M7_compact_weather_ridge': 0.637972}

OOF prediction comparisons:

- `M5_v10_morphology_ridge vs M6_v10_overhead_ridge`: max_abs_diff=1.98134841867e-11, nonzero_after_round6=0
- `M5_v10_morphology_ridge vs M7_compact_weather_ridge`: max_abs_diff=1.06190611859e-11, nonzero_after_round6=0
- `M6_v10_overhead_ridge vs M7_compact_weather_ridge`: max_abs_diff=1.0341949519e-11, nonzero_after_round6=0

### hourly_mean
- Dataset status: **PASS**
- Metrics pass: `True`
- OOF pass: `True`
- OOF rows per model: `{'M5_v10_morphology_ridge': 10473, 'M6_v10_overhead_ridge': 10473, 'M7_compact_weather_ridge': 10473}`

Metric rounded values:

- `mae`: pass=True, values={'M5_v10_morphology_ridge': 0.894784, 'M6_v10_overhead_ridge': 0.894784, 'M7_compact_weather_ridge': 0.894784}
- `rmse`: pass=True, values={'M5_v10_morphology_ridge': 1.229108, 'M6_v10_overhead_ridge': 1.229108, 'M7_compact_weather_ridge': 1.229108}
- `bias`: pass=True, values={'M5_v10_morphology_ridge': 0.003546, 'M6_v10_overhead_ridge': 0.003546, 'M7_compact_weather_ridge': 0.003546}
- `r2`: pass=True, values={'M5_v10_morphology_ridge': 0.654248, 'M6_v10_overhead_ridge': 0.654248, 'M7_compact_weather_ridge': 0.654248}

OOF prediction comparisons:

- `M5_v10_morphology_ridge vs M6_v10_overhead_ridge`: max_abs_diff=3.1512570331e-12, nonzero_after_round6=0
- `M5_v10_morphology_ridge vs M7_compact_weather_ridge`: max_abs_diff=3.33955085807e-12, nonzero_after_round6=0
- `M6_v10_overhead_ridge vs M7_compact_weather_ridge`: max_abs_diff=1.79056769412e-12, nonzero_after_round6=0

### hourly_max
- Dataset status: **PASS**
- Metrics pass: `True`
- OOF pass: `True`
- OOF rows per model: `{'M5_v10_morphology_ridge': 10473, 'M6_v10_overhead_ridge': 10473, 'M7_compact_weather_ridge': 10473}`

Metric rounded values:

- `mae`: pass=True, values={'M5_v10_morphology_ridge': 0.954158, 'M6_v10_overhead_ridge': 0.954158, 'M7_compact_weather_ridge': 0.954158}
- `rmse`: pass=True, values={'M5_v10_morphology_ridge': 1.312972, 'M6_v10_overhead_ridge': 1.312972, 'M7_compact_weather_ridge': 1.312972}
- `bias`: pass=True, values={'M5_v10_morphology_ridge': 0.003854, 'M6_v10_overhead_ridge': 0.003854, 'M7_compact_weather_ridge': 0.003854}
- `r2`: pass=True, values={'M5_v10_morphology_ridge': 0.679275, 'M6_v10_overhead_ridge': 0.679275, 'M7_compact_weather_ridge': 0.679275}

OOF prediction comparisons:

- `M5_v10_morphology_ridge vs M6_v10_overhead_ridge`: max_abs_diff=3.63087337973e-12, nonzero_after_round6=0
- `M5_v10_morphology_ridge vs M7_compact_weather_ridge`: max_abs_diff=3.76587649953e-12, nonzero_after_round6=0
- `M6_v10_overhead_ridge vs M7_compact_weather_ridge`: max_abs_diff=1.06936681732e-12, nonzero_after_round6=0


## Interpretation

PASS means M5/M6/M7 metrics and full-length LOSO OOF predictions are identical to 6 decimal places for all formal framings checked here.
