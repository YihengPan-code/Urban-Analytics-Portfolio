# B8.6f Surrogate Closure Mega-Suite

Status: `B86F_SURROGATE_CLOSURE_PASS`

## 1. Why B8.6f Follows B8.6e

B8.6e diagnosed spatial failure and proposed a targeted N300 v1 design, but it
also left over-optimistic wording around safe engineered features. B8.6f
therefore consolidates the evidence, corrects that caveat, rebalances N300
candidate roles, and tests abstention gates without creating AOI-wide or B9
outputs.

## 2. What B8.6e Proved And Did Not Prove

| caveat_id | caveat_headline | required_action |
| --- | --- | --- |
| safe_feature_probe_not_spatial_closure | B8.6e safe physical engineered features did not close spatial_holdout. | Override over-optimistic B8.6e wording in B8.6f reports. |
| typology_gain_diagnostic_only | Typology Spearman improvement is diagnostic, not production-ready. | Keep AOI-wide and B9 blocked. |
| coordinate_distance_diagnostic_only | Coordinate and distance features are diagnostic-only. | Do not use them as validated spatial-closure features. |
| n300_v1_role_skew | N300 v1 is candidate-design only and too skewed to typology_gap_fill. | Create role-quota-balanced N300 v2; do not create a manifest or runner. |
| aoi_b9_blocked | AOI-wide/B9 remains blocked. | Do not create AOI-wide predictions, B9 outputs, WBGT, hazard, risk, or coupling output. |

## 3. Spatial Failure Synthesis

| spatial_bin | mean_abs_error | Spearman | top10pct_overlap | false_promotion_rate | dominant_blocker | b86f_decision |
| --- | --- | --- | --- | --- | --- | --- |
| west_north | 0.154 | 0.074 | 0.250 | 0.240 | feature_representation|sample_coverage|neutral_boundary | keep_spatial_holdout_blocking_aoi_preflight |
| west_south | 0.218 | 0.082 | 0.000 | 0.115 | feature_representation|sample_coverage | keep_spatial_holdout_blocking_aoi_preflight |
| east_south | 0.174 | 0.244 | 0.500 | 0.182 | feature_representation | keep_spatial_holdout_blocking_aoi_preflight |
| east_north | 0.351 | 0.288 | 0.500 | 0.054 | feature_representation|anchor_representation | keep_spatial_holdout_blocking_aoi_preflight |

## 4. Anchor / Neutral Failure Synthesis

| cell_id | diagnostic_role | spatial_bin | typology | mean_abs_error | failure_rate | failure_type | severity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP_0037 | anchor_reference | west_south | other | 0.397 | 1.000 | anchor-underprediction | high |
| TP_0141 | anchor_reference | east_south | residential | 0.258 | 0.900 | anchor-underprediction | high |
| TP_0433 | anchor_reference | east_south | tree_shaded_reference | 0.620 | 1.000 | anchor-underprediction | high |
| TP_0542 | anchor_reference | east_north | river_edge_shaded_walkway | 0.495 | 1.000 | anchor-underprediction | high |
| TP_0857 | anchor_reference | east_north | hdb_canyon | 2.539 | 1.000 | anchor-underprediction | high |
| TP_0115 | known_neutral_reference | east_south | water | 1.137 | 1.000 | neutral-false-promotion | high |
| TP_0301 | known_neutral_reference | west_south | residential | 1.110 | 1.000 | neutral-false-promotion | high |
| TP_0326 | known_neutral_reference | west_south | stable_high_rise_residential_estate | 0.932 | 1.000 | neutral-false-promotion | high |
| TP_0366 | known_neutral_reference | east_south | exposed_bus_stop_waiting_node |  |  | neutral-context-missing | review |
| TP_0492 | known_neutral_reference | east_north | dense_shaded_low_svf | 0.580 | 1.000 | neutral-false-promotion | high |
| TP_0565 | known_neutral_reference | west_north | confident_hot_anchor |  |  | neutral-context-missing | review |
| TP_0676 | known_neutral_reference | west_north | residential | 1.257 | 1.000 | neutral-false-promotion | high |
| TP_0960 | known_neutral_reference | west_north | park_open_space |  |  | neutral-context-missing | review |
| TP_0986 | known_neutral_reference | east_north | clean_confident_hot_anchor_null_control |  |  | neutral-context-missing | review |
| TP_0005 | near_zero_false_promotion_context | west_south | residential | 1.637 | 1.000 | neutral-false-promotion | high |
| TP_0799 | near_zero_false_promotion_context | east_north | residential | 1.623 | 1.000 | neutral-false-promotion | high |
| TP_0379 | near_zero_false_promotion_context | west_south | residential | 1.591 | 1.000 | neutral-false-promotion | high |
| TP_0318 | near_zero_false_promotion_context | east_south | water | 1.394 | 1.000 | neutral-false-promotion | high |
| TP_0254 | near_zero_false_promotion_context | east_south | residential | 1.372 | 1.000 | neutral-false-promotion | high |
| TP_0053 | near_zero_false_promotion_context | east_south | residential | 1.339 | 1.000 | neutral-false-promotion | high |

