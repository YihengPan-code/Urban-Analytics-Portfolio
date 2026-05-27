# System A A-L2.1c Scoped Station-Level Residual Preflight

Generated: 2026-05-27
Decision status: `A_L2_SCOPED_SIGNAL_PROMISING`
Branch: `codex/systema-l2-scoped-residual-preflight`
Config: `configs/v11/systema_l2_scoped_residual_preflight.yaml`

## 1. Why this follows A-L2.1b

A-L2.0 found stable station-level residual structure after Level 1 controls, especially for the score residual and high-tail residual. A-L2.1a-S1 then built all-27 station-local OSM buffer features, and A-L2.1b narrowed them to a small non-redundant primary set. This A-L2.1c lane only asks whether those station-local context features explain station-level residual ranking or magnitude better than null station mean baselines under n=27 constraints.

This is not a promoted Level 2 correction model.

## 2. Input table and station unit

The model input table has one row per station, not hourly rows. `station_id` is retained only as an identifier and is never passed to a model. The score-residual target has 27 station rows. The high-tail target has 26 usable rows because stations with no high-tail support can have missing high-tail residuals. Low-support flags are retained for interpretation; 19 stations are flagged.

| station_id | station_name | n_rows | n_ge31 | low_support_warning_flag | mean_context_adjusted_score_residual_c | mean_context_adjusted_high_tail_residual_c |
| --- | --- | --- | --- | --- | --- | --- |
| S124 | Upper Changi Road North | 62.000000 | 0.000000 | 1.000000 | -0.322673 |  |
| S125 | Woodlands Street 13 | 62.000000 | 8.000000 | 1.000000 | -0.086004 | 0.466778 |
| S126 | Old Chua Chu Kang Road | 62.000000 | 8.000000 | 1.000000 | -0.013654 | 0.809962 |
| S127 | Stadium Road | 62.000000 | 10.000000 | 0.000000 | 0.360424 | 0.547811 |
| S128 | Bishan Street | 62.000000 | 11.000000 | 0.000000 | 0.121816 | 1.158280 |
| S129 | Bedok North Street 2 | 62.000000 | 10.000000 | 0.000000 | 0.402433 | 0.841193 |
| S130 | West Coast Road | 62.000000 | 6.000000 | 1.000000 | 0.300331 | 0.153110 |
| S132 | Jurong West Street 93 | 62.000000 | 9.000000 | 1.000000 | 0.173415 | 0.138712 |
| S135 | Mandai Wildlife Reserve | 62.000000 | 11.000000 | 0.000000 | -0.173508 | 0.933017 |
| S137 | Sakra Road | 62.000000 | 13.000000 | 0.000000 | 0.774637 | 1.347448 |

_Showing 10 of 27 rows._

## 3. Feature sets and target definitions

Primary targets are `mean_context_adjusted_score_residual_c` and `mean_context_adjusted_high_tail_residual_c`. Probability-error and miss/false-alarm station summaries remain diagnostic only and are not modelled as primary targets.

