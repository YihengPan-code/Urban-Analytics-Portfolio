# B8.6d Recommendation

Generated: 2026-05-27 19:28:28

Status basis: `B86C_TWO_STAGE_PROMISING`

- Feature-set evidence: minimal_physics_interpretable/random_forest_regressor vs baseline random_forest_regressor: supporting Spearman 0.441 (+0.001), top10pct 0.245 (-0.024), MAE gain -1.4%.
- Two-stage evidence: full_safe_compact, threshold=0.05, random_forest_classifier+random_forest_regressor: neutral_accuracy=0.770, supporting Spearman=0.489, top10pct=0.361, anchor_MAE=0.673.
- Recommendation: Recommend B8.6d to formalize the two-stage neutral-boundary workflow before any AOI-wide preflight; B9 remains blocked.

## Boundaries

- B8.6d may be an improved surrogate workflow review.
- It must not create AOI-wide prediction or B9 outputs.
- It must not create local WBGT, hazard_score, risk_score, observed-truth claims, causal feature-importance claims, or System A/B coupling.
