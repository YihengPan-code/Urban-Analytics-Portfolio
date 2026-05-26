# Sprint B5 — System B Target Freeze / Modifier Reference Definition

## Status
PASS

## Scope
- target freeze / reference definition only
- no QGIS
- no SOLWEIG rerun
- no raw raster reads
- no local WBGT
- no hazard_score
- no risk_score
- no surrogate
- no System A/B coupling

## Inputs
- B3 focus summary rows: `240`
- B3 base-vs-overhead delta rows: `120`
- B3 provisional modifier rows: `240`
- Unique N24 cells: `24`
- Scenarios: `base, overhead_as_canopy`
- Hours: `10, 12, 13, 15, 16`

## B4 decision carried forward
- `tmrt_p90_c` = N24-supported primary candidate.
- `tmrt_p75_c`, `tmrt_p95_c`, `tmrt_mean_c`, and `tmrt_max_c` remain companions/sensitivities.
- `pct_pixels_tmrt_ge_40/45/50/55` remain optional threshold-area companions.
- Delta and modifier rows are derived/provisional in B4 and are formalized here only as a method contract.

## Frozen target family
The frozen target family is written to `systemb_target_family_freeze.csv`. The primary physical target is `tmrt_p90_c`, the primary physical modifier delta is `delta_tmrt_p90_c`, and the normalized modifier candidate is `m_rad_pct01`.

## Reference definition
`tmrt_ref_p90_c` is the same-hour, same-scenario median `tmrt_p90_c` across eligible cells in a declared `reference_domain_version`. `delta_tmrt_p90_c` is the cell p90 minus that reference. `m_rad_pct01` is `(rank_average - 1) / (n_reference_cells - 1)`. The method forbids Celsius ratios and never ranks across hours or across scenarios unless an explicit scenario comparison is intended.

## N24 method check
- B5 method-check rows: `240`
- Reference rows: `10`
- Comparison rows: `240`
- Legacy comparison: 230 rows differ from legacy m_rad_pct; max abs difference 0.041667

If the existing provisional `m_rad_pct` differs, it is preserved as legacy/provisional and not overwritten. B5 recommends `m_rad_pct01` going forward.

## Schema / downstream contract
The output schema is written to `systemb_target_output_schema.csv`. The surrogate label contract is written to `systemb_surrogate_label_contract.csv`. The preferred future supervised label candidate is `delta_tmrt_p90_c`; `tmrt_p90_c` is secondary; companion labels remain required for validation context.

## Claim boundaries
Forbidden claims remain explicit: no local WBGT, no observed truth, no official warning, no hazard_score, no risk_score, no exposure/vulnerability score, no final AOI-wide M_rad before surrogate/full-AOI prediction, and no System A/B coupling.

## Next recommended action
B6 — N150 sample design + manifest using the B5 target family. Do not jump directly to surrogate until N150 labels exist.
