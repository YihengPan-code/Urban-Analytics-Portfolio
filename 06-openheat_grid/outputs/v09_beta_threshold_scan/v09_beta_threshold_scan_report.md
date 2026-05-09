# OpenHeat v0.9-beta threshold scan extension

This report scans **model decision thresholds** for detecting official WBGT events. These thresholds do **not** replace official WBGT thresholds; they calibrate the score scale of each model.

Predictions CSV: `outputs/v09_beta_calibration/v09_beta_predictions_long.csv`
Rows scanned: **1952** threshold rows
Target recall: **0.6**, target precision: **0.5**

## Best-F1 decision thresholds for official WBGT≥31, LOSO overall
| model                       |   selected_model_decision_threshold |   selected_precision |   selected_recall |   selected_f1 |   selected_tp |   selected_fp |   selected_fn |   selected_tn |
|:----------------------------|------------------------------------:|---------------------:|------------------:|--------------:|--------------:|--------------:|--------------:|--------------:|
| M1b_period_bias             |                                29.8 |             0.341625 |          0.768657 |      0.47302  |           206 |           397 |            62 |          1899 |
| M3_regime_current_ridge     |                                30   |             0.430052 |          0.929104 |      0.587957 |           249 |           330 |            19 |          1966 |
| M4_inertia_ridge            |                                30.1 |             0.436494 |          0.910448 |      0.590085 |           244 |           315 |            24 |          1981 |
| M5_inertia_morphology_ridge |                                30.1 |             0.426199 |          0.86194  |      0.57037  |           231 |           311 |            37 |          1985 |

## Recall-target decision thresholds for official WBGT≥31, LOSO overall
| model                       |   selected_model_decision_threshold |   selected_precision |   selected_recall |   selected_f1 |   selected_tp |   selected_fp |   selected_fn |   selected_tn |   note |
|:----------------------------|------------------------------------:|---------------------:|------------------:|--------------:|--------------:|--------------:|--------------:|--------------:|-------:|
| M1b_period_bias             |                                30   |             0.352564 |          0.615672 |      0.44837  |           165 |           303 |           103 |          1993 |    nan |
| M3_regime_current_ridge     |                                30.3 |             0.447423 |          0.809701 |      0.576361 |           217 |           268 |            51 |          2028 |    nan |
| M4_inertia_ridge            |                                30.3 |             0.450199 |          0.843284 |      0.587013 |           226 |           276 |            42 |          2020 |    nan |
| M5_inertia_morphology_ridge |                                30.5 |             0.455497 |          0.649254 |      0.535385 |           174 |           208 |            94 |          2088 |    nan |

## Interpretation notes
- A lower model decision threshold is expected if a calibrated regression model still underpredicts the high-WBGT tail.
- Treat these thresholds as post-hoc detection cut-offs for the current 24h pilot archive.
- Do not interpret a threshold such as `M4_pred ≥ 29°C` as a new official WBGT threshold.
- WBGT≥33 results are reported for diagnostics only because the current archive has very few High events.