# System A A-L2.0 Station-Context Residual Identifiability Preflight

Generated: 2026-05-27
Acceptance status: `PASS`
Decision status: `A_L2_READY_FOR_SCOPED_PREFLIGHT_MODEL`
Branch: `codex/systema-l2-identifiability-preflight`
Config: `configs/v11/systema_l2_identifiability_preflight.yaml`

## 1. Why A-L2 is not a Level 1 substitute

A-L2.0 only asks whether station-level residual or probability-error structure remains identifiable after the current Level 1 score/probability evidence and the A-L1H.3 recall-first challenger. It does not replace WBGT_A, does not recalibrate the canonical Level 1 companion, and does not train a final station-context residual model.

The current Level 1 contract remains: WBGT_A/model_score is the primary retrospective temporal severity diagnostic; P_ge31 is a retrospective diagnostic companion only; the challenger is recall-first diagnostic evidence, not the canonical replacement.

## 2. Input inventory

| inventory_role                           | exists | rows_total | has_station_id | has_cell_id | source_class                           | notes                                                                                   |
| ---------------------------------------- | ------ | ---------- | -------------- | ----------- | -------------------------------------- | --------------------------------------------------------------------------------------- |
| residual_weather_merge                   | 1.000  | 6696.000   | 1.000          | 0.000       | diagnostic_input                       | Station key available.                                                                  |
| probability_predictions_oof              | 1.000  | 33356.000  | 1.000          | 0.000       | diagnostic_input                       | Station key available.                                                                  |
| threshold_operating_points               | 1.000  | 103.000    | 0.000          | 0.000       | diagnostic_input                       |                                                                                         |
| threshold_by_station                     | 1.000  | 2359.000   | 1.000          | 0.000       | diagnostic_input                       | Station key available.                                                                  |
| station_regime_caveats                   | 1.000  | 6.000      | 0.000          | 0.000       | diagnostic_input                       |                                                                                         |
| challenger_oof_predictions               | 1.000  | 10044.000  | 1.000          | 0.000       | diagnostic_input                       | Station key available.                                                                  |
| challenger_threshold_metrics             | 1.000  | 17.000     | 0.000          | 0.000       | diagnostic_input                       |                                                                                         |
| challenger_by_station                    | 1.000  | 445.000    | 1.000          | 0.000       | diagnostic_input                       | Station key available.                                                                  |
| challenger_pairwise_vs_current_companion | 1.000  | 30.000     | 0.000          | 0.000       | diagnostic_input                       |                                                                                         |
| station_grid_mapping                     | 1.000  | 27.000     | 1.000          | 1.000       | station_metadata_or_pairing            | Station key available.                                                                  |
| v09_station_pairs                        | 1.000  | 2564.000   | 1.000          | 0.000       | station_metadata_or_pairing            | Station key available.                                                                  |
| v09_station_weather                      | 1.000  | 1296.000   | 1.000          | 0.000       | station_metadata_or_pairing            | Station key available.                                                                  |
| v11_live_chunk                           | 1.000  | 243.000    | 1.000          | 0.000       | station_metadata_or_pairing            | Compact live chunk source; inventoried but not used as a modelling input.               |
| grid_v10_basic_morphology                | 1.000  | 986.000    | 0.000          | 1.000       | morphology_proxy                       | Grid morphology proxy; may be considered only through explicit station-to-cell mapping. |
| grid_v10_umep_features                   | 1.000  | 986.000    | 0.000          | 1.000       | morphology_proxy                       | Grid morphology proxy; may be considered only through explicit station-to-cell mapping. |
| data_stations_dir                        | 0.000  | 0.000      | 0.000          | 0.000       | unavailable_station_metadata_directory | No dedicated station metadata directory found.                                          |

## 3. Station residual summaries

Residual definition: `score_residual_c = official_wbgt_c - model_score`. Positive residual means the Level 1 score underpredicts the official station WBGT target in this diagnostic input.

Top context-adjusted positive residual stations:

