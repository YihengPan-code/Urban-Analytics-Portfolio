# A-L1H.2 Status

Status: PASS
Decision: PASS_CANDIDATE_PROBABILITY_COMPANION
Generated: 2026-05-26
Branch: codex/systema-l1h2-prob-threshold-calibration

## Scope

Probability / threshold calibration for existing System A M4/M7 OOF scores. This is score-to-event calibration only, not official warning probability and not prospective forecast skill.

## Command

- `C:\Users\CloudStar\anaconda3\envs\openheat\python.exe scripts/v11_l1h_run_probability_threshold_calibration.py --config configs/v11/systema_l1h_probability_threshold_calibration.yaml`

## Files Created / Modified

- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/calibration_input_inventory.csv`
- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/calibration_analysis_input.csv`
- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/probability_predictions_oof.csv.gz`
- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/score_bin_event_rates.csv`
- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/reliability_bins_fixed.csv`
- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/reliability_bins_quantile.csv`
- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/probability_calibration_metrics.csv`
- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/threshold_operating_points.csv`
- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/threshold_by_station.csv`
- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/threshold_by_regime.csv`
- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/probability_threshold_calibration_report.md`
- `outputs/v11_systema_l1_high_tail/probability_threshold_calibration/A_L1H_2_STATUS.md`

## Key Results

- Best probability companion candidate: M4_inertia_ridge + isotonic_score_only (station_grouped_loso)
- Reliability headline: Brier=0.052; PR-AUC=0.610; ECE_fixed=0.018; ECE_quantile=0.022; P05/P50/P95=0.000/0.000/0.702.
- Recommended operating point: selected_candidate_policy from best_F1: threshold=0.309, precision=0.678, recall=0.765, F1=0.719, CSI=0.561.
- Station/regime caveats: S142 and S139 remain station diagnostics to review; radiation-hot and very-high shortwave rows are retrospective regime diagnostics only and do not establish a causal mechanism.
- Next recommended action: Use calibrated P_ge31 as a diagnostic companion in A-L1H evidence notes; keep deterministic WBGT_A score separate. Proceed to A-L1H.3 only if a separately scoped high-tail regression review is opened; do not start A-L2 from this lane.

## Caveats

- Station-held-out retrospective OOF calibration only.
- P_ge31 is diagnostic and not an official warning probability.
- ge33 remains exploratory.
- Optional score+hour and score+radiation-hot calibrators are diagnostic only.

## Safe To Commit

- Config, scripts, docs, and compact A-L1H.2 diagnostic outputs after review.

## Not Safe To Commit

- Raw archives, rasters, SOLWEIG outputs, tif/tiff files, svfs.zip, patch zip packages, or large hourly forecast CSVs.
