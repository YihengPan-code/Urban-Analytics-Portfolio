# A-L2.1c Status

Status: A_L2_SCOPED_SIGNAL_PROMISING
Branch: codex/systema-l2-scoped-residual-preflight
Scope: station-level n=27 scoped residual preflight only; no station-adjusted WBGT, no local 100 m WBGT, no causal correction.

Commands run:
- python scripts/v11_l2_run_scoped_residual_preflight.py --config configs/v11/systema_l2_scoped_residual_preflight.yaml

Key results:
- n_stations used: mean_context_adjusted_score_residual_c=27;mean_context_adjusted_high_tail_residual_c=26
- best model / feature set by target: high-tail residual:elasticnet/compact_water_road MAE=0.4035 null=0.4316 Spearman=0.3573; score residual:one_feature_ridge/one_feature:landuse_entropy_250m MAE=0.2824 null=0.2873 Spearman=-0.1374
- null baseline comparison: high-tail residual: improvement=0.0281C (6.52%); score residual: improvement=0.0049C (1.69%)
- permutation / bootstrap headline: high-tail residual:p_mae=0.0529,p_spearman=0.0250; score residual:p_mae=0.1419,p_spearman=0.3087; high-tail residual:3 stable-sign coefficients; score residual:1 stable-sign coefficients
- S142/S139 caveats: S142:n_ge31=15,score_resid=0.7726,high_tail=2.2396,low_support=False; S139:n_ge31=1,score_resid=-0.3106,high_tail=0.1109,low_support=True
- A-L2.2 recommendation: Proceed to A-L2.2 only as a protocol review for station-level residual explanation; do not promote to station correction, station-adjusted WBGT, or local 100 m WBGT.

Caveats:
- This is a station-level preflight model, not a promoted Level 2 correction model.
- Coefficients are descriptive and not causal.
- Probability-error summaries are diagnostic only.
- High-tail interpretation must respect low-support station flags.

Files created / modified:
- outputs/v11_systema_l2_residual/scoped_residual_preflight/l2_scoped_model_input_table.csv
- outputs/v11_systema_l2_residual/scoped_residual_preflight/l2_scoped_feature_sets.csv
- outputs/v11_systema_l2_residual/scoped_residual_preflight/l2_scoped_null_baseline_metrics.csv
- outputs/v11_systema_l2_residual/scoped_residual_preflight/l2_scoped_one_feature_metrics.csv
- outputs/v11_systema_l2_residual/scoped_residual_preflight/l2_scoped_ridge_metrics.csv
- outputs/v11_systema_l2_residual/scoped_residual_preflight/l2_scoped_elasticnet_metrics.csv
- outputs/v11_systema_l2_residual/scoped_residual_preflight/l2_scoped_permutation_null.csv
- outputs/v11_systema_l2_residual/scoped_residual_preflight/l2_scoped_bootstrap_stability.csv
- outputs/v11_systema_l2_residual/scoped_residual_preflight/l2_scoped_predictions_loo.csv
- outputs/v11_systema_l2_residual/scoped_residual_preflight/l2_scoped_station_diagnostics.csv
- outputs/v11_systema_l2_residual/scoped_residual_preflight/l2_scoped_decision_matrix.csv
- outputs/v11_systema_l2_residual/scoped_residual_preflight/l2_scoped_residual_preflight_report.md
- outputs/v11_systema_l2_residual/scoped_residual_preflight/A_L2_1C_STATUS.md
- docs/v11/OpenHeat_SystemA_L2_scoped_residual_preflight_CN.md

Safe to commit: controlled config/script/docs and compact CSV/Markdown outputs after review.
Not safe to commit: raw spatial layers, rasters, archives, SOLWEIG/System B outputs, or large forecast/live CSVs.
