# Sprint B7.1 - N150 Merge Schema Hotfix

## Status
PASS

## Scope
- repo-side merge script hotfix only
- QGIS/SOLWEIG was not rerun
- raw outputs were not deleted or modified
- N150 selected cells and manifests were not changed
- no local WBGT
- no hazard_score
- no risk_score
- no surrogate
- no System A/B coupling
- no stage/commit by this script

## Cause
`compute_b5_targets()` merged the B5 reference table into focus rows that already carried schema fields, which could create suffixed version columns and leave no unsuffixed `target_version` / `reference_domain_version` for final column ordering.

## Fix
- B5 schema defaults are now explicit: `systemb_target_family_v0_1_b5` and `n150_training_future`.
- `target_version` and `reference_domain_version` are written onto modifier targets after reference merge.
- reference values also carry the same B5 schema columns.
- output column ordering only selects columns that are present after required fields have been added.

## Rerun result
- aggregation had already succeeded: new focus rows = `1260`, new delta rows = `630`
- merged focus rows = `1500`
- merged delta rows = `750`
- modifier target rows = `1500`
- reference rows = `10`
- B5 target schema columns present = `True`

## Claim boundaries
These outputs are SOLWEIG-derived Tmrt labels and B5 modifier targets only. They are not local WBGT, hazard_score, risk_score, surrogate output, final AOI-wide maps, or System A/B coupling.
