# A-L1H.0b Status

Status: PASS
Generated: 2026-05-26
Branch: codex/systema-l1h-residual-decomposition

## Scope

Weather-regime residual merge only, using existing residual diagnostics and existing weather/feature tables. No training, formula-v2 implementation, probability calibration, high-tail regression, A-L2 work, System B outputs, SOLWEIG, rasters, or archive hot-path changes.

## Command

- `python scripts/v11_l1h_run_weather_regime_merge.py --config configs/v11/systema_l1h_weather_regime_merge.yaml`

## Outputs

- `outputs/v11_systema_l1_high_tail/weather_regime_merge/weather_source_inventory.csv`
- `outputs/v11_systema_l1_high_tail/weather_regime_merge/residual_weather_merge_input.csv`
- `outputs/v11_systema_l1_high_tail/weather_regime_merge/residual_by_weather_regime.csv`
- `outputs/v11_systema_l1_high_tail/weather_regime_merge/ge31_miss_by_weather_regime.csv`
- `outputs/v11_systema_l1_high_tail/weather_regime_merge/weather_regime_bias_report.md`
- `outputs/v11_systema_l1_high_tail/weather_regime_merge/A_L1H_0B_STATUS.md`

## Headline

- Selected weather source: `data/calibration/v09_wbgt_station_pairs.csv`
- Merge row retention: 2700 / 6696 (40.3%)
- Recovered weather columns: temperature_2m, relative_humidity_2m, wind_speed_10m, shortwave_radiation, shortwave_3h_mean, cloud_cover, direct_radiation, diffuse_radiation
- Weather-regime interaction: plausible_but_partial
- Next recommended action: mixed staged follow-up: first secure a full-period weather feature table, then revisit formula-v2 / physical proxy and threshold-calibration gates.