## 5. Safe Feature Probe Verdict

| verdict_topic | feature_variant | Spearman_delta_vs_b86d | top10_delta_vs_b86d | verdict | production_boundary |
| --- | --- | --- | --- | --- | --- |
| spatial_holdout | safe_physical_engineered | 0.004 | -0.062 | not_improved | diagnostic_only_not_validated_spatial_closure |
| cell_group_holdout | safe_physical_engineered | -0.082 | -0.133 | not_improved | diagnostic_only_not_validated_spatial_closure |
| typology_holdout | safe_physical_engineered | 0.100 | -0.267 | partial_diagnostic_spearman_gain_but_topk_worsened | diagnostic_only_not_validated_spatial_closure |
| coordinate_and_distance_features | coordinate_context_diagnostic|safe_physical_plus_distance_diagnostic | 0.052 | -0.333 | diagnostic_only | diagnostic_only_not_production_predictors |
| overall_safe_feature_probe | b86e_probe |  |  | do_not_treat_as_validated_spatial_closure | aoi_and_b9_blocked |

## 6. N300 V1 Audit And V2 Role-Balanced Design

V2 selected 150 additional candidate-design cells. It is not run-ready
and does not create a SOLWEIG manifest or runner.

| primary_role | target_count | final_selected_count | final_deficit_or_surplus |
| --- | --- | --- | --- |
| typology_gap_fill | 50.000 | 50.000 | 0.000 |
| spatial_gap_fill | 30.000 | 30.000 | 0.000 |
| anchor_like_replication | 25.000 | 25.000 | 0.000 |
| neutral_boundary_replication | 25.000 | 25.000 | 0.000 |
| sparse_feature_space | 10.000 | 10.000 | 0.000 |
| control_cell | 10.000 | 10.000 | 0.000 |

| primary_role | count |
| --- | --- |
| typology_gap_fill | 50.000 |
| spatial_gap_fill | 30.000 |
| anchor_like_replication | 25.000 |
| neutral_boundary_replication | 25.000 |
| sparse_feature_space | 10.000 |
| control_cell | 10.000 |

## 7. Feature Acquisition Register

| feature_family | priority | expected_benefit | implementation_lane | likely_failure_modes_addressed |
| --- | --- | --- | --- | --- |
| pedestrian-accessible shaded fraction | high | high | B8.6g_vector_compact_feature_acquisition | neutral-false-promotion|anchor-underprediction|feature-distribution-shift |
| connected shade corridor / shade continuity | high | high | B8.6g_vector_compact_feature_acquisition | spatial-bin-out-of-domain|anchor-underprediction|sample-support-low |
| overhead geometry shape descriptors | high | medium-high | B8.6g_vector_compact_feature_acquisition | feature-distribution-shift|target-role-mismatch |
| sunlit-hot-pocket area fraction | high | high | B8.6g_vector_compact_feature_acquisition | neutral-false-promotion|target-role-mismatch|spatial-bin-out-of-domain |
| local boundary / edge context | medium | medium | B8.6g_vector_compact_feature_acquisition | east_south_neutral_false_promotion|feature-distribution-shift |
| neighbourhood-scale context | medium | medium | B8.7-N300-PRE_or_B8.6g | spatial-bin-out-of-domain|sample-support-low |
| tree/building shadow interaction | high | high | B8.6g_vector_compact_feature_acquisition | anchor-underprediction|feature-distribution-shift |
| canyon orientation / height roughness | high | medium-high | B8.6g_vector_compact_feature_acquisition | anchor-underprediction|spatial-bin-out-of-domain |
| typology-specific geometry | medium | medium | B8.6g_or_B8.7-N300-PRE | target-role-mismatch|sample-support-low|feature-distribution-shift |

## 8. Abstention Gate Diagnostics

