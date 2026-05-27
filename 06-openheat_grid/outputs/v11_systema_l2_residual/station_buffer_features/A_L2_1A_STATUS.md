# A-L2.1a Status

Status: BLOCKED_MISSING_SOURCES
Branch: codex/systema-l2-station-buffer-features
Scope: station-local buffer feature builder and QA only; no residual modelling.

Commands run:
- python scripts/v11_l2_run_station_buffer_features.py --config configs/v11/systema_l2_station_buffer_features.yaml

Key results:
- Station count: 27
- Feature groups built: none
- Feature groups unavailable: built_impervious;distance_context;landuse_lcz;morphology;surface;vegetation;water
- All-27 coverage summary: no features have all-27 non-null coverage
- Key exclusions: Toa Payoh-only/AOI-limited sources excluded=40; leakage fields and station_id excluded; no System B/SOLWEIG sources used.

Caveats:
- No model trained.
- No station-context causal correction claimed.
- No station-adjusted WBGT or local 100m WBGT created.
- Toa Payoh-only sources are inventory-only and excluded from 27-station features.

Next recommended action: Add or point to Singapore-wide/all-27 station-local spatial layers, then rerun A-L2.1a before A-L2.1b QA.

Files created / modified:
- outputs/v11_systema_l2_residual/station_buffer_features/station_context_source_inventory.csv
- outputs/v11_systema_l2_residual/station_buffer_features/station_buffer_feature_long.csv
- outputs/v11_systema_l2_residual/station_buffer_features/station_buffer_feature_wide.csv
- outputs/v11_systema_l2_residual/station_buffer_features/station_buffer_feature_schema.csv
- outputs/v11_systema_l2_residual/station_buffer_features/station_buffer_feature_qa.csv
- outputs/v11_systema_l2_residual/station_buffer_features/station_buffer_feature_missingness.csv
- outputs/v11_systema_l2_residual/station_buffer_features/station_buffer_feature_collinearity_screen.csv
- outputs/v11_systema_l2_residual/station_buffer_features/station_buffer_feature_builder_report.md
- outputs/v11_systema_l2_residual/station_buffer_features/A_L2_1A_STATUS.md
- docs/v11/OpenHeat_SystemA_L2_station_buffer_features_CN.md

Safe to commit: controlled config/script/docs and compact CSV/Markdown outputs after review.
Not safe to commit: rasters, raw archives, SOLWEIG outputs, System B outputs, or large forecast/live CSVs.
