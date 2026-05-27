# B8.6g Vector/Compact Feature Acquisition

Status: `B86G_FEATURE_ACQUISITION_PASS`

## 1. Why B8.6g follows B8.6f

B8.6f kept AOI preflight and B9 blocked because spatial holdout, anchor underprediction, neutral false-promotion, and feature representation gaps remained unresolved. B8.6g therefore acquires compact/vector-derived cell features only; it does not train a final surrogate or create AOI-wide predictions.

## 2. Source discovery results

- Sources scanned: 1256
- Usable safe-to-inspect sources: 982
- Raster/QGIS/SOLWEIG/raw roots were skipped by guardrail status rather than read.

| path | extension | likely_role | read_status | safety_status |
| --- | --- | --- | --- | --- |
| configs/v071_risk_exposure_config.example.json | .json | unusable_or_unknown | READ_OK | SAFE_TO_INSPECT |
| configs/v07_grid_features_config.example.json | .json | cell_grid_geometry | READ_OK | SAFE_TO_INSPECT |
| configs/v07_grid_features_config.sample_fixture.json | .json | cell_grid_geometry | READ_OK | SAFE_TO_INSPECT |
| configs/v09_alpha_config.example.json | .json | unusable_or_unknown | READ_OK | SAFE_TO_INSPECT |
| configs/v09_beta_config.example.json | .json | unusable_or_unknown | READ_OK | SAFE_TO_INSPECT |
| configs/v09_beta_threshold_config.example.json | .json | unusable_or_unknown | READ_OK | SAFE_TO_INSPECT |
| configs/v09_gamma_overhead_aware_config.example.json | .json | overhead_vector | READ_OK | SAFE_TO_INSPECT |
| configs/v09_gamma_solweig_config.example.json | .json | building_footprint_height | READ_OK | SAFE_TO_INSPECT |
| configs/v10/v10_alpha2_qa_config.example.json | .json | unusable_or_unknown | READ_OK | SAFE_TO_INSPECT |
| configs/v10/v10_alpha3_manual_qa_config.example.json | .json | unusable_or_unknown | READ_OK | SAFE_TO_INSPECT |
| configs/v10/v10_alpha_augmented_dsm_config.example.json | .json | building_footprint_height | READ_OK | SAFE_TO_INSPECT |
| configs/v10/v10_augmented_dsm_config.example.json | .json | building_footprint_height | READ_OK | SAFE_TO_INSPECT |

## 3. Feature family readiness

| feature_family | priority | b86g_computability_status | n150_coverage_fraction | n300_coverage_fraction | source_status | proxy_status |
| --- | --- | --- | --- | --- | --- | --- |
| pedestrian-accessible shaded fraction | high | COMPUTED_PROXY | 1.0 | 1.0 | COMPACT_VECTOR_DERIVED_PROXY | STRONG_COMPACT_VECTOR_PROXY |
| connected shade corridor / shade continuity | high | NOT_AVAILABLE | 0.0 | 0.0 | NOT_AVAILABLE_REQUIRES_PEDESTRIAN_SHADE_NETWORK | NOT_AVAILABLE |
| overhead geometry shape descriptors | high | COMPUTED | 1.0 | 1.0 | COMPACT_VECTOR_DERIVED_NO_PERIMETER | VECTOR_DERIVED_COMPACT |
| sunlit-hot-pocket area fraction | high | COMPUTED_PROXY | 1.0 | 1.0 | COMPUTED | PROXY_ONLY |
| local boundary / edge context | medium | COMPUTED_PROXY | 1.0 | 1.0 | COMPACT_PROXY_ONLY | PROXY_ONLY |
| neighbourhood-scale context | medium | COMPUTED_PROXY | 1.0 | 1.0 | CENTROID_RADIUS_CONTEXT | PROXY_ONLY |
| tree/building shadow interaction | high | COMPUTED_PROXY | 1.0 | 1.0 | COMPUTED | PROXY_ONLY |
| canyon orientation / height roughness | high | COMPUTED_PROXY | 1.0 | 1.0 | LIMITED_COMPACT_HEIGHT_PROXY_NO_AXIS | PROXY_ONLY |
| typology-specific geometry | medium | COMPUTED_PROXY | 1.0 | 1.0 | COMPUTED | PROXY_ONLY |