| station_id | n_rows | n_ge31 | mean_score_residual_c | mean_context_adjusted_score_residual_c | mean_high_tail_residual_c | low_support_warning_flag |
| ---------- | ------ | ------ | --------------------- | -------------------------------------- | ------------------------- | ------------------------ |
| S137       | 62.000 | 13.000 | 0.765                 | 0.775                                  | 1.471                     | 0.000                    |
| S142       | 62.000 | 15.000 | 0.763                 | 0.773                                  | 2.286                     | 0.000                    |
| S129       | 62.000 | 10.000 | 0.396                 | 0.402                                  | 0.823                     | 0.000                    |
| S127       | 62.000 | 10.000 | 0.361                 | 0.360                                  | 0.551                     | 0.000                    |
| S144       | 62.000 | 8.000  | 0.349                 | 0.349                                  | 0.794                     | 1.000                    |
| S141       | 62.000 | 10.000 | 0.366                 | 0.346                                  | 1.461                     | 0.000                    |
| S130       | 62.000 | 6.000  | 0.295                 | 0.300                                  | 0.215                     | 1.000                    |
| S132       | 62.000 | 9.000  | 0.176                 | 0.173                                  | 0.128                     | 1.000                    |

Top context-adjusted negative residual stations:

| station_id | n_rows | n_ge31 | mean_score_residual_c | mean_context_adjusted_score_residual_c | mean_high_tail_residual_c | low_support_warning_flag |
| ---------- | ------ | ------ | --------------------- | -------------------------------------- | ------------------------- | ------------------------ |
| S146       | 62.000 | 3.000  | -0.440                | -0.443                                 | 0.133                     | 1.000                    |
| S150       | 62.000 | 3.000  | -0.394                | -0.389                                 | 0.350                     | 1.000                    |
| S149       | 62.000 | 5.000  | -0.360                | -0.354                                 | 0.282                     | 1.000                    |
| S148       | 62.000 | 5.000  | -0.346                | -0.339                                 | 0.332                     | 1.000                    |
| S140       | 62.000 | 4.000  | -0.335                | -0.337                                 | -0.265                    | 1.000                    |
| S124       | 62.000 | 0.000  | -0.329                | -0.323                                 | NA                        | 1.000                    |
| S139       | 62.000 | 1.000  | -0.425                | -0.311                                 | 0.238                     | 1.000                    |
| S143       | 62.000 | 7.000  | -0.226                | -0.245                                 | 0.206                     | 1.000                    |

## 4. Probability error summaries

`probability_error = obs_ge31 - p_ge31`. Positive values mean observed events exceed predicted probability on average. Three policies are compared: current companion best-F1/selected policy, A-L1H.3 recall-first challenger selected policy, and current companion recall90.

| probability_case_id                     | station_id | n_ge31 | p_ge31_Brier | mean_context_adjusted_probability_error_obs_minus_p | miss_rate_at_policy | false_alarm_ratio_at_policy |
| --------------------------------------- | ---------- | ------ | ------------ | --------------------------------------------------- | ------------------- | --------------------------- |
| current_companion_best_f1               | S142       | 15.000 | 0.090        | 0.130                                               | 0.467               | 0.000                       |
| current_companion_best_f1               | S139       | 1.000  | 0.069        | -0.106                                              | 0.000               | 0.889                       |
| current_companion_recall90              | S142       | 15.000 | 0.090        | 0.130                                               | 0.133               | 0.071                       |
| current_companion_recall90              | S139       | 1.000  | 0.069        | -0.106                                              | 0.000               | 0.917                       |
| recall_first_challenger_selected_policy | S142       | 15.000 | 0.065        | 0.136                                               | 0.333               | 0.000                       |
| recall_first_challenger_selected_policy | S139       | 1.000  | 0.084        | -0.076                                              | 0.000               | 0.875                       |

## 5. S142 and S139 assessment

S142:n_ge31=15, ctx_resid=0.773C, challenger_miss=0.333; S139:n_ge31=1, ctx_resid=-0.311C, challenger_miss=0.000

S142 remains the main high-tail underprediction caveat to review. S139 remains low-support for station-specific conclusions; its threshold behavior is dominated by very small event counts and should not be used as broad reliability proof.

## 6. Stability / bootstrap findings

context-adjusted residual stable stations=14; context-adjusted high-tail stable stations=8; challenger probability-error stable stations=1

