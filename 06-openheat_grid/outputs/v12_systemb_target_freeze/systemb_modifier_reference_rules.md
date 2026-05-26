# System B Modifier Reference Rules

## Status
PASS - reference rule frozen for next-scale use.

## Canonical calculation

For each `reference_domain_version`, `hour_sgt`, and `scenario`:

```text
tmrt_ref_p90_c(hour, scenario, reference_domain_version)
= median(tmrt_p90_c across eligible cells in that reference domain, same hour, same scenario)

delta_tmrt_p90_c(cell, hour, scenario)
= tmrt_p90_c(cell, hour, scenario) - tmrt_ref_p90_c(hour, scenario, reference_domain_version)

m_rad_pct01(cell, hour, scenario)
= (rank_average(delta_tmrt_p90_c) - 1) / (n_reference_cells - 1)
```

## Rules

- The lowest reference-domain delta gets `0`.
- The highest reference-domain delta gets `1`.
- Ties use average rank.
- If `n_reference_cells = 1`, set `m_rad_pct01 = 0.5` and flag `insufficient_reference_domain`.
- Compute within the same hour and same scenario only.
- Never compare h10 against h13.
- Never compare `base` against `overhead_as_canopy` directly for rank unless scenario comparison is explicitly intended.
- Celsius ratios are forbidden: use difference plus rank, not division by mean Tmrt.

## Reference-domain versions

- `n24_internal_b3`: completed N24 cells only; B4/B5 evidence and traceability only; not final AOI-wide M_rad.
- `n150_training_future`: future N150 executed SOLWEIG sample; intended for surrogate training and validation.
- `full_aoi_prediction_future`: all eligible predicted cells after accepted surrogate inference; intended for final AOI-wide modifier ranking.
- `sensitivity_reference_optional`: shaded-reference or typology-specific references may be explored later, but are not canonical in B5.