## 4. Computed vs blocked features

Computed or partially computed families: pedestrian-accessible shaded fraction, overhead geometry shape descriptors, sunlit-hot-pocket area fraction, local boundary / edge context, neighbourhood-scale context, tree/building shadow interaction, canyon orientation / height roughness, typology-specific geometry.

Blocked families: connected shade corridor / shade continuity.

## 5. N150 feature coverage

N150 feature dataset shape: (150, 41).

| feature_family | n150_coverage_fraction | n_non_null_features | proxy_status | blocked_reason |
| --- | --- | --- | --- | --- |
| pedestrian-accessible shaded fraction | 1.0 | 2 | STRONG_COMPACT_VECTOR_PROXY | proxy-only; requires formal feature-upgraded retest before promotion |
| connected shade corridor / shade continuity | 0.0 | 0 | NOT_AVAILABLE | required vector/compact source not available |
| overhead geometry shape descriptors | 1.0 | 3 | VECTOR_DERIVED_COMPACT | nan |
| sunlit-hot-pocket area fraction | 1.0 | 2 | PROXY_ONLY | proxy-only; requires formal feature-upgraded retest before promotion |
| local boundary / edge context | 1.0 | 3 | PROXY_ONLY | proxy-only; requires formal feature-upgraded retest before promotion |
| neighbourhood-scale context | 1.0 | 3 | PROXY_ONLY | proxy-only; requires formal feature-upgraded retest before promotion |
| tree/building shadow interaction | 1.0 | 2 | PROXY_ONLY | proxy-only; requires formal feature-upgraded retest before promotion |
| canyon orientation / height roughness | 1.0 | 2 | PROXY_ONLY | proxy-only; requires formal feature-upgraded retest before promotion |
| typology-specific geometry | 1.0 | 3 | PROXY_ONLY | proxy-only; requires formal feature-upgraded retest before promotion |

## 6. N300 candidate feature coverage

N300 candidate feature dataset shape: (150, 41).

| feature_family | n300_coverage_fraction | n_non_null_features | proxy_status | recommended_next_action |
| --- | --- | --- | --- | --- |
| pedestrian-accessible shaded fraction | 1.0 | 2 | STRONG_COMPACT_VECTOR_PROXY | use in B8.6g2/B8.6f2 diagnostic retest |
| connected shade corridor / shade continuity | 0.0 | 0 | NOT_AVAILABLE | acquire missing vector source before retest |
| overhead geometry shape descriptors | 1.0 | 3 | VECTOR_DERIVED_COMPACT | use in B8.6g2/B8.6f2 diagnostic retest |
| sunlit-hot-pocket area fraction | 1.0 | 2 | PROXY_ONLY | use in B8.6g2/B8.6f2 diagnostic retest |
| local boundary / edge context | 1.0 | 3 | PROXY_ONLY | use in B8.6g2/B8.6f2 diagnostic retest |
| neighbourhood-scale context | 1.0 | 3 | PROXY_ONLY | use in B8.6g2/B8.6f2 diagnostic retest |
| tree/building shadow interaction | 1.0 | 2 | PROXY_ONLY | use in B8.6g2/B8.6f2 diagnostic retest |
| canyon orientation / height roughness | 1.0 | 2 | PROXY_ONLY | use in B8.6g2/B8.6f2 diagnostic retest |
| typology-specific geometry | 1.0 | 3 | PROXY_ONLY | use in B8.6g2/B8.6f2 diagnostic retest |

## 7. Failure-context feature coverage

- Anchors: 5 anchor rows joined; mean family coverage=0.889.
- Neutral false-promotion / near-zero cells: 15 neutral/near-zero rows joined; mean family coverage=0.889.
- Weak spatial bins: 4 weak-bin summaries joined; mean family coverage=0.889.

