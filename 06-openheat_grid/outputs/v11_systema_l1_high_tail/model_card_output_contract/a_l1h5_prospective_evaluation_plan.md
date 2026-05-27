# A-L1H.5 Prospective Evaluation Plan

Generated: 2026-05-27
Decision status: `A_L1H5_CONTRACT_PASS`

## Purpose

System A Level 1 v1.0 is frozen as a model card and output contract before prospective evaluation. The current evidence is retrospective station-held-out evidence; it is not a public warning system and not a validated prospective forecast.

## Required Future Snapshot

- Use a future formal archive snapshot with immutable input rows, model/card version, and extraction timestamp.
- Separate retrospective rows from prospective rows using `is_retrospective_or_prospective`.
- Keep `lead_time_hours_optional` populated for prospective rows when lead time exists.
- Do not append live-growing archive rows during formal comparison.

## Validation Design

LOSO is retrospective evidence. A prospective time validation is required before any stronger operational claim for `p_ge31_optional`, interval columns, or expected exceedance columns.

The model card, output schema, threshold-policy register, and companion decisions must be frozen before the prospective window starts.

## Metrics

- `recall_ge31`
- `precision_ge31`
- `miss_rate_ge31`
- Brier score for `p_ge31_optional`
- ECE for `p_ge31_optional`
- high-tail MAE for rows with observed WBGT >=31 C
- S142/S139 and all-station caveat register refresh

## P_ge31 Promotion Criteria

`p_ge31_optional` may be considered for stronger companion status only if a future prospective snapshot preserves materially improved ge31 recall/miss behavior relative to `wbgt_a_c` fixed_31, maintains acceptable precision/false-alarm behavior, has stable Brier/ECE, and does not fail station caveat checks.

Promotion still cannot make it an official public warning probability without separate operational governance.

## ge33 Promotion Gate

`p_ge33_optional` remains exploratory until at least 30 held-out/prospective ge33 events are available in an explicitly reviewed snapshot, with station support and calibration diagnostics reported separately.
