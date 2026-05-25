# System A AOI Temporal Aggregation Design

## Status
Design + retrospective dry-run / not System B integration.

## Why needed
Station diagnostic rows are not AOI temporal severity. System B needs a timestamp-level AOI temporal gate candidate before any coupling contract can be reviewed.

## Inputs
- Primary station diagnostic source: outputs/v11_level1/p_ge31_export/p_ge31_station_diagnostic.csv.
- Sample-only source is allowed only for schema smoke checks and is not suitable for final aggregation.
- Fallback source is outputs/v11_level1/probability_calibration/p_ge31_diagnostic_predictions.csv if no exported station diagnostic exists.
- Contract context: configs/v11/system_a_level1_output_contract.yaml and System A Level 1 model-card outputs.

## Candidate methods
- network_mean: diagnostic average only.
- network_median: background severity candidate using median score and probability.
- network_p75: moderate-conservative station-network candidate.
- network_p90: conservative event-gate candidate.
- network_max: upper-bound sensitivity only.
- anchor_S128: local-anchor sensitivity only if S128 exists; not validated as Toa Payoh AOI truth.
- exclude_S142_network_p90: high-event-station sensitivity.
- exclude_high_event_stations_network_p90: S142/S137/S135 sensitivity only, not default.
- probability_any_independence_experimental: disabled-by-default experiment that assumes station independence.

## Recommended candidate set
- network_median_wbgt_a_score_c as background severity candidate pending human review.
- network_p90_p_ge31 as conservative event-gate candidate pending human review.
- anchor_S128 as sensitivity only.
- network_max as upper-bound sensitivity only.

## Claim boundaries
Allowed:
- AOI temporal severity candidate.
- Retrospective diagnostic aggregation.
- Future System B temporal gate candidate.

Forbidden:
- Local WBGT.
- Cell-level WBGT.
- Risk score.
- Official warning probability.
- Prospective forecast skill.
- System B integration completed.

## What remains unresolved
- Final AOI aggregation selection.
- System B coupling contract.
- Prospective evaluation.
- Actual AOI validation.
- Exposure/vulnerability risk layer.

## Next step
System A/System B coupling contract after human review, or System B target robustness audit.
