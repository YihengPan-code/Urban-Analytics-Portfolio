# v10-gamma robustness audit report

This read-only audit checks transition-class consistency, false-positive candidate definitions, old-top20 baseline rates, and dense-cell edge cases after v10-gamma.

## Inputs
- rank comparison CSV: `outputs\v10_gamma_comparison\v10_vs_v08_rank_comparison.csv`
- v10 hotspot ranking CSV: `outputs\v10_gamma_forecast_live\v10_gamma_hotspot_ranking_with_grid_features.csv`
- morphology shift CSV: `outputs\v10_morphology\v10_old_vs_new_building_morphology_shift.csv`
- old false-positive candidates CSV: `outputs\v10_ranking_audit\v10_old_false_positive_candidates.csv`

## Top-set summary
- Top-N used: **20**
- Old top-N cells: **20**
- v10 top-N cells: **20**
- Top-N overlap: **10 / 20**

## Transition-class counts
```text
                   transition_class  n
fp_candidate_outside_top_transition 21
             entering_v10_top_nonfp  9
                old_top_fp_left_top  9
         old_top_nonfp_retained_top  7
            old_top_fp_retained_top  3
      entering_v10_top_fp_candidate  1
             old_top_nonfp_left_top  1
                              other  1
```

## TP_0315 classification diagnostic
TP_0315 diagnostic: v08_rank=22, v10_rank=14, co_derived_fp_candidate=True, transition_class=entering_v10_top_fp_candidate.

Interpretation: if TP_0315 is listed as `entering_v10_top_fp_candidate`, it should **not** be described as an old-top20 false-positive that remained in the top20. It entered v10 top20 from outside old top20 while carrying the broader v10-beta candidate flag.

## False-positive candidate definition check
Two definitions are reported:

1. `co_derived_fp_candidate`: the v10-beta diagnostic flag / rank-comparison flag. This uses v10 reviewed-DSM information such as coverage gain and building-density gain, so it should be framed as a co-derived diagnostic signal, not a fully independent validation target.
2. `independent_old_dsm_gap_candidate`: old rank ≤ 50 and old-vs-OSM completeness ≤ 0.1. This uses old-rank and old completeness only, not v10 rank; it is a cleaner robustness check.

## Old-topN leaving-rate baseline
```text
                              candidate_definition  candidate_left_topN  candidate_stayed_topN  noncandidate_left_topN  noncandidate_stayed_topN  candidate_leave_rate  noncandidate_leave_rate  fisher_two_sided_p  odds_ratio  top_n
                          co_derived_v10_beta_flag                    9                      3                       1                         7              0.750000                    0.125            0.019767        21.0     20
independent_old_rank_top50_old_completeness_le_0.1                   10                      5                       0                         5              0.666667                    0.000            0.032508         inf     20
                    recomputed_co_derived_criteria                    9                      3                       1                         7              0.750000                    0.125            0.019767        21.0     20
```

Recommended wording: v10-gamma does not independently prove that every diagnosed candidate was a false positive; rather, cells diagnosed as old DSM-gap candidates were disproportionately affected by reviewed-DSM morphology correction.

For the co-derived v10-beta flag, candidate old-top20 cells left the top20 at **9/12 = 0.750**, while non-candidates left at **1/8 = 0.125**.
Fisher exact two-sided p-value for this 2×2 table: **0.0198**. Treat this as a small-sample descriptive check, not a definitive statistical proof.

## Dense / fully-built cell sanity check
Density column used: `v10_building_density`
```text
      density_column  threshold  n_cells  hazard_score_count  hazard_score_mean  hazard_score_median  hazard_score_min  hazard_score_p25  hazard_score_p75  hazard_score_max  max_utci_c_count  max_utci_c_mean  max_utci_c_median  max_utci_c_min  max_utci_c_p25  max_utci_c_p75  max_utci_c_max  svf_count  svf_mean  svf_median  svf_min  svf_p25  svf_p75  svf_max  shade_fraction_count  shade_fraction_mean  shade_fraction_median  shade_fraction_min  shade_fraction_p25  shade_fraction_p75  shade_fraction_max  rank_count  rank_mean  rank_median  rank_min  rank_p25  rank_p75  rank_max  risk_priority_score_count  risk_priority_score_mean  risk_priority_score_median  risk_priority_score_min  risk_priority_score_p25  risk_priority_score_p75  risk_priority_score_max
v10_building_density       0.85        2                   2           0.343709             0.343709               0.0          0.171855          0.515564          0.687418                 1         39.27147           39.27147        39.27147        39.27147        39.27147        39.27147          1  0.435814    0.435814 0.435814 0.435814 0.435814 0.435814                     2             0.071429               0.071429                 0.0            0.035714            0.107143            0.142857           2      540.0        540.0     118.0     329.0     751.0     962.0                          2                  0.383875                    0.383875                  0.16355                 0.273713                 0.494038                 0.604201
v10_building_density       0.95        1                   1           0.000000             0.000000               0.0          0.000000          0.000000          0.000000                 0              NaN                NaN             NaN             NaN             NaN             NaN          0       NaN         NaN      NaN      NaN      NaN      NaN                     1             0.000000               0.000000                 0.0            0.000000            0.000000            0.000000           1      962.0        962.0     962.0     962.0     962.0     962.0                          1                  0.163550                    0.163550                  0.16355                 0.163550                 0.163550                 0.163550
v10_building_density       0.99        1                   1           0.000000             0.000000               0.0          0.000000          0.000000          0.000000                 0              NaN                NaN             NaN             NaN             NaN             NaN          0       NaN         NaN      NaN      NaN      NaN      NaN                     1             0.000000               0.000000                 0.0            0.000000            0.000000            0.000000           1      962.0        962.0     962.0     962.0     962.0     962.0                          1                  0.163550                    0.163550                  0.16355                 0.163550                 0.163550                 0.163550
```

TP_0945 appears in the dense-cell set. It should be treated as a fully/near-fully built edge case rather than a normal open-pedestrian hazard cell.

## Outputs
- transition classes: `outputs\v10_gamma_robustness\v10_gamma_top20_transition_classes.csv`
- false-positive definition check: `outputs\v10_gamma_robustness\v10_gamma_false_positive_definition_check.csv`
- FP vs non-FP contingency: `outputs\v10_gamma_robustness\v10_gamma_fp_vs_nonfp_top20_contingency.csv`
- dense-cell sanity check: `outputs\v10_gamma_robustness\v10_gamma_dense_cell_sanity_check.csv`
- TP_0315 diagnostic: `outputs\v10_gamma_robustness\v10_gamma_tp0315_diagnostic.csv`

## Suggested edits to v10-gamma final findings report
- Split TP_0315 from 'old-top20 retained candidates'; describe it as an `entering_v10_top_fp_candidate` if applicable.
- Explicitly state that the v10-beta false-positive candidate flag is co-derived from reviewed-DSM diagnostics.
- Add the FP-vs-nonFP old-top20 leaving-rate baseline.
- Add a dense-cell edge-case note for TP_0945 and any other cells above the dense thresholds.
- Keep the main v10-gamma conclusion, but phrase it as a disproportionate correction of diagnosed DSM-gap candidates rather than independent proof for every candidate.