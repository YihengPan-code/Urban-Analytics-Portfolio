# System A Level 1 Model Card v1.0

Generated: 2026-05-27
Decision status: `A_L1H5_CONTRACT_PASS`
Branch: `codex/systema-l1h5-model-card-contract`

## Intended Use

System A Level 1 produces a calibrated hourly WBGT_A temporal baseline for internal retrospective and future prospective evaluation. The primary output is `wbgt_a_c`.

Optional companions may support internal diagnostics around WBGT >=31 C, expected exceedance above 31 C, and uncertainty intervals. These companions do not replace `wbgt_a_c`.

## Not Intended Use

System A Level 1 is not a validated local 100 m WBGT prediction system, not a real-time public warning system, not a station correction layer, not a System A/B coupling product, and not a risk or hazard score.

## Input Data

The model card is based on compact A-L1H.4 evidence, prior A-L1H high-tail reports, and A-L2.1c station-context preflight evidence if present. The contract uses no System B, SOLWEIG, Tmrt, raster, cell-level, exposure, vulnerability, or archive collector inputs.

## Output Columns

Required columns: timestamp_sgt, timestamp_utc, wbgt_a_c, wbgt_a_model_id, wbgt_a_version, s_wbgt_ge31, s_wbgt_band_31_33, source_forcing, is_retrospective_or_prospective, quality_flag.

Optional companion columns: p_ge31_optional, p_ge31_model_id_optional, p_ge31_threshold_policy_optional, p_ge33_optional, expected_exceedance_ge31_optional, prediction_interval_low_optional, prediction_interval_high_optional, lead_time_hours_optional.

Forbidden columns are listed in `a_l1h5_output_schema.csv` and include cell-level WBGT, station-adjusted WBGT, risk score, and hazard score fields.

## Validation Evidence

- Deterministic WBGT_A baseline: MAE=0.639 C; high-tail MAE for observed ge31=0.995 C.
- P_ge31 optional companion: n=1674.000; events=204.000; Brier=0.052; ECE_fixed=0.018; PR-AUC=0.610; ROC-AUC=0.947.
- P_ge31 best_F1 policy: threshold=0.446; recall=0.765; precision=0.678; miss_rate=0.235; false_alarm_ratio=0.322.
- Expected exceedance optional diagnostic: exceedance_MAE=0.100 C; positive_exceedance_MAE=0.779 C; bias=-0.058 C.
- Interval optional diagnostic: nominal=0.900; coverage=0.898; mean_width=2.869 C.
- P_ge33 support: status=LOW_SUPPORT; events=15.000.

## Known Failure Modes

- High-tail compression near and above 31 C remains a diagnostic caveat.
- ge33 support is low and cannot support promoted probability claims.
- Threshold policies are retrospective operating points, not official warning thresholds.
- Optional intervals have retrospective coverage diagnostics and weak near-ge33 coverage.
- Station diagnostics can be unstable where event support is low.

## S142/S139 Caveats

- S142: n_ge31=15.000; recall=0.533; miss_rate=0.467; false_alarm_ratio=0.000
- S139: n_ge31=1.000; recall=1.000; miss_rate=0.000; false_alarm_ratio=0.889

These are caveats and monitoring requirements, not station correction rules.

## Level 2 Boundary

A-L2.1c is an explanatory station-level residual preflight only. It does not create station-adjusted WBGT, a score residual correction, or a local cell-level modifier.

## System B Boundary

This Level 1 contract does not use System B, SOLWEIG, Tmrt, morphology, cell_id, or radiative modifier features. Any System A/B coupling must be a separate future-scoped lane.

## Prospective Evaluation Requirements

Before any stronger claim for optional companions, freeze this model card and output schema, then evaluate a future formal archive snapshot with prospective rows separated from retrospective rows. Required metrics include recall_ge31, precision_ge31, miss_rate_ge31, Brier, ECE, high-tail MAE, and station caveat refresh.

## Versioning

Contract version: `systema_l1h5_hourly_output_contract_v1`.

Primary model id: `M4_inertia_ridge`.
