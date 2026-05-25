# P_ge31 Reliability Hardening Report

## Selected model/calibrator

- Score model: `M4_like_inertia_ridge`
- Calibrator: `logistic_score_calibration`
- Validation context: `blocked_date_calibration`
- Scope: retrospective System A Level 1 diagnostic only.

## Sprint 3B metrics

- Brier: 0.064
- ECE_10: 0.013
- Average precision: 0.601
- ROC_AUC: 0.931
- Observed event rate: 0.114
- Mean predicted probability: 0.113
- Probability bias: -0.001

## Station bias warnings

- Stations with abs(probability_bias) >= 0.075: 4
- Stations with event_count below 10: 1

## S142/S137/S135/S139 behavior

| station_id | event_count | event_rate | mean_p | bias | Brier | precision | recall |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S135 | 69 | 0.178 | 0.113 | -0.065 | 0.088 | 0.672 | 0.594 |
| S137 | 77 | 0.198 | 0.111 | -0.087 | 0.104 | 0.705 | 0.558 |
| S139 | 8 | 0.021 | 0.106 | 0.086 | 0.036 | 0.122 | 0.750 |
| S142 | 84 | 0.216 | 0.108 | -0.108 | 0.096 | 0.911 | 0.607 |

## Hour diagnostics

| hour | n | event_rate | mean_p | bias | Brier |
| --- | --- | --- | --- | --- | --- |
| 15 | 405 | 0.341 | 0.243 | -0.098 | 0.238 |
| 14 | 405 | 0.435 | 0.370 | -0.064 | 0.262 |
| 9 | 432 | 0.141 | 0.092 | -0.049 | 0.118 |
| 17 | 459 | 0.037 | 0.079 | 0.042 | 0.042 |
| 18 | 459 | 0.002 | 0.039 | 0.037 | 0.004 |

## Known limitations

- Retrospective calibration context only.
- No lead-time skill is established.
- Station bias remains, including underprediction at S142/S137 and overprediction at S139.
- ge33 remains exploratory and is not promoted in this export.
- This is not an operational warning probability.

## Reliability interpretation

- Acceptable for retrospective diagnostic use: yes, with station-bias caveats.
- Enough for operational use: no.
