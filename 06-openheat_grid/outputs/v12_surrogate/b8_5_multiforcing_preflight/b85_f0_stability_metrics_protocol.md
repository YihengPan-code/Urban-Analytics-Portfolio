# B8.5-F0 Stability Metrics Protocol

Generated: 2026-05-26

## Scope

This is a post-SOLWEIG analysis protocol for a later B8.5 execution lane. B8.5-F0 did not execute QGIS or SOLWEIG, did not create rasters, did not create local WBGT, and did not create `hazard_score`, `risk_score`, System A/B coupling, or AOI-wide inference outputs.

## Planned Forcing Days

| forcing_day_id | date | regime_label | n_station_hours | n_ge31_obs | selection_basis |
| --- | --- | --- | ---: | --- | --- |
| `FD01_high_shortwave_hot_20260507` | 2026-05-07 | `high_shortwave_hot` | 135 | 198 | GE31-rich high-shortwave / hot forcing day with official-WBGT GE31 support in the available v09 paired station file. |
| `FD02_humid_hot_cloudy_or_diffuse_20260508` | 2026-05-08 | `humid_hot_cloudy_or_diffuse` | 135 | not_available | Contrast day for humidity/cloud/diffuse/radiation diversity. Official GE31 observations are unavailable in the local paired station file, so this day is not treated as GE31-rich. |

Recommended hours: `10,12,13,15,16` SGT. Scenarios: `base`, `overhead_as_canopy`.

## Required Post-Execution Inputs

- Completed run matrix with one row per `cell_id x forcing_day_id x hour_sgt x scenario`.
- Aggregated Tmrt summaries keyed by `run_id`, `cell_id`, `forcing_day_id`, `date`, `hour_sgt`, and `scenario`.
- Per-forcing-day `delta_tmrt_p90_c` and `m_rad_pct01` computed within the same forcing day, hour, and scenario reference domain.

## Metrics

1. Rank correlation of `delta_tmrt_p90_c` across forcing days: compute Spearman correlations for each forcing-day pair at cell level, with all hours/scenarios pooled only as a diagnostic view.
2. Spearman by hour/scenario: compute pairwise Spearman separately for every `hour_sgt x scenario` slice to detect timing-specific instability.
3. Top-k overlap: compare top 10%, top 20%, and top 5 cells by `delta_tmrt_p90_c` across forcing days; report Jaccard overlap and shared-cell counts.
4. Sign stability: flag cells where `delta_tmrt_p90_c` changes sign across forcing days for the same hour/scenario.
5. `m_rad_pct01` rank stability: compute Spearman and absolute percentile-rank drift for `m_rad_pct01`; summarize median, p90, and max drift.
6. Cell class stability: assign within-day classes such as high, middle, and low radiative modifier; report class transition matrices across forcing days.
7. Unstable-cell inventory: list cells with high rank drift, class flips, sign flips, or repeated top-k disagreement, including their N24 provenance and typology notes.
8. Forcing-day interaction notes: describe whether instability concentrates in a scenario, hour, or typology. Keep this descriptive; do not infer causal real-world heat-risk drivers.

## Suggested Review Thresholds

- Treat low rank correlation, low top-k overlap, or many sign/class flips as a blocker for B9 AOI-wide inference.
- Do not promote System B beyond internal SOLWEIG-derived modifier ranking unless multi-forcing stability is accepted by review.
- Keep `delta_tmrt_p90_c` as a radiative modifier label; do not convert it to local WBGT.
