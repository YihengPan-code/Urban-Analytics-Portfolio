# A-L2.1a-S1 Status

Status: PASS_FEATURE_TABLE
Branch: codex/systema-l2-station-buffer-source-acquisition
Scope: station-local source acquisition/extraction only; no residual modelling.

Commands run:
- python scripts/v11_l2_run_station_buffer_source_acquisition.py --config configs/v11/systema_l2_station_buffer_source_acquisition.yaml

Key results:
- Station count: 27
- Feature groups built with all-27 coverage: buildings;green;landuse;roads;water
- Feature groups still unavailable: none
- Assumptions: CRS read from source metadata.;Area fractions use deterministic grid sampling of source polygons within EPSG:3414 circular buffers; no clipped raw geometries are written.;Road lengths use exact line-circle segment clipping in EPSG:3414.;OSM landuse polygons are treated as partial context where polygons exist, not as a complete LCZ product.

Caveats:
- No model trained.
- No station-context causal correction claimed.
- No station-adjusted WBGT or local 100 m WBGT created.
- Raw spatial source layers remain outside the repo.
- Toa Payoh-only/AOI-limited features remain excluded.

Next recommended action: Proceed to A-L2.1b QA/collinearity review using S1 tables; keep A-L2.1c residual modelling out of this lane.

Files created / modified:
- outputs/v11_systema_l2_residual/station_buffer_features_s1/station_context_source_acquisition_inventory.csv
- outputs/v11_systema_l2_residual/station_buffer_features_s1/station_buffer_source_normalization.csv
- outputs/v11_systema_l2_residual/station_buffer_features_s1/station_buffer_feature_long_s1.csv
- outputs/v11_systema_l2_residual/station_buffer_features_s1/station_buffer_feature_wide_s1.csv
- outputs/v11_systema_l2_residual/station_buffer_features_s1/station_buffer_feature_schema_s1.csv
- outputs/v11_systema_l2_residual/station_buffer_features_s1/station_buffer_feature_qa_s1.csv
- outputs/v11_systema_l2_residual/station_buffer_features_s1/station_buffer_missing_sources_next_actions.csv
- outputs/v11_systema_l2_residual/station_buffer_features_s1/station_buffer_feature_builder_s1_report.md
- outputs/v11_systema_l2_residual/station_buffer_features_s1/A_L2_1A_S1_STATUS.md
- docs/v11/OpenHeat_SystemA_L2_station_buffer_source_acquisition_CN.md

Safe to commit: controlled config/script/docs and compact CSV/Markdown outputs after review.
Not safe to commit: raw spatial layers, rasters, archives, SOLWEIG/System B outputs, or large forecast/live CSVs.