| row_type | cell_id | diagnostic_role | spatial_bin | failure_type | feature_family_coverage_fraction |
| --- | --- | --- | --- | --- | --- |
| cell_failure_context | TP_0037 | anchor_reference | west_south | anchor-underprediction | 0.8888888888888888 |
| cell_failure_context | TP_0141 | anchor_reference | east_south | anchor-underprediction | 0.8888888888888888 |
| cell_failure_context | TP_0433 | anchor_reference | east_south | anchor-underprediction | 0.8888888888888888 |
| cell_failure_context | TP_0542 | anchor_reference | east_north | anchor-underprediction | 0.8888888888888888 |
| cell_failure_context | TP_0857 | anchor_reference | east_north | anchor-underprediction | 0.8888888888888888 |
| cell_failure_context | TP_0115 | known_neutral_reference | east_south | neutral-false-promotion | 0.8888888888888888 |
| cell_failure_context | TP_0301 | known_neutral_reference | west_south | neutral-false-promotion | 0.8888888888888888 |
| cell_failure_context | TP_0326 | known_neutral_reference | west_south | neutral-false-promotion | 0.8888888888888888 |
| cell_failure_context | TP_0366 | known_neutral_reference | east_south | neutral-context-missing | 0.8888888888888888 |
| cell_failure_context | TP_0492 | known_neutral_reference | east_north | neutral-false-promotion | 0.8888888888888888 |
| cell_failure_context | TP_0565 | known_neutral_reference | west_north | neutral-context-missing | 0.8888888888888888 |
| cell_failure_context | TP_0676 | known_neutral_reference | west_north | neutral-false-promotion | 0.8888888888888888 |
| cell_failure_context | TP_0960 | known_neutral_reference | west_north | neutral-context-missing | 0.8888888888888888 |
| cell_failure_context | TP_0986 | known_neutral_reference | east_north | neutral-context-missing | 0.8888888888888888 |
| cell_failure_context | TP_0005 | near_zero_false_promotion_context | west_south | neutral-false-promotion | 0.8888888888888888 |
| cell_failure_context | TP_0799 | near_zero_false_promotion_context | east_north | neutral-false-promotion | 0.8888888888888888 |
| cell_failure_context | TP_0379 | near_zero_false_promotion_context | west_south | neutral-false-promotion | 0.8888888888888888 |
| cell_failure_context | TP_0318 | near_zero_false_promotion_context | east_south | neutral-false-promotion | 0.8888888888888888 |

## 8. Feature gap closure matrix

| gap_family | B8.6f_priority | feature_computed | proxy_only | closure_status | recommended_next_lane |
| --- | --- | --- | --- | --- | --- |
| pedestrian-accessible shaded fraction | high | True | True | PARTIAL_PROXY_ONLY | B8.6g2/B8.6f2 feature-upgraded compact retest |
| connected shade corridor / shade continuity | high | False | False | NOT_AVAILABLE_REQUIRES_SOURCE | B8.7-N300-PRE or acquire missing vector source |
| overhead geometry shape descriptors | high | True | False | CLOSED_WITH_VECTOR_FEATURE | B8.6g2/B8.6f2 feature-upgraded compact retest |
| sunlit-hot-pocket area fraction | high | True | True | PARTIAL_PROXY_ONLY | B8.6g2/B8.6f2 feature-upgraded compact retest |
| local boundary / edge context | medium | True | True | PARTIAL_PROXY_ONLY | B8.6g2/B8.6f2 feature-upgraded compact retest |
| neighbourhood-scale context | medium | True | True | PARTIAL_PROXY_ONLY | B8.6g2/B8.6f2 feature-upgraded compact retest |
| tree/building shadow interaction | high | True | True | PARTIAL_PROXY_ONLY | B8.6g2/B8.6f2 feature-upgraded compact retest |
| canyon orientation / height roughness | high | True | True | PARTIAL_PROXY_ONLY | B8.6g2/B8.6f2 feature-upgraded compact retest |
| typology-specific geometry | medium | True | True | PARTIAL_PROXY_ONLY | B8.6g2/B8.6f2 feature-upgraded compact retest |

## 9. Retest readiness and next lanes

- Retest readiness: `PARTIAL_RETEST_ONLY`.
- Recommended next lane: B8.6g2 partial feature-upgraded retest plus B8.7-N300-PRE design freeze.
- B8.7-N300-PRE remains useful because connected shade corridor/network sources are still not available and B8.6g created no new SOLWEIG labels.
- B8.6h scope-limited preflight remains low/conditional and cannot bypass a feature-upgraded retest.

## 10. Claim boundaries

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
