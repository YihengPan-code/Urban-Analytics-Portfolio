# A-L1H.0c Status

Status: PASS_FULL_PERIOD
Generated: 2026-05-26
Branch: codex/systema-l1h-residual-decomposition

## Scope

Full-period weather feature recovery / merge hardening for System A A-L1H residual diagnostics only. No model training, formula-v2, probability calibration, high-tail regression, A-L2, System B, SOLWEIG, rasters, or archive hot-path work.

## Command

- `python scripts/v11_l1h_run_full_period_weather_merge.py --config configs/v11/systema_l1h_full_period_weather_merge.yaml`

## Outputs

- `outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/full_period_weather_source_inventory.csv`
- `outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/residual_weather_merge_full_period.csv`
- `outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/residual_by_weather_regime_full_period.csv`
- `outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/ge31_miss_by_weather_regime_full_period.csv`
- `outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/weather_regime_full_period_decision_report.md`
- `outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/A_L1H_0C_STATUS.md`

## Key Results

- Selected weather source: `outputs/v11_systema_l1_high_tail/weather_regime_merge_inputs/best_weather_feature_source.csv.gz`
- Original provenance: `orig:outputs/v11_beta_formal/diagnostics_inputs/v11_pairs_14d_formal_20260524_40419_v091_diag.csv`
- Retention: 6696 / 6696 (100.0%)
- Matched observed ge31 rows: 816 / 816
- Station coverage: 27 / 27
- Weather columns recovered: temperature_2m, relative_humidity_2m, wind_speed_10m, shortwave_radiation, shortwave_3h_mean, cloud_cover, precipitation, direct_radiation, diffuse_radiation
- Weather-regime classification: supported_full_period
- Weather-regime interpretation: Weather-regime diagnostic coverage: PASS_FULL_PERIOD. Radiation-hot regimes contain nearly all observed ge31 events and misses, but conditional miss-rate enrichment beyond the observed-ge31 base rate is mixed. This supports full-period weather-regime diagnostic evidence, not causal proof. The dominant issue remains global high-tail score compression, with station-specific bias and weather-regime structure as interacting diagnostics.
- Next recommended action: close A-L1H.0c as full-period weather-regime residual diagnostic evidence; use it only to inform separately scoped formula-audit review, with probability calibration, high-tail regression, and A-L2 behind explicit review gates.

## Safe To Commit

- Config, scripts, docs, and compact Markdown/CSV diagnostic outputs from this task.

## Not Safe To Commit

- Raw archives, rasters, SOLWEIG outputs, tif/tiff files, svfs.zip, patch zip packages, or large hourly forecast CSVs.
