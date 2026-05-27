# B8.6 Promotion Gate

Status: `B86_WEAK_BASELINE_NEEDS_N150_MULTIFORCING`

## Gate Result

- Protocol-ready artifacts: yes
- Baseline promising under cell/typology/hour holdouts: yes
- Forcing-day holdout: `FUTURE_REQUIRED` because existing N150 labels are single-forcing.
- B9 status: `BLOCKED`.

## Target-Card Verdict

| target            | available   | best_model                       |   mean_main_MAE |   mean_main_spearman | b86_target_card_verdict                     |
|:------------------|:------------|:---------------------------------|----------------:|---------------------:|:--------------------------------------------|
| delta_tmrt_p90_c  | True        | random_forest_regressor          |        0.161646 |             0.611277 | PRIMARY_REMAINS_B8_6_TARGET_CARD            |
| tmrt_p90_c        | True        | random_forest_regressor          |        2.64406  |             0.900496 | SECONDARY_CONTEXT_ONLY_NOT_PROMOTION_TARGET |
| delta_tmrt_mean_c | True        | random_forest_regressor          |        0.2595   |             0.866057 | SECONDARY_CONTEXT_ONLY_NOT_PROMOTION_TARGET |
| delta_tmrt_p95_c  | True        | random_forest_regressor          |        0.125057 |             0.501852 | SECONDARY_CONTEXT_ONLY_NOT_PROMOTION_TARGET |
| m_rad_pct01       | True        | hist_gradient_boosting_regressor |        0.150172 |             0.690169 | SECONDARY_CONTEXT_ONLY_NOT_PROMOTION_TARGET |

## Promotion Boundary

B8.6 may support a reviewed surrogate protocol baseline, but it does not authorize AOI-wide prediction, B9, local WBGT, risk, hazard_score, causal feature importance, or System A/B coupling.

## Next Action

Run a future N150 multi-forcing precheck and controlled execution lane before any surrogate promotion beyond this weak/single-forcing baseline gate.
