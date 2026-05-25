# Sprint B1 - System B Target Robustness Audit

## Status
PARTIAL

## Scope
- existing SOLWEIG summaries only
- no rasters
- no SOLWEIG rerun
- no QGIS
- no surrogate
- no System A/B coupling
- no risk map
- no local WBGT

## Inputs
Loaded/inspected files: 51.

Core 8 loaded summaries:
- outputs/v12_solweig_typology_pilot/core8_base_summary/modifier_normalization_params.csv: rows=5, scenario=base
- outputs/v12_solweig_typology_pilot/core8_base_summary/modifier_reference_table.csv: rows=5, scenario=base
- outputs/v12_solweig_typology_pilot/core8_base_summary/modifier_targets_long.csv: rows=40, scenario=base
- outputs/v12_solweig_typology_pilot/core8_base_summary/tmrt_cell_summary_long.csv: rows=40, scenario=base
- outputs/v12_solweig_typology_pilot/core8_base_summary/v12_solweig_typology_aggregation_report.md: rows=49, scenario=base
- outputs/v12_solweig_typology_pilot/core8_overhead_summary/core8_base_vs_overhead_delta.csv: rows=40, scenario=overhead_as_canopy
- outputs/v12_solweig_typology_pilot/core8_overhead_summary/core8_base_vs_overhead_delta_by_cell.csv: rows=8, scenario=overhead_as_canopy
- outputs/v12_solweig_typology_pilot/core8_overhead_summary/core8_base_vs_overhead_delta_report.md: rows=38, scenario=overhead_as_canopy
- outputs/v12_solweig_typology_pilot/core8_overhead_summary/modifier_normalization_params.csv: rows=5, scenario=overhead_as_canopy
- outputs/v12_solweig_typology_pilot/core8_overhead_summary/modifier_reference_table.csv: rows=5, scenario=overhead_as_canopy
- outputs/v12_solweig_typology_pilot/core8_overhead_summary/modifier_targets_long.csv: rows=40, scenario=overhead_as_canopy
- outputs/v12_solweig_typology_pilot/core8_overhead_summary/tmrt_cell_summary_long.csv: rows=40, scenario=overhead_as_canopy
- outputs/v12_solweig_typology_pilot/core8_overhead_summary/v12_solweig_typology_aggregation_report.md: rows=49, scenario=overhead_as_canopy

Scenario/hour/cell coverage:
- base: cells=8, hours=10,12,13,15,16
- overhead_as_canopy: cells=8, hours=10,12,13,15,16

## Product taxonomy
Product A is the System A WBGT heat-stress state and answers when it is hot; it is not implemented here. Product B is the System B SOLWEIG-derived radiative heat-hazard potential and answers where structure is more radiant under the same forcing. Product B2 is a future UTCI/PET sensitivity layer. Product C is a future WBGT-conditioned radiative priority. Product D is a future planning heat-risk priority requiring explicit exposure and vulnerability.

## Target availability
Available metrics: delta_tmrt_p90_c, m_rad_pct, tmrt_max_c, tmrt_mean_c, tmrt_p75_c, tmrt_p90_c, tmrt_p95_c.

Unavailable or empty metrics in at least one scenario/hour: none.

Threshold-area metrics such as `pct_pixels_tmrt_ge_40`, `pct_pixels_tmrt_ge_45`, `pct_pixels_tmrt_ge_50`, and `pct_pixels_tmrt_ge_55` are not available in the current normalized Core 8 target summary. They should be added in the next SOLWEIG aggregation pass before canonical target selection.

## Ranking robustness
Mean p90-paired Spearman = 0.764; mean p90-paired top-k Jaccard = 0.692.

Core 8 top-k statistics are small-sample diagnostics only. p90 is evaluated here against mean, p75, p95, max, delta p90, and m_rad_pct where available.

### p90 companion interpretation
- `tmrt_p90_c` vs `tmrt_p75_c`: very strong agreement; this supports p90 as a stable mixed-cell upper-tail radiant exposure target.
- `tmrt_p90_c` vs `tmrt_p95_c`: moderate agreement; p95 should remain a companion metric for more extreme upper-tail behavior.
- `tmrt_p90_c` vs `tmrt_max_c`: weak agreement; max should remain upper-bound sensitivity only, while p90 captures a more stable upper-tail exposure signal rather than pixel-level extremes.
- `delta_tmrt_p90_c` and `m_rad_pct` are derived from p90, so perfect or near-perfect rank agreement with p90 is expected and should not be treated as independent validation.

## Scenario sensitivity
Base and overhead scenarios were matched by cell_id/hour. Overall p90 mean delta overhead-minus-base = -0.332 C; cooled cells = 17, warmed cells = 1. Overall m_rad_pct mean delta = 0.000.

Largest cooling/warming cells and hour-wise summaries are written to `base_vs_overhead_sensitivity_summary.csv`.

## Hour stability
Mean cross-hour Spearman = 0.983; mean cross-hour top-k Jaccard = 0.921.

Consistently top-ranked and cool-ranked cells across hours are written to `hour_stability_consistent_cells.csv`.

## Typology interpretability
Typology labels are available. Consistent p90 hot anchors: TP_0059, TP_0565, TP_0986; consistent cool anchors: TP_0326, TP_0542, TP_0835.

If pedestrian relevance is needed downstream, a future pedestrian-accessible mask remains required.

## Decision
Keep `tmrt_p90_c` as a provisional primary System B target candidate, but do not promote it to canonical target yet. Current Core 8 evidence supports p90 as a stable mixed-cell upper-tail radiant exposure metric, especially because its hour-to-hour ranking is stable and it is consistent with p75. However, Core 8 is too small for canonical promotion; p90 has only moderate agreement with p95 and weak agreement with max, and threshold-area metrics are not yet available. Therefore p90 should proceed with required companion targets and N=24 validation.

## Caveats
- Core 8 is small sample.
- p90 is operational target, not external standard.
- no pedestrian-accessible mask yet.
- no exposure/vulnerability.
- no risk claim.
- no local WBGT claim.

## Next recommended action
B2 N=24 scaled sample design with companion metrics: p75, p90, p95, max, mean, delta_p90, m_rad_pct, and threshold-area metrics where available.

## Run boundary confirmation
- no rasters touched
- no .tif touched
- no SOLWEIG rerun
- no QGIS
- no model training
- no risk map
- no local WBGT
- no System A/B coupling performed
- no commit/stage performed
