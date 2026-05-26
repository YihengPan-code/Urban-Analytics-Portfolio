# Sprint B6 - System B N150 Sample Design + Manifest

## Status
PASS

## Scope
- N150 sample design + manifest only
- no QGIS
- no SOLWEIG
- no raw raster reads
- no local WBGT
- no hazard_score
- no risk_score
- no surrogate
- no System A/B coupling

## Inputs
B5 target family is frozen around `tmrt_p90_c`, `delta_tmrt_p90_c`, and `m_rad_pct01`. Completed N24 rows are reused as seed / continuity labels and are not rerun in this sprint.

## Candidate universe
- Candidate cells with feature sources: 986
- Eligible cells after hard exclusions / feature checks: 981
- Excluded cells recorded: 5
- Feature source and missingness are written to `n150_feature_source_map.csv` and `n150_sampling_feature_missingness.csv`.

## Sampling strategy
N24 retention, diagnostic quotas, feature-space extremes, and `qmc_lhs` feature-space fill were used. Geographic coordinates were included as normalized sampling features when available.

## Selected N150
- Total selected = 150
- Retained N24 = 24
- New cells = 126
- Alternates count = 30
- Replaced-out cells absent = True

## Coverage
Primary stratum counts: `{'shaded_canopy_low_svf': 114, 'open_hardscape_high_svf': 17, 'grass_or_open_park': 7, 'max_extreme_probe_proxy': 4, 'water_edge_or_blue_green_mixed': 3, 'road_edge_or_high_road_fraction': 2, 'dense_built_or_low_open_pixel': 1, 'background_feature_space_fill': 1, 'overhead_or_transport_structure': 1}`. Feature distribution, quantile-bin, stratum, and geographic diagnostics are written in the B6 output directory.

## Auto QA
Selected cells with at least one automated QA flag: 51. No full manual QA is required; optional spot-check suggestions are capped at 15 cells.

## Surrogate readiness
This creates a future label design and advisory split labels only. It is not surrogate training and does not finalize B8 cross-validation.

## Manifest
- Full matrix rows = 1500
- New-run-only rows = 1260
- Base new manifest rows = 630
- Overhead new manifest rows = 630
- Raw outputs marked do_not_commit
- B7 should execute the new-run-only matrix and merge with existing N24 summaries.

## Claim boundaries
No local WBGT, no hazard_score, no risk_score, no surrogate, no A/B coupling.

## Next recommended action
B7 - execute N150 new-run-only SOLWEIG matrix in QGIS Desktop Python Console, then aggregate and merge with existing N24 summaries.
