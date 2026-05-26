# Sprint B4 — N24 System B Target Robustness Re-audit

## Status
PASS

## Scope
- reads completed N24 SOLWEIG summaries
- no QGIS
- no SOLWEIG rerun
- no raw rasters
- no local WBGT
- no hazard_score
- no risk_score
- no surrogate
- no System A/B coupling

## Inputs
B3 status is PASS. Focus summary rows: `240`. Base-vs-overhead delta rows: `120`. Unique cells: `24`. Scenarios: `base, overhead_as_canopy`. Hours: `10, 12, 13, 15, 16`.

## Target availability
Available target metrics include `tmrt_mean_c`, `tmrt_p50_c`, `tmrt_p75_c`, `tmrt_p90_c`, `tmrt_p95_c`, `tmrt_max_c`, and threshold-area metrics `pct_pixels_tmrt_ge_40/45/50/55`.
Availability rows marked available: `100` / `100`.

## Rank robustness
Mean Spearman: p90 vs p75 `0.931`, p90 vs p95 `0.858`, p90 vs max `0.660`, p90 vs mean `0.906`, p90 vs pct_ge_50 `0.896`, p90 vs pct_ge_55 `0.906`.
p90 is interpreted as a simulation-derived mixed-cell upper-tail radiant exposure target, not observed truth.

## Top-k overlap
Mean top6 Jaccard for p90 vs pct_ge_50 is `0.477`. See `n24_target_topk_overlap.csv` for top6 and top3 cell sets by metric pair.

## Hour stability
p90 mean cross-hour Spearman is `0.993` and mean top6 Jaccard is `0.943` across 10/12/13/15/16.
Consistent p90 top6 cells across at least 3 of 5 hours: `TP_0037, TP_0059, TP_0088, TP_0301, TP_0565, TP_0986, TP_0627, TP_0960`.

## Tail heterogeneity
Tail classes by cell/scenario: `{'threshold_area_hot': 20, 'uniform_hot': 12, 'mixed_cell_upper_tail': 6, 'max_only_extreme': 6, 'mostly_shaded_low_tail': 4}`.
The audit separates broad hot cells, mixed cells where p90 reveals residual hot pockets, and max-only extremes where `tmrt_max_c` may be too outlier-sensitive.

## Overhead sensitivity
Strongest mean p90 cooling cells: TP_0575 (-2.90), TP_0037 (-2.70), TP_0542 (-2.54), TP_0088 (-1.93), TP_0141 (-0.28).
Strongest threshold-area ge50 reductions: TP_0088 (-59.34), TP_0575 (-43.06), TP_0037 (-17.23), TP_0059 (-10.76), TP_0676 (-3.07).
Largest rank shifts: TP_0575 pct_pixels_tmrt_ge_50 h16 (13), TP_0088 pct_pixels_tmrt_ge_50 h12 (13), TP_0037 tmrt_p90_c h16 (13), TP_0088 pct_pixels_tmrt_ge_55 h12 (13), TP_0088 pct_pixels_tmrt_ge_50 h16 (12).
The `overhead_as_canopy` scenario is a sensitivity scenario, not absolute truth.

## Threshold-area companions
Aggregate threshold recommendations: `{'pct_pixels_tmrt_ge_40': 'optional_companion', 'pct_pixels_tmrt_ge_45': 'optional_companion', 'pct_pixels_tmrt_ge_50': 'optional_companion', 'pct_pixels_tmrt_ge_55': 'optional_companion'}`.
Threshold-area metrics are useful companions because they express area share above radiant thresholds and can reveal cases where p90 is high but the hot area is small, or p90 is moderate but a broad area exceeds a threshold.

## Replacement and legacy sanity
Replacement cells checked: `TP_0141, TP_0301, TP_0773, TP_0676, TP_0575`.
Legacy / continuity anchors checked: `TP_0565, TP_0986, TP_0088, TP_0433, TP_0575`.
These are sanity checks only; they do not validate observed truth.

## Target decision
`tmrt_p90_c` recommended status: `n24_supported_primary_candidate`.
Required/retained companions include p75, p95, mean, max sensitivity, threshold-area metrics, and derived/provisional delta or modifier metrics where explicitly caveated.
No final AOI-wide canonical target is claimed here.

## Claim boundaries
Allowed:
- N24 SOLWEIG-derived target robustness evidence
- N24-supported radiative target family
- simulation-informed radiative hazard-potential target

Forbidden:
- local WBGT
- risk
- hazard_score
- official warning
- observed truth
- final AOI-wide M_rad map
- surrogate validation

## Next recommended action
B5: N24 target freeze / modifier reference definition update.

## Output files
- `b4_input_validation.csv` / `b4_input_validation.md`
- `n24_metric_availability_matrix.csv`
- `n24_target_descriptive_stats.csv`
- `n24_target_rank_correlation.csv`
- `n24_target_topk_overlap.csv`
- `n24_hour_stability_rank_correlation.csv`
- `n24_hour_stability_topk_overlap.csv`
- `n24_consistent_top_cells.csv`
- `n24_tail_heterogeneity_diagnostics.csv`
- `n24_base_vs_overhead_sensitivity_summary.csv`
- `n24_overhead_cooling_by_cell.csv`
- `n24_overhead_rank_shift.csv`
- `n24_threshold_area_audit.csv`
- `n24_replacement_cell_sanity.csv`
- `n24_legacy_anchor_sanity.csv`
- `n24_target_decision_matrix.csv`
