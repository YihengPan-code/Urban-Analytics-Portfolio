# P_ge31 AOI Temporal Design Note

Sprint 4C exports station-level retrospective diagnostics only. These rows are not System B temporal severity by themselves.

System B should consume AOI-level temporal severity, not raw station diagnostic rows. This sprint does not select an AOI aggregation method and does not silently promote station rows to AOI or 100m cell severity.

Candidate future AOI aggregation methods include:

- `station_anchor_S128_or_ToaPayoh_station`, if validated.
- `network_median`.
- `network_p90`.
- `max_or_high_recall_screening`.
- `probability-pooled statistic`.

Each aggregation method must be separately justified, versioned, and checked against the Level 1 output contract before System B consumption.

Do not use station rows as 100m cell severity. Do not treat this export as local WBGT, cell-level WBGT, or risk.
