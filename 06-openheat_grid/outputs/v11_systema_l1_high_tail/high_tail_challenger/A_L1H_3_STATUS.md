# A-L1H.3 Status

Status: PASS
Decision: RECALL_FIRST_DIAGNOSTIC
Generated: 2026-05-27
Branch: codex/systema-l1h3-high-tail-challenger

## Scope

Constrained high-tail challenger benchmark against the accepted A-L1H.2 M4+isotonic P_ge31 diagnostic companion.

## Commands Run

- `C:\Users\CloudStar\anaconda3\envs\openheat\python.exe scripts/v11_l1h3_run_high_tail_challenger.py --config configs/v11/systema_l1h3_high_tail_challenger.yaml`

## Files Created / Modified

- `outputs/v11_systema_l1_high_tail/high_tail_challenger/challenger_input_inventory.csv`
- `outputs/v11_systema_l1_high_tail/high_tail_challenger/challenger_feature_schema.csv`
- `outputs/v11_systema_l1_high_tail/high_tail_challenger/challenger_oof_predictions.csv.gz`
- `outputs/v11_systema_l1_high_tail/high_tail_challenger/challenger_overall_metrics.csv`
- `outputs/v11_systema_l1_high_tail/high_tail_challenger/challenger_threshold_metrics.csv`
- `outputs/v11_systema_l1_high_tail/high_tail_challenger/challenger_reliability_metrics.csv`
- `outputs/v11_systema_l1_high_tail/high_tail_challenger/challenger_by_station.csv`
- `outputs/v11_systema_l1_high_tail/high_tail_challenger/challenger_by_regime.csv`
- `outputs/v11_systema_l1_high_tail/high_tail_challenger/challenger_pairwise_vs_current_companion.csv`
- `outputs/v11_systema_l1_high_tail/high_tail_challenger/high_tail_challenger_report.md`
- `outputs/v11_systema_l1_high_tail/high_tail_challenger/A_L1H_3_STATUS.md`

## Key Results

- Best challenger: cost_sensitive_logistic_score_weather (RECALL_FIRST_DIAGNOSTIC)
- Decision: RECALL_FIRST_DIAGNOSTIC
- Versus current best-F1: cost_sensitive_logistic_score_weather best_F1 vs current best_F1: delta recall=0.088, delta miss_rate=-0.088, delta precision=-0.031, delta F1=0.017, delta CSI=0.021.
- Versus current recall90: cost_sensitive_logistic_score_weather best_F1 vs current recall_90: delta recall=-0.093, delta miss_rate=0.093, delta precision=0.102, delta F1=0.044, delta CSI=0.053.
- A-L2 recommendation: Hold A-L2 from this lane. If reviewed station residual evidence remains compelling after Level 1 closeout, open a separate A-L2.0 preflight; do not merge it into A-L1H.3.

## Caveats

- S142/S139 and radiation-hot / very-high shortwave regimes remain diagnostics; station/regime structure is not treated as causal proof or prospective skill.
- Retrospective station-held-out OOF benchmark only.
- P_ge31 remains diagnostic, not official warning probability.
- No prospective forecast skill is claimed.
- ge33 remains exploratory.

## Safe To Commit

- Config, scripts, Chinese documentation, and compact A-L1H.3 benchmark outputs after review.

## Not Safe To Commit

- System B outputs, SOLWEIG outputs, raster/raw archive data, .tif/.tiff files, svfs.zip, large hourly forecast CSVs, patch zips, or raw API dumps.

## Next Recommended Action

Hold A-L2 from this lane. If reviewed station residual evidence remains compelling after Level 1 closeout, open a separate A-L2.0 preflight; do not merge it into A-L1H.3.