| gate_level | split_family | retained_coverage_fraction | MAE_retained | Spearman_retained | top10pct_overlap_retained | neutral_false_promotion_rate_retained |
| --- | --- | --- | --- | --- | --- | --- |
| baseline_no_gate | overall | 1.000 | 0.194 | 0.450 | 0.667 | 0.180 |
| moderate_gate | overall | 0.564 | 0.111 | 0.603 | 0.667 | 0.013 |
| strict_gate | overall | 0.000 |  |  |  |  |
| baseline_no_gate | spatial_holdout | 1.000 | 0.225 | 0.190 | 0.400 | 0.236 |
| moderate_gate | spatial_holdout | 0.553 | 0.124 | 0.353 | 0.556 | 0.016 |
| strict_gate | spatial_holdout | 0.000 |  |  |  |  |
| baseline_no_gate | cell_group_holdout | 1.000 | 0.174 | 0.455 | 0.533 | 0.186 |
| moderate_gate | cell_group_holdout | 0.553 | 0.104 | 0.634 | 0.667 | 0.028 |
| strict_gate | cell_group_holdout | 0.000 |  |  |  |  |
| baseline_no_gate | typology_holdout | 1.000 | 0.425 | 0.250 | 0.357 | 0.288 |
| moderate_gate | typology_holdout | 0.611 | 0.213 | 0.425 | 0.375 | 0.024 |
| strict_gate | typology_holdout | 0.000 |  |  |  |  |
| baseline_no_gate | forcing_day_holdout | 1.000 | 0.086 | 0.709 | 0.800 | 0.099 |
| moderate_gate | forcing_day_holdout | 0.553 | 0.061 | 0.791 | 0.667 | 0.000 |
| strict_gate | forcing_day_holdout | 0.000 |  |  |  |  |
| baseline_no_gate | hour_holdout | 1.000 | 0.088 | 0.715 | 0.800 | 0.102 |
| moderate_gate | hour_holdout | 0.553 | 0.060 | 0.794 | 0.889 | 0.000 |
| strict_gate | hour_holdout | 0.000 |  |  |  |  |

## 9. Scope-Limited Surrogate Diagnostic

| gate_level | split_family | retained_coverage_fraction | Spearman_delta_vs_baseline | top10_delta_vs_baseline | topk_screening_suitability | scope_status |
| --- | --- | --- | --- | --- | --- | --- |
| baseline_no_gate | overall | 1.000 | 0.000 | 0.000 | weak_diagnostic_screening_candidate | SCOPE_LIMITED_DIAGNOSTIC_ONLY |
| moderate_gate | overall | 0.564 | 0.153 | 0.000 | diagnostic_screening_candidate_only | SCOPE_LIMITED_DIAGNOSTIC_ONLY |
| strict_gate | overall | 0.000 |  |  | not_suitable_for_screening | NOT_READY |
| baseline_no_gate | spatial_holdout | 1.000 | 0.000 | 0.000 | not_suitable_for_screening | SCOPE_LIMITED_DIAGNOSTIC_ONLY |
| moderate_gate | spatial_holdout | 0.553 | 0.163 | 0.156 | weak_diagnostic_screening_candidate | SCOPE_LIMITED_DIAGNOSTIC_ONLY |
| strict_gate | spatial_holdout | 0.000 |  |  | not_suitable_for_screening | NOT_READY |
| baseline_no_gate | cell_group_holdout | 1.000 | 0.000 | 0.000 | weak_diagnostic_screening_candidate | SCOPE_LIMITED_DIAGNOSTIC_ONLY |
| moderate_gate | cell_group_holdout | 0.553 | 0.179 | 0.133 | diagnostic_screening_candidate_only | SCOPE_LIMITED_DIAGNOSTIC_ONLY |
| strict_gate | cell_group_holdout | 0.000 |  |  | not_suitable_for_screening | NOT_READY |
| baseline_no_gate | typology_holdout | 1.000 | 0.000 | 0.000 | not_suitable_for_screening | SCOPE_LIMITED_DIAGNOSTIC_ONLY |
| moderate_gate | typology_holdout | 0.611 | 0.175 | 0.018 | not_suitable_for_screening | SCOPE_LIMITED_DIAGNOSTIC_ONLY |
| strict_gate | typology_holdout | 0.000 |  |  | not_suitable_for_screening | NOT_READY |
| baseline_no_gate | forcing_day_holdout | 1.000 | 0.000 | 0.000 | diagnostic_screening_candidate_only | SCOPE_LIMITED_DIAGNOSTIC_ONLY |
| moderate_gate | forcing_day_holdout | 0.553 | 0.083 | -0.133 | diagnostic_screening_candidate_only | NOT_READY |
| strict_gate | forcing_day_holdout | 0.000 |  |  | not_suitable_for_screening | NOT_READY |
| baseline_no_gate | hour_holdout | 1.000 | 0.000 | 0.000 | diagnostic_screening_candidate_only | SCOPE_LIMITED_DIAGNOSTIC_ONLY |
| moderate_gate | hour_holdout | 0.553 | 0.080 | 0.089 | diagnostic_screening_candidate_only | SCOPE_LIMITED_DIAGNOSTIC_ONLY |
| strict_gate | hour_holdout | 0.000 |  |  | not_suitable_for_screening | NOT_READY |