| feature_set_id | feature_set_role | decision_eligible | feature_count | feature_columns |
| --- | --- | --- | --- | --- |
| null_baseline | null_baseline | 1.000000 | 0.000000 |  |
| primary_8 | primary | 1.000000 | 8.000000 | building_footprint_fraction_250m;distance_to_park_or_green_m_250m;green_space_fraction_250m;landuse_entropy_250m;major_road_length_m_250m;road_density_m_per_ha_250m;distance_to_water_m_250m;water_fraction_250m |
| water_sensitivity | sensitivity | 1.000000 | 8.000000 | building_footprint_fraction_250m;distance_to_park_or_green_m_250m;green_space_fraction_250m;landuse_entropy_250m;major_road_length_m_250m;road_density_m_per_ha_250m;distance_to_water_m_250m;water_fraction_100m |
| road_sensitivity | sensitivity | 1.000000 | 8.000000 | building_footprint_fraction_250m;distance_to_park_or_green_m_250m;green_space_fraction_250m;landuse_entropy_250m;major_road_length_m_250m;distance_to_water_m_250m;water_fraction_250m;road_density_m_per_ha_500m |
| road_length_sensitivity | sensitivity | 1.000000 | 8.000000 | building_footprint_fraction_250m;distance_to_park_or_green_m_250m;green_space_fraction_250m;landuse_entropy_250m;major_road_length_m_250m;distance_to_water_m_250m;water_fraction_250m;road_length_m_500m |
| compact_water_road | compact | 1.000000 | 4.000000 | distance_to_water_m_250m;water_fraction_250m;road_density_m_per_ha_250m;building_footprint_fraction_250m |
| building_50m_exploratory | exploratory_sensitivity | 0.000000 | 2.000000 | building_count_50m;building_footprint_fraction_50m |
| one_feature:building_footprint_fraction_250m | one_feature | 1.000000 | 1.000000 | building_footprint_fraction_250m |
| one_feature:distance_to_park_or_green_m_250m | one_feature | 1.000000 | 1.000000 | distance_to_park_or_green_m_250m |
| one_feature:green_space_fraction_250m | one_feature | 1.000000 | 1.000000 | green_space_fraction_250m |
| one_feature:landuse_entropy_250m | one_feature | 1.000000 | 1.000000 | landuse_entropy_250m |
| one_feature:major_road_length_m_250m | one_feature | 1.000000 | 1.000000 | major_road_length_m_250m |
| one_feature:road_density_m_per_ha_250m | one_feature | 1.000000 | 1.000000 | road_density_m_per_ha_250m |
| one_feature:distance_to_water_m_250m | one_feature | 1.000000 | 1.000000 | distance_to_water_m_250m |
| one_feature:water_fraction_250m | one_feature | 1.000000 | 1.000000 | water_fraction_250m |

## 4. Validation design

All reported model metrics use leave-one-station-out validation. Ridge and ElasticNet use standardized features with inner leave-one-station-out hyperparameter selection inside each outer training fold. The null baseline predicts the mean of the outer training stations. There is no random train/test split and no same-row fitting/evaluation claim.

The permutation null and bootstrap stability are run only for the best eligible non-null model per primary target, using fixed full-data-selected hyperparameters for computationally bounded preflight resampling. This is disclosed as a preflight approximation and is not causal evidence.

## 5. Null baseline results

| target_label | n_stations | mae | rmse | bias_pred_minus_obs | r2 | spearman_observed_vs_predicted | s142_abs_error | s139_abs_error | no_s142_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| score residual | 27.000000 | 0.287287 | 0.346418 | 0.000000 | -0.078402 | -1.000000 | 0.802283 | 0.322546 | 0.267480 |
| high-tail residual | 26.000000 | 0.431620 | 0.542148 | 0.000000 | -0.081600 | -1.000000 | 1.696596 | 0.517278 | 0.381021 |

## 6. One-feature screen

| target_label | model_family | feature_set_id | n_stations | mae | spearman_observed_vs_predicted | selected_params_summary | no_s142_mae |
| --- | --- | --- | --- | --- | --- | --- | --- |
| high-tail residual | one_feature_ridge | one_feature:water_fraction_250m | 26.000000 | 0.422483 | -0.770940 | alpha=10.0000:1;alpha=100.0000:25 | 0.371224 |
| high-tail residual | one_feature_ridge | one_feature:distance_to_water_m_250m | 26.000000 | 0.422662 | 0.283419 | alpha=0.0100:3;alpha=1.0000:12;alpha=10.0000:11 | 0.378894 |
| high-tail residual | one_feature_ridge | one_feature:road_density_m_per_ha_250m | 26.000000 | 0.426356 | 0.107009 | alpha=0.0100:6;alpha=1.0000:9;alpha=10.0000:11 | 0.379195 |
| high-tail residual | one_feature_ridge | one_feature:major_road_length_m_250m | 26.000000 | 0.429058 | -0.517949 | alpha=100.0000:26 | 0.378908 |
| score residual | one_feature_ridge | one_feature:landuse_entropy_250m | 27.000000 | 0.282430 | -0.137363 | alpha=0.0100:4;alpha=1.0000:8;alpha=10.0000:13;alpha=100.0000:2 | 0.262795 |
| score residual | one_feature_ridge | one_feature:distance_to_park_or_green_m_250m | 27.000000 | 0.289534 | -0.819292 | alpha=100.0000:27 | 0.269636 |
| score residual | one_feature_ridge | one_feature:road_density_m_per_ha_250m | 27.000000 | 0.290011 | -0.885226 | alpha=100.0000:27 | 0.270406 |
| score residual | one_feature_ridge | one_feature:distance_to_water_m_250m | 27.000000 | 0.290059 | -0.967643 | alpha=100.0000:27 | 0.270168 |

