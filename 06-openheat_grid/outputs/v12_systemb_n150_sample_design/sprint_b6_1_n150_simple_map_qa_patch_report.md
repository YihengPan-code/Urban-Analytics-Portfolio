# Sprint B6.1 - N150 Simple Map-QA Package Patch

## Status
PASS

## Scope
- simple map-QA package only
- no resampling
- no selected-cell changes
- no manifest changes
- no QGIS
- no SOLWEIG
- no raster reads
- no local WBGT
- no hazard_score
- no risk_score
- no surrogate
- no System A/B coupling

## Why this patch exists
B6 mechanically passed, but before B7 the user wants one short whole-sample map sanity QA to remove obvious bad samples only.

## B6 validation
- Selected rows: 150
- Unique selected cells: 150
- Retained N24: 24
- New selected cells: 126
- Full run matrix rows: 1500
- New-run-only rows: 1260
- B2.2 replaced-out cells absent.
- B2.2 replacement-in N24 cells present.

## New QA philosophy
- Default KEEP.
- REPLACE only obvious bad cells.
- No AMBER.
- No full 150-cell semantic QA.
- No pedestrian-accessibility pass/fail.
- No street-view forensic review.

## New files
- `n150_simple_map_qa_checklist.csv` / `.md`
- `n150_review_points.geojson` / `.kml`
- `n150_replacement_suggestions.csv`
- `n150_stratum_multilabel_summary.csv`
- `n150_primary_stratum_caveat.md`

## Review points
- Generated: True
- Usable point count: 150
- Note: WGS84 lon/lat review points generated from candidate-universe centroid columns.

## Consistency patch
`n150_new_cells.csv` was synchronized from `n150_selected_cells.csv` for selected_new rows so review flags are not lost. New-cell ID set unchanged: True.

## Primary stratum caveat
Primary-stratum labels are coarse automatic labels and are skewed by label priority/order. Use multi-label strata, feature bins, and numeric sampling features for B8 validation design.

## Checklist and replacements
- Checklist rows: 150
- Auto-flagged rows first in checklist: 51
- Replacement suggestion rows: 150

## Next recommended action
User performs quick KEEP/REPLACE map sanity pass. If replacements exist, B6.2 should apply replacements and regenerate manifests. If no replacements exist, proceed to B7 new-run-only N150 SOLWEIG execution.
