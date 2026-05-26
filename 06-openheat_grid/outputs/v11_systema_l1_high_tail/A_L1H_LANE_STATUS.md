# A-L1H Lane Status

Status: PASS
Generated: 2026-05-26
Branch: codex/systema-l1h-residual-decomposition

## Scope

A-L1H.0 residual decomposition only, using existing System A OOF predictions/model scores. No new models, formula-v2, probability calibration, high-tail regression, System B outputs, SOLWEIG outputs, or archive collector changes.

## Commands run

- `python scripts/v11_l1h_run_residual_decomposition.py --config configs/v11/systema_l1h_residual_decomposition.yaml`

## Files created / modified

- `outputs/v11_systema_l1_high_tail/residual_decomposition/residual_input_inventory.csv`
- `outputs/v11_systema_l1_high_tail/residual_decomposition/residual_analysis_input.csv`
- `outputs/v11_systema_l1_high_tail/residual_decomposition/residual_by_observed_bin.csv`
- `outputs/v11_systema_l1_high_tail/residual_decomposition/residual_by_predicted_bin.csv`
- `outputs/v11_systema_l1_high_tail/residual_decomposition/residual_by_station.csv`
- `outputs/v11_systema_l1_high_tail/residual_decomposition/residual_by_hour.csv`
- `outputs/v11_systema_l1_high_tail/residual_decomposition/residual_by_regime.csv`
- `outputs/v11_systema_l1_high_tail/residual_decomposition/ge31_miss_inventory.csv`
- `outputs/v11_systema_l1_high_tail/residual_decomposition/ge31_false_alarm_inventory.csv`
- `outputs/v11_systema_l1_high_tail/residual_decomposition/ge31_hit_inventory.csv`
- `outputs/v11_systema_l1_high_tail/residual_decomposition/ge33_exploratory_inventory.csv`
- `outputs/v11_systema_l1_high_tail/residual_decomposition/high_tail_bias_report.md`
- `outputs/v11_systema_l1_high_tail/A_L1H_LANE_STATUS.md`

## Key results

- Selected input: `outputs/v11_beta_calibration/hourly_max/v11_beta_oof_predictions.csv`
- Model(s): `M4_inertia_ridge, M7_compact_weather_ridge`
- Target column: `official_wbgt_c_max`
- Selected row count: 6696
- Station count: 27
- Primary fixed ge31 observed / predicted: 408 / 290
- Primary ge31 hits / misses / false alarms: 194 / 214 / 96
- Preliminary classification: mixed: global Level 1 score compression with station-specific residual bias
- Diagnostic caveat: For M4_inertia_ridge, 49.3% of observed ge31 rows fall in predicted 29-31 bins; station mean-residual range is 1.17 C; weather regimes are limited by absent weather columns.

## Caveats

- This is a retrospective OOF residual diagnostic, not a validated local 100m WBGT prediction system.
- Fixed ge31 summaries are threshold diagnostics only and do not establish operational prospective forecast skill.
- ge33 inventory is exploratory only.
- Weather-regime decomposition is limited if weather variables are absent from the selected OOF prediction file.

## Safe to commit

- Config, scripts, protocol doc, and compact CSV/Markdown outputs under `outputs/v11_systema_l1_high_tail/` from this lane, subject to final changed-file review.

## Not safe to commit

- Any `data/solweig/`, `data/rasters/`, raw archive, `.tif`, `.tiff`, `svfs.zip`, patch zip packages, large hourly forecast CSV, System B outputs, SOLWEIG outputs, or unrelated existing modified `outputs/v11_level1/` files.

## Next recommended action

Recommend a staged review: first confirm score-compression evidence, then decide between A-L1H.1 formula-v2, A-L1H.2 probability calibration, A-L1H.3 high-tail regression review gate, and A-L2 station-context preflight. Do not launch one large model change.