## 7. Ridge and ElasticNet scoped results

Ridge top rows:

| target_label | feature_set_id | n_stations | mae | rmse | spearman_observed_vs_predicted | selected_params_summary | no_s142_mae |
| --- | --- | --- | --- | --- | --- | --- | --- |
| high-tail residual | water_sensitivity | 26.000000 | 0.414703 | 0.520953 | 0.137778 | alpha=100.0000:26 | 0.365715 |
| high-tail residual | primary_8 | 26.000000 | 0.437828 | 0.539673 | 0.141880 | alpha=10.0000:1;alpha=100.0000:25 | 0.390160 |
| high-tail residual | compact_water_road | 26.000000 | 0.442428 | 0.544950 | 0.201368 | alpha=10.0000:19;alpha=100.0000:7 | 0.394948 |
| high-tail residual | road_sensitivity | 26.000000 | 0.448197 | 0.547967 | 0.130256 | alpha=10.0000:5;alpha=100.0000:21 | 0.401212 |
| score residual | building_50m_exploratory | 27.000000 | 0.280357 | 0.338459 | -0.399878 | alpha=100.0000:27 | 0.260975 |
| score residual | water_sensitivity | 27.000000 | 0.295599 | 0.358379 | -0.586081 | alpha=100.0000:27 | 0.275641 |
| score residual | primary_8 | 27.000000 | 0.296065 | 0.358537 | -0.580586 | alpha=100.0000:27 | 0.276241 |
| score residual | road_length_sensitivity | 27.000000 | 0.296301 | 0.358918 | -0.564103 | alpha=100.0000:27 | 0.276228 |

ElasticNet top rows:

| target_label | feature_set_id | n_stations | mae | rmse | spearman_observed_vs_predicted | selected_params_summary | no_s142_mae |
| --- | --- | --- | --- | --- | --- | --- | --- |
| high-tail residual | compact_water_road | 26.000000 | 0.403497 | 0.506591 | 0.357265 | alpha=0.1000,l1_ratio=0.1000:21;alpha=0.1000,l1_ratio=0.5000:5 | 0.362705 |
| high-tail residual | road_sensitivity | 26.000000 | 0.421373 | 0.517260 | 0.260171 | alpha=0.1000,l1_ratio=0.5000:7;alpha=0.1000,l1_ratio=0.9000:16;alpha=1.0000,l1_ratio=0.1000:3 | 0.378692 |
| high-tail residual | road_length_sensitivity | 26.000000 | 0.421373 | 0.517260 | 0.260171 | alpha=0.1000,l1_ratio=0.5000:7;alpha=0.1000,l1_ratio=0.9000:16;alpha=1.0000,l1_ratio=0.1000:3 | 0.378692 |
| high-tail residual | building_50m_exploratory | 26.000000 | 0.444729 | 0.553518 | -0.978803 | alpha=0.0100,l1_ratio=0.1000:2;alpha=1.0000,l1_ratio=0.1000:1;alpha=1.0000,l1_ratio=0.5000:23 | 0.394654 |
| score residual | building_50m_exploratory | 27.000000 | 0.281259 | 0.341015 | -0.416361 | alpha=0.1000,l1_ratio=0.5000:22;alpha=0.1000,l1_ratio=0.9000:3;alpha=1.0000,l1_ratio=0.1000:1;alpha=1.0000,l1_ratio=0.5000:1 | 0.262052 |
| score residual | compact_water_road | 27.000000 | 0.287287 | 0.346418 | -1.000000 | alpha=0.1000,l1_ratio=0.5000:1;alpha=0.1000,l1_ratio=0.9000:15;alpha=1.0000,l1_ratio=0.1000:6;alpha=1.0000,l1_ratio=0.5000:5 | 0.267480 |
| score residual | primary_8 | 27.000000 | 0.291039 | 0.355558 | -1.000000 | alpha=0.1000,l1_ratio=0.5000:1;alpha=1.0000,l1_ratio=0.5000:26 | 0.271376 |
| score residual | water_sensitivity | 27.000000 | 0.291039 | 0.355558 | -1.000000 | alpha=0.1000,l1_ratio=0.5000:1;alpha=1.0000,l1_ratio=0.5000:26 | 0.271376 |