## 10. AOI Preflight Readiness

| readiness_item | status | evidence | blocker | allowed_future_lane |
| --- | --- | --- | --- | --- |
| spatial_holdout | BLOCKED | west_north Spearman=0.074, top10=0.250 | spatial-bin-out-of-domain and weak ranking support | B8.6g|B8.7-N300-PRE |
| typology_holdout | DIAGNOSTIC_ONLY | Typology Spearman improved, but top-k support worsened; not production-ready. | Spearman-only improvement is insufficient when top-k worsens. | B8.6g |
| cell_group_holdout | BLOCKED | cell_group_holdout did not receive validated closure from safe physical engineered features. | safe feature probe did not improve cell-group evidence. | B8.6f2_model_retest_after_inputs |
| neutral false-promotion | BLOCKED | 11 neutral/near-zero rows remain in the B8.6f matrix. | known neutral and near-zero cells can still be promoted as cooling. | B8.7-N300-PRE|B8.6h_conditional |
| anchor underprediction | BLOCKED | 5 anchor rows remain medium/high severity. | TP_0857/TP_0542/TP_0433/TP_0037/TP_0141 anchor contexts remain required gates. | B8.6g|B8.7-N300-PRE |
| feature gap closure | NOT_CLOSED | 6 high-priority feature families remain. | current safe engineered features did not close spatial holdout. | B8.6g |
| N300 design | READY_FOR_REVIEW_NOT_EXECUTION | 150 role-balanced additional candidate-design cells selected. | candidate design is not a SOLWEIG manifest or run package. | B8.7-N300-PRE |
| feature acquisition | RECOMMENDED | Feature acquisition register and spec are actionable. | feature representation is the dominant blocker. | B8.6g |
| uncertainty/abstention gate | DIAGNOSTIC_ONLY | Best spatial gated Spearman=0.353, coverage=0.553 | gate is not a production or AOI-wide prediction path. | B8.6h_conditional |
| claim boundary | PASS | B8.6f creates compact diagnostic/design outputs only. | none if boundaries are preserved. | B8.6g|B8.7-N300-PRE |
| overall_aoi_preflight | AOI_PREFLIGHT_BLOCKED | Spatial, neutral, anchor, and feature-gap blockers remain. | insufficient spatial closure and safety diagnostics. | B8.6g|B8.7-N300-PRE |

AOI preflight status: `AOI_PREFLIGHT_BLOCKED`.

## 11. Recommended Next Lane

| future_lane | recommended_priority | why | codex_prompt_path |
| --- | --- | --- | --- |
| B8.6g vector/compact feature acquisition | high | Feature representation gaps are the dominant blocker and B8.6e safe features did not close spatial holdout. | outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_codex_prompt_B86G_feature_acquisition.md |
| B8.7-N300-PRE targeted sample design freeze | high | N300 v2 is role-balanced and current compact features cannot close spatial/anchor/neutral failures alone. | outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_codex_prompt_B87_N300_PRE.md |
| B8.6h scope-limited surrogate dry-run preflight | low_conditional | Abstention gate is useful diagnostically, but should only proceed if retained metrics become clearly strong. |  |
| B8.6f2 model retest | medium_after_new_inputs | Model retest is useful only after B8.6g features or reviewed N300 labels exist. |  |
| no-go / wait | fallback | If feature acquisition or N300 review is not approved, AOI/B9 should remain blocked. |  |

Recommended order: B8.6g vector/compact feature acquisition, then B8.7-N300-PRE
targeted design freeze if reviewers approve the role-balanced candidate list.

## 12. Claim Boundaries

- Not B9.
- Not AOI-wide prediction.
- Not local WBGT.
- Not hazard_score or risk_score.
- Not observed truth.
- Not causal feature importance.
- No raster read/open/create/copy/write.
- No QGIS or SOLWEIG.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
