# A-L1H.4 Future System A Hourly Output Contract Draft

Generated: 2026-05-27
Decision context: `A_L1H4_COMPANION_PROMISING`

## Recommended Columns

- `timestamp_sgt`
- `timestamp_utc`
- `wbgt_a_c`
- `wbgt_a_model_id`
- `wbgt_a_version`
- `s_wbgt_ge31`
- `s_wbgt_band_31_33`
- `p_ge31_optional`
- `p_ge33_optional`
- `expected_exceedance_ge31_optional`
- `prediction_interval_low_optional`
- `prediction_interval_high_optional`
- `source_forcing`
- `is_retrospective_or_prospective`
- `lead_time_hours_optional`
- `quality_flag`

## Explicitly Forbidden Columns

- `cell_id`
- `local_wbgt_c`
- `delta_wbgt_cell`
- `risk_score`

## Recommendation

Keep `wbgt_a_c` as the deterministic Level 1 WBGT_A baseline. Add probability, expected-exceedance, and interval fields only as optional companion diagnostics until a later model-card gate promotes them.