| station_id | metric_name                                         | probability_case_id                     | n_ge31 | estimate | ci_low | ci_high | stability_label      |
| ---------- | --------------------------------------------------- | --------------------------------------- | ------ | -------- | ------ | ------- | -------------------- |
| S139       | mean_context_adjusted_score_residual_c              |                                         | 1.000  | -0.311   | -0.510 | -0.115  | stable_negative_bias |
| S142       | mean_context_adjusted_score_residual_c              |                                         | 15.000 | 0.773    | 0.532  | 0.999   | stable_positive_bias |
| S139       | mean_context_adjusted_probability_error_obs_minus_p | current_companion_best_f1               | 1.000  | -0.106   | -0.167 | -0.051  | unstable_low_support |
| S139       | miss_rate_at_policy                                 | current_companion_best_f1               | 1.000  | 0.000    | 0.000  | 0.000   | unstable_low_support |
| S142       | mean_context_adjusted_probability_error_obs_minus_p | current_companion_best_f1               | 15.000 | 0.130    | 0.066  | 0.200   | stable_positive_bias |
| S142       | miss_rate_at_policy                                 | current_companion_best_f1               | 15.000 | 0.467    | 0.214  | 0.750   | stable_positive_bias |
| S139       | mean_context_adjusted_probability_error_obs_minus_p | current_companion_recall90              | 1.000  | -0.106   | -0.170 | -0.053  | unstable_low_support |
| S139       | miss_rate_at_policy                                 | current_companion_recall90              | 1.000  | 0.000    | 0.000  | 0.000   | unstable_low_support |
| S142       | mean_context_adjusted_probability_error_obs_minus_p | current_companion_recall90              | 15.000 | 0.130    | 0.065  | 0.204   | stable_positive_bias |
| S142       | miss_rate_at_policy                                 | current_companion_recall90              | 15.000 | 0.133    | 0.000  | 0.333   | no_station_signal    |
| S139       | mean_context_adjusted_probability_error_obs_minus_p | recall_first_challenger_selected_policy | 1.000  | -0.076   | -0.133 | -0.027  | unstable_low_support |
| S139       | miss_rate_at_policy                                 | recall_first_challenger_selected_policy | 1.000  | 0.000    | 0.000  | 0.000   | unstable_low_support |
| S142       | mean_context_adjusted_probability_error_obs_minus_p | recall_first_challenger_selected_policy | 15.000 | 0.136    | 0.069  | 0.209   | stable_positive_bias |
| S142       | miss_rate_at_policy                                 | recall_first_challenger_selected_policy | 15.000 | 0.333    | 0.091  | 0.591   | no_station_signal    |

Bootstrap resamples station date/hour rows with deterministic seeds. Stability labels are diagnostic: they do not establish station-context causal correction.

## 7. Station-context feature availability

forcing_pairing_metadata:6;morphology_proxy:23;station_metadata:7

| feature_class            | available | allowed_for_future_preflight_model | feature_count | max_station_coverage |
| ------------------------ | --------- | ---------------------------------- | ------------- | -------------------- |
| forbidden_leakage        | 1.000     | 0.000                              | 6.000         | NA                   |
| forcing_pairing_metadata | 1.000     | 1.000                              | 6.000         | 27.000               |
| morphology_proxy         | 1.000     | 1.000                              | 23.000        | 27.000               |
| station_metadata         | 1.000     | 1.000                              | 7.000         | 27.000               |
| unavailable              | 0.000     | 0.000                              | 4.000         | 0.000                |

Morphology proxy fields are inventoried only because explicit station-to-cell mapping exists. They are not used here to infer station-level WBGT, and they remain proxy context rather than causal station correction.

## 8. Identifiability decision

