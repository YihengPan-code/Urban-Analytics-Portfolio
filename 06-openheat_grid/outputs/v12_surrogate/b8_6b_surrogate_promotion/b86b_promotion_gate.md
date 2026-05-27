# B8.6b Promotion Gate

Generated: 2026-05-27 18:11:49

Status: `B86B_WEAK_NEEDS_FEATURE_UPGRADE`

## Gate Result

- Best primary model: `hist_gradient_boosting_regressor`
- Forcing-day holdout MAE=0.0666, R2=0.850, Spearman=0.864, top10pct=1.000, improvement=70.0%.
- cell_group_holdout Spearman=0.462, top10pct=0.333; spatial_holdout Spearman=0.386, top10pct=0.312; typology_holdout Spearman=0.391, top10pct=0.124; hour_holdout Spearman=0.902, top10pct=0.960
- Most predictable target: base_tmrt_p90_c (Spearman=0.867); primary p90 Spearman=0.864.
- AOI-wide preflight recommendation: AOI-wide preflight is not recommended; upgrade compact features and re-test forcing-day/spatial/typology generalisation.
- B9 status: `BLOCKED`.

## Boundaries

- Not B9.
- Not local WBGT.
- Not risk.
- Not observed truth.
- Not causal feature importance.
- No raster committed.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
