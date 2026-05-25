# Sprint 4D - System A AOI Temporal Aggregation Design

## Status
PASS

## Scope
- System A Level 1 interface only.
- Retrospective aggregation only.
- No model training.
- No System B integration.
- No local WBGT.
- No risk map.

## Inputs
- Input file: outputs\v11_level1\p_ge31_export\p_ge31_station_diagnostic.csv.
- Input status: full_station_diagnostic.
- Sample-only: False.
- Filtered rows: 10473.
- Station count: 27.
- Timestamp count: 388.
- Dataset labels used: hourly_max.

## Coverage
- Station count per timestamp ranged from 26 to 27.
- Mean station coverage fraction: 1.000.
- Quality flags: low_support_station:388; not_operational_warning:10473; ok_retrospective_diagnostic:10473; station_bias_warning:1552.
- S128 anchor rows available for 388 candidate timestamps.

## Candidate methods
- network_mean, network_median, network_p75, network_p90, and network_max are station-network diagnostic aggregations.
- anchor_S128 is retained as local-anchor sensitivity only.
- exclude_S142 and exclude_high_event_stations p90 variants are high-event-station sensitivities only.
- probability_any_independence_experimental is computed as a disabled-by-default diagnostic and assumes station independence.

## Comparison findings
- Mean absolute network_p90_p_ge31 vs network_median_p_ge31 difference: 0.0237.
- Mean absolute anchor_S128_p_ge31 vs network_p90_p_ge31 difference: 0.0236.
- Mean absolute network_max_p_ge31 vs network_p90_p_ge31 difference: 0.0261.
- Median-vs-p90 top-decile Jaccard overlap: 0.9500.
- S142 exclusion changed p90 by >0.05 at 0 timestamps.
- High-event-station exclusion changed p90 by >0.05 at 0 timestamps.
- p_ge31 aggregation should be interpreted as diagnostic probability aggregation, not official warning probability.
- wbgt_a_score_c aggregation should be interpreted as score aggregation, not local WBGT.

## Recommendation
- Background severity candidate: network_median_wbgt_a_score_c, pending human review.
- Conservative event-gate candidate: network_p90_p_ge31, pending human review.
- Sensitivity candidates: anchor_S128, network_max, exclude_S142 p90, and exclude_high_event_stations p90.
- Experimental only: probability_any_independence_experimental.

## Downstream contract implications
The dry-run can inform a later System A/System B coupling contract by offering timestamp-level AOI temporal gate candidates. It cannot be passed downstream as local WBGT, cell-level hazard, risk score, official warning probability, or prospective forecast skill.

## Caveats
- Retrospective only.
- Station-network diagnostic aggregation only.
- Not local WBGT.
- Not prospective.
- Not risk.
- Aggregation is not validated as true Toa Payoh WBGT.
- No final default aggregation is claimed; candidates remain pending human review.

## Next recommended action
AOI aggregation human review, followed by System A/System B coupling contract or System B target robustness audit.

## Run safeguards
- No forbidden files touched.
- No model training.
- No System B/v12/SOLWEIG touched.
- No archive modification.
- No API calls.
- No commit/stage performed.