| signal_metric                                       | probability_case_id                     | feature_class            | stable_signal_station_count | n_feature_columns_available | max_station_feature_coverage | best_descriptive_rank_feature         | best_abs_spearman_rank_association | identifiability_assessment                        |
| --------------------------------------------------- | --------------------------------------- | ------------------------ | --------------------------- | --------------------------- | ---------------------------- | ------------------------------------- | ---------------------------------- | ------------------------------------------------- |
| mean_context_adjusted_score_residual_c              |                                         | station_metadata         | 14.000                      | 7.000                       | 27.000                       | station_lat                           | 0.458                              | scoped_preflight_model_possible_descriptive_low_n |
| mean_context_adjusted_score_residual_c              |                                         | forcing_pairing_metadata | 14.000                      | 6.000                       | 27.000                       | nearest_grid_distance_m               | 0.205                              | scoped_preflight_model_possible_descriptive_low_n |
| mean_context_adjusted_score_residual_c              |                                         | morphology_proxy         | 14.000                      | 23.000                      | 27.000                       | station_nearest_grid_water_distance_m | 0.614                              | scoped_preflight_model_possible_descriptive_low_n |
| mean_context_adjusted_high_tail_residual_c          |                                         | station_metadata         | 8.000                       | 7.000                       | 27.000                       | station_lon                           | 0.331                              | scoped_preflight_model_possible_descriptive_low_n |
| mean_context_adjusted_high_tail_residual_c          |                                         | forcing_pairing_metadata | 8.000                       | 6.000                       | 27.000                       | nearest_grid_distance_m               | 0.405                              | scoped_preflight_model_possible_descriptive_low_n |
| mean_context_adjusted_high_tail_residual_c          |                                         | morphology_proxy         | 8.000                       | 23.000                      | 27.000                       | station_nearest_grid_water_distance_m | 0.420                              | scoped_preflight_model_possible_descriptive_low_n |
| mean_context_adjusted_probability_error_obs_minus_p | current_companion_best_f1               | station_metadata         | 1.000                       | 7.000                       | 27.000                       | station_lat                           | 0.230                              | signal_not_stable_enough                          |
| mean_context_adjusted_probability_error_obs_minus_p | current_companion_best_f1               | forcing_pairing_metadata | 1.000                       | 6.000                       | 27.000                       | nearest_grid_distance_m               | 0.241                              | signal_not_stable_enough                          |
| mean_context_adjusted_probability_error_obs_minus_p | current_companion_best_f1               | morphology_proxy         | 1.000                       | 23.000                      | 27.000                       | station_nearest_grid_water_distance_m | 0.464                              | signal_not_stable_enough                          |
| mean_context_adjusted_probability_error_obs_minus_p | current_companion_recall90              | station_metadata         | 1.000                       | 7.000                       | 27.000                       | station_lat                           | 0.230                              | signal_not_stable_enough                          |
| mean_context_adjusted_probability_error_obs_minus_p | current_companion_recall90              | forcing_pairing_metadata | 1.000                       | 6.000                       | 27.000                       | nearest_grid_distance_m               | 0.241                              | signal_not_stable_enough                          |
| mean_context_adjusted_probability_error_obs_minus_p | current_companion_recall90              | morphology_proxy         | 1.000                       | 23.000                      | 27.000                       | station_nearest_grid_water_distance_m | 0.464                              | signal_not_stable_enough                          |
| mean_context_adjusted_probability_error_obs_minus_p | recall_first_challenger_selected_policy | station_metadata         | 1.000                       | 7.000                       | 27.000                       | station_lat                           | 0.245                              | signal_not_stable_enough                          |
| mean_context_adjusted_probability_error_obs_minus_p | recall_first_challenger_selected_policy | forcing_pairing_metadata | 1.000                       | 6.000                       | 27.000                       | nearest_grid_distance_m               | 0.178                              | signal_not_stable_enough                          |
| mean_context_adjusted_probability_error_obs_minus_p | recall_first_challenger_selected_policy | morphology_proxy         | 1.000                       | 23.000                      | 27.000                       | station_nearest_grid_water_distance_m | 0.492                              | signal_not_stable_enough                          |

Decision: `A_L2_READY_FOR_SCOPED_PREFLIGHT_MODEL`.

## 9. Whether to proceed to A-L2.1

Proceed only to a scoped A-L2.1 preflight model design, with station_id excluded and no operational claims.

A-L2.1, if opened, should be a scoped preflight model-design/reproducibility gate only. It should exclude `station_id` as a predictive feature, avoid random station/time splits, and preserve the current Level 1 claim boundaries.

## 10. Claim boundaries

- No local 100m WBGT is created or implied.
- No station causal correction is claimed.
- No operational warning probability is claimed.
- The A-L1H.3 challenger is not promoted as canonical replacement.
- No full A-L2 residual ML model is trained in this preflight.

## Output paths

- `outputs/v11_systema_l2_residual/identifiability_preflight/station_context_input_inventory.csv`
- `outputs/v11_systema_l2_residual/identifiability_preflight/station_level_residual_summary.csv`
- `outputs/v11_systema_l2_residual/identifiability_preflight/station_level_probability_error_summary.csv`
- `outputs/v11_systema_l2_residual/identifiability_preflight/station_residual_stability_bootstrap.csv`
- `outputs/v11_systema_l2_residual/identifiability_preflight/station_context_feature_schema.csv`
- `outputs/v11_systema_l2_residual/identifiability_preflight/station_context_identifiability_matrix.csv`
- `outputs/v11_systema_l2_residual/identifiability_preflight/station_context_preflight_report.md`
- `outputs/v11_systema_l2_residual/identifiability_preflight/A_L2_0_STATUS.md`
