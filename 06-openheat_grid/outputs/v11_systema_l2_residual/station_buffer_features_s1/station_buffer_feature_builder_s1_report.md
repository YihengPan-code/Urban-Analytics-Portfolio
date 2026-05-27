# System A A-L2.1a-S1 Station-Local Source Acquisition

Generated: 2026-05-27
Decision status: `PASS_FEATURE_TABLE`
Branch: `codex/systema-l2-station-buffer-source-acquisition`
Config: `configs/v11/systema_l2_station_buffer_source_acquisition.yaml`

## Why A-L2.1a Was Blocked

The previous A-L2.1a gate was `BLOCKED_MISSING_SOURCES` because the available in-repo spatial files were Toa Payoh-only, AOI-limited, unknown-coverage, or metadata-only. They could not defensibly produce all-27 station-local buffer features.

## Local Sources Used

| source_name | source_group | source_format | row_count | usable_geometry_count | source_crs | station_coverage_count | coverage_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| osm_station_context_buildings | buildings | .gpkg | 7557 | 7557 | EPSG:4326 | 27 | bbox_covers_all_27_stations |
| osm_station_context_green | green | .gpkg | 385 | 385 | EPSG:4326 | 27 | bbox_covers_all_27_stations |
| osm_station_context_landuse | landuse | .gpkg | 2349 | 2349 | EPSG:4326 | 27 | bbox_covers_all_27_stations |
| osm_station_context_roads | roads | .gpkg | 20485 | 20485 | EPSG:4326 | 27 | bbox_covers_all_27_stations |
| osm_station_context_water | water | .gpkg | 270 | 270 | EPSG:4326 | 27 | bbox_covers_all_27_stations |

## Source Coverage Summary

| source_group | coverage_status | source_count |
| --- | --- | --- |
| buildings | bbox_covers_all_27_stations | 1 |
| buildings | missing_local_source | 2 |
| green | bbox_covers_all_27_stations | 1 |
| green | missing_local_source | 2 |
| landuse | bbox_covers_all_27_stations | 1 |
| landuse | missing_local_source | 2 |
| roads | bbox_covers_all_27_stations | 1 |
| roads | missing_local_source | 2 |
| water | bbox_covers_all_27_stations | 1 |
| water | missing_local_source | 2 |

## Normalization Summary

| source_name | source_group | input_crs | crs_action | geometry_type_counts | attribute_classification_status | assumptions |
| --- | --- | --- | --- | --- | --- | --- |
| osm_station_context_buildings | buildings | EPSG:4326 | projected_to_EPSG_3414 | MultiPolygon:8;Point:5;Polygon:7544 | usable | CRS read from source metadata. |
| osm_station_context_green | green | EPSG:4326 | projected_to_EPSG_3414 | MultiPolygon:5;Point:5;Polygon:375 | usable | CRS read from source metadata. |
| osm_station_context_landuse | landuse | EPSG:4326 | projected_to_EPSG_3414 | LineString:158;MultiPolygon:9;Point:623;Polygon:1559 | usable | CRS read from source metadata. |
| osm_station_context_roads | roads | EPSG:4326 | projected_to_EPSG_3414 | LineString:17406;MultiPolygon:1;Point:3038;Polygon:40 | usable | CRS read from source metadata. |
| osm_station_context_water | water | EPSG:4326 | projected_to_EPSG_3414 | LineString:189;Point:4;Polygon:77 | usable | CRS read from source metadata. |

## Feature Groups With All-27 Coverage

buildings;green;landuse;roads;water

## Feature Groups Still Unavailable

none

## Schema Snapshot

