# B8.7a Manual QA Summary

Status: `B87A_PATCHED_DESIGN_READY_FOR_REVIEW`

- Manual input found: `yes`
- Water / pure-river review queue count: `8`
- Auto replacement candidates: `681`
- v3 design row count: `150`
- N150 overlap count: `0`
- Duplicate cell count: `0`

## Manual Review Status

| status_item | value | status | evidence |
| --- | --- | --- | --- |
| manual_input_found | yes | PASS | C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/outputs/v12_surrogate/b8_7a_n300_design_qa_patch/manual_inputs/b87a_manual_candidate_review.csv |
| template_rows | 150 | PASS | one row per B8.7 candidate |
| reviewed_rows | 8 | PASS | exclude=3|keep=2|not_reviewed=142|source_review=3 |
| auto_only_mode | no | PASS | manual decisions available for patching |

If manual input is missing, this is AUTO_ONLY and waiting for human review. It
is acceptable to review only obvious exclusions such as pure river/water-only
cells or cells mostly outside pedestrian-relevant land.

## Guardrails

No raster, no QGIS/SOLWEIG, no N300 execution manifest, no AOI-wide prediction,
no B9, no local WBGT, no hazard/risk/exposure/vulnerability score, no observed
truth, no causal feature importance, no Tmrt-to-WBGT conversion, and no System
A/B coupling were created.