ElasticNet is included only as a cautious sparse linear sensitivity model. It is not a promotion signal by itself under n=27.

## 8. Permutation null and bootstrap stability

| target_label | model_family | feature_set_id | iterations | observed_fixed_mae | permutation_mae_p50 | observed_fixed_spearman | permutation_spearman_p50 | permutation_p_value_mae_directional | permutation_p_value_spearman_directional |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high-tail residual | elasticnet | compact_water_road | 1000.000000 | 0.402679 | 0.470881 | 0.362735 | -0.144274 | 0.052947 | 0.024975 |
| score residual | one_feature_ridge | one_feature:landuse_entropy_250m | 1000.000000 | 0.279168 | 0.295597 | -0.077534 | -0.285714 | 0.141858 | 0.308691 |

Bootstrap coefficient stability is descriptive only:

| target_label | model_family | feature_set_id | feature_column | full_data_standardized_coef | same_sign_as_full_fraction | selection_fraction_nonzero | coef_ci_low | coef_ci_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high-tail residual | elasticnet | compact_water_road | distance_to_water_m_250m | -0.206652 | 0.981000 | 0.987000 | -0.385457 | -0.011617 |
| high-tail residual | elasticnet | compact_water_road | road_density_m_per_ha_250m | -0.152322 | 0.972000 | 0.988000 | -0.296590 | 0.000000 |
| high-tail residual | elasticnet | compact_water_road | building_footprint_fraction_250m | -0.076209 | 0.761000 | 0.933000 | -0.242855 | 0.073199 |
| high-tail residual | elasticnet | compact_water_road | water_fraction_250m | 0.000000 | 0.146000 | 0.854000 | -0.105368 | 0.122976 |
| score residual | one_feature_ridge | one_feature:landuse_entropy_250m | landuse_entropy_250m | 0.068299 | 0.847000 | 1.000000 | -0.063497 | 0.176510 |

## 9. S142 / S139 caveats

| station_id | n_ge31 | low_support_warning_flag | mean_context_adjusted_score_residual_c | mean_context_adjusted_high_tail_residual_c | score_stability_label | high_tail_stability_label | best_score_abs_error_c | best_high_tail_abs_error_c |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S139 | 1.000000 | 1.000000 | -0.310600 | 0.110892 | stable_negative_bias | unstable_low_support | 0.239789 | 0.462521 |
| S142 | 15.000000 | 0.000000 | 0.772569 | 2.239617 | stable_positive_bias | stable_positive_bias | 0.792939 | 1.423291 |

S142 remains the main high-tail underprediction caveat station. S139 remains low-support for station-specific conclusions, especially probability and threshold behavior. Any apparent station-context explanation must survive no-S142 checks before it can be considered promising.

## 10. A-L2.2 decision matrix

| target_label | n_stations | null_mae | best_model_family | best_feature_set_id | best_mae | mae_improvement_fraction | best_spearman | no_s142_mae_improvement_fraction | permutation_p_value_mae_directional | permutation_p_value_spearman_directional | target_decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high-tail residual | 26.000000 | 0.431620 | elasticnet | compact_water_road | 0.403497 | 0.065158 | 0.357265 | 0.048071 | 0.052947 | 0.024975 | A_L2_SCOPED_SIGNAL_PROMISING |
| score residual | 27.000000 | 0.287287 | one_feature_ridge | one_feature:landuse_entropy_250m | 0.282430 | 0.016907 | -0.137363 | 0.017514 | 0.141858 | 0.308691 | A_L2_NOT_IDENTIFIABLE |

Recommendation: Proceed to A-L2.2 only as a protocol review for station-level residual explanation; do not promote to station correction, station-adjusted WBGT, or local 100 m WBGT.

## 11. Claim boundaries

- No station-adjusted WBGT is created.
- No station-context causal correction is claimed.
- No local 100 m WBGT is created.
- No operational forecast or public health warning claim is made.
- Station context is used only as residual explanation under station-level n=27 constraints.