| feature_column | feature_group | n_stations_non_null | missing_fraction | allowed_for_future_model | leakage_check |
| --- | --- | --- | --- | --- | --- |
| building_count_50m | buildings | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| building_count_100m | buildings | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| building_count_250m | buildings | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| building_count_500m | buildings | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| building_footprint_fraction_50m | buildings | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| building_footprint_fraction_100m | buildings | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| building_footprint_fraction_250m | buildings | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| building_footprint_fraction_500m | buildings | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| distance_to_major_road_m_50m | roads | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| distance_to_major_road_m_100m | roads | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| distance_to_major_road_m_250m | roads | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| distance_to_major_road_m_500m | roads | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| distance_to_park_or_green_m_50m | green | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| distance_to_park_or_green_m_100m | green | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| distance_to_park_or_green_m_250m | green | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| distance_to_park_or_green_m_500m | green | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| distance_to_water_m_50m | water | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| distance_to_water_m_100m | water | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| distance_to_water_m_250m | water | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| distance_to_water_m_500m | water | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| green_space_fraction_50m | green | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| green_space_fraction_100m | green | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| green_space_fraction_250m | green | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| green_space_fraction_500m | green | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| landuse_entropy_50m | landuse | 24 | 0.111111 | False | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| landuse_entropy_100m | landuse | 26 | 0.037037 | False | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| landuse_entropy_250m | landuse | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| landuse_entropy_500m | landuse | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| landuse_majority_50m | landuse | 24 | 0.111111 | False | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| landuse_majority_100m | landuse | 26 | 0.037037 | False | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| landuse_majority_250m | landuse | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| landuse_majority_500m | landuse | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| major_road_length_m_50m | roads | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| major_road_length_m_100m | roads | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| major_road_length_m_250m | roads | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| major_road_length_m_500m | roads | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| road_density_m_per_ha_50m | roads | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| road_density_m_per_ha_100m | roads | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| road_density_m_per_ha_250m | roads | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |
| road_density_m_per_ha_500m | roads | 27 | 0.000000 | True | PASS_NO_FORBIDDEN_FEATURE_TOKEN |

_Showing 40 of 48 rows._

## Missing Sources / Next Actions

| feature_group | status | usable_sources | next_action |
| --- | --- | --- | --- |
| water | BUILT_ALL_27 | osm_station_context_water | Proceed to A-L2.1b QA review for this group; do not train residual models in S1. |
| green | BUILT_ALL_27 | osm_station_context_green | Proceed to A-L2.1b QA review for this group; do not train residual models in S1. |
| roads | BUILT_ALL_27 | osm_station_context_roads | Proceed to A-L2.1b QA review for this group; do not train residual models in S1. |
| buildings | BUILT_ALL_27 | osm_station_context_buildings | Proceed to A-L2.1b QA review for this group; do not train residual models in S1. |
| landuse | BUILT_ALL_27 | osm_station_context_landuse | Proceed to A-L2.1b QA review for this group; do not train residual models in S1. |

## QA

| qa_metric | qa_value | qa_status | notes |
| --- | --- | --- | --- |
| station_count | 27 | PASS | Unique station centroids from v09 station pairs. |
| buffer_count | 4 | PASS | Buffers: 50;100;250;500 m. |
| station_crs | EPSG:4326 | PASS | Station coordinates read as EPSG:4326 and projected to EPSG:3414 for metric buffers. |
| metric_buffer_crs | EPSG:3414 | PASS | SVY21 projection used before metric buffers/lengths. |
| all_27_feature_groups | buildings;green;landuse;roads;water | PASS | Groups with at least one non-leakage all-27 feature. |
| missing_fraction_max | 0.111111 | PASS | Maximum schema missing fraction. |
| constant_feature_count | 0 | PASS | Constant features are flagged for later QA, not removed here. |
| source_count_readable | 5 | PASS | Readable local source files only; raw spatial layers remain outside repo. |
| source_assumptions | CRS read from source metadata. | PASS | CRS/attribute assumptions captured in normalization inventory. |
| forbidden_features | none | PASS | No official WBGT, residual, event label, station_id predictive feature, System B, or SOLWEIG feature is emitted. |
| raw_spatial_layers_written | none | PASS | Only compact CSV/Markdown summaries are written. |
| model_training | none | PASS | No residual ML model was trained. |
| toa_payoh_only_features | excluded | PASS | Toa Payoh-only/AOI-limited features remain excluded from all-27 station-context features. |

## Assumptions

- CRS read from source metadata.
- Area fractions use deterministic grid sampling of source polygons within EPSG:3414 circular buffers; no clipped raw geometries are written.
- Road lengths use exact line-circle segment clipping in EPSG:3414.
- OSM landuse polygons are treated as partial context where polygons exist, not as a complete LCZ product.

## Claim Boundaries

- Toa Payoh-only features remain excluded because this lane requires all-27 station-local source coverage.
- No model was trained.
- No station-context causal correction is claimed.
- No station-adjusted WBGT was created.
- No local 100 m WBGT was created.
- No System B or SOLWEIG outputs were touched or used.
