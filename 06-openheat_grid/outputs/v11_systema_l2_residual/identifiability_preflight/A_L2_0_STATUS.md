# A-L2.0 Status

Status: PASS
Decision: A_L2_READY_FOR_SCOPED_PREFLIGHT_MODEL
Branch: codex/systema-l2-identifiability-preflight
Scope: station-context residual identifiability preflight only.

Commands run:
- python scripts/v11_l2_run_identifiability_preflight.py --config configs/v11/systema_l2_identifiability_preflight.yaml

Key results:
- context-adjusted residual stable stations=14; context-adjusted high-tail stable stations=8; challenger probability-error stable stations=1
- S142:n_ge31=15, ctx_resid=0.773C, challenger_miss=0.333; S139:n_ge31=1, ctx_resid=-0.311C, challenger_miss=0.000
- forcing_pairing_metadata:6;morphology_proxy:23;station_metadata:7

Caveats:
- No final residual ML model trained.
- No station-context causal correction claimed.
- No local 100m WBGT created.
- P_ge31 remains a retrospective diagnostic companion only.
- A-L1H.3 challenger remains recall-first diagnostic evidence only.

Next recommended action: Proceed only to a scoped A-L2.1 preflight model design, with station_id excluded and no operational claims.

Files created / modified:
- outputs/v11_systema_l2_residual/identifiability_preflight/station_context_input_inventory.csv
- outputs/v11_systema_l2_residual/identifiability_preflight/station_level_residual_summary.csv
- outputs/v11_systema_l2_residual/identifiability_preflight/station_level_probability_error_summary.csv
- outputs/v11_systema_l2_residual/identifiability_preflight/station_residual_stability_bootstrap.csv
- outputs/v11_systema_l2_residual/identifiability_preflight/station_context_feature_schema.csv
- outputs/v11_systema_l2_residual/identifiability_preflight/station_context_identifiability_matrix.csv
- outputs/v11_systema_l2_residual/identifiability_preflight/station_context_preflight_report.md
- outputs/v11_systema_l2_residual/identifiability_preflight/A_L2_0_STATUS.md

Safe to commit: controlled scripts/config/docs and compact CSV/Markdown outputs only after review.
Not safe to commit: raw data, rasters, SOLWEIG outputs, forecast-live hourly CSVs, or archive raw dumps.
