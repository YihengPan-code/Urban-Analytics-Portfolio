# Sprint B7 - N150 New-run-only SOLWEIG Execution

## Status
PASS

## Scope
- N150 new-run-only SOLWEIG execution
- N24 completed outputs reused
- no N24 rerun
- local raw rasters allowed but local-only
- no local WBGT
- no hazard_score
- no risk_score
- no surrogate
- no System A/B coupling

## B6/B6.1/B6.2 input
- N150 = 24 retained N24 + 126 new.
- no replacements after quick map QA.
- selected cells unchanged.
- new-run-only matrix rows = 1260.
- B7 input preflight status: `PASS`.

## Execution environment
- QGIS Desktop Python Console.
- qgis_process not used.
- UMEP/SOLWEIG algorithm resolution: `selected_algorithm_id: `umep:Outdoor Thermal Comfort: SOLWEIG``.
- UMEP preprocess algorithm resolution: `algorithm report present`.

## Run summary
- expected new runs = 1260
- attempted = 1260
- success = 1260
- skipped_completed = 0
- failed_preprocess = 0
- failed_solweig = 0
- blocked = 0
- completed_new = 1260
- catastrophic stop = no

## Aggregation summary
- new focus summary rows expected = 1260; observed = `1260`
- new delta rows expected = 630; observed = `630`
- merged focus rows expected = 1500; observed = `1500`
- merged delta rows expected = 750; observed = `750`
- B5 modifier target rows expected = 1500; observed = `1500`

## Git safety
- raw outputs under data/solweig/v12_n150_tiles are local-only
- never stage/commit .tif, .tiff, svfs.zip, data/solweig, data/rasters

## What this proves
- N150 label execution/merge ready for B8 surrogate protocol if PASS

## What this does not prove
- no local WBGT
- no risk
- no final AOI-wide map
- no surrogate validation
- no observed truth

## Next recommended action
B8 - surrogate / emulator protocol and model comparison using N150 labels.
