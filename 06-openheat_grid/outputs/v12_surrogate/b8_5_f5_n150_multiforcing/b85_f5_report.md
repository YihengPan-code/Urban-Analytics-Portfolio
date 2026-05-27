# B8.5-F5 N150 Multi-Forcing Readiness Report

Generated: 2026-05-27 17:45:04

## 1. Why F5 Follows B8.6

B8.5-F4 passed the N24 decision matrix and allowed controlled N150 execution after precheck. B8.6 found a weak but real N150 single-forcing surrogate baseline and explicitly required N150 multi-forcing before promotion or B9. F5 therefore prepares the controlled N150 / 3000-run human-execution package.

## 2. Manifest Definition And Count

- Cells: `150`
- Forcing days: `2`
- Hours: `5`
- Scenarios: `2`
- Expected runs: `3000`
- Output group: `b85_f5_n150/<forcing_day_id>/<cell_id>/<scenario>/h<hour>`
- Expected Tmrt path: `C:/OpenHeat-local/solweig/b85_f1_tiles/<expected_output_group>/Tmrt_average.tif`

## 3. Pre-Execution Readiness

- Decision status: `N150_MULTIFORCING_STABILITY_REVIEW_READY`
- Ready rows: `3000/3000`
- The asset check records geometry, raster-tile path, SVF path, met forcing path, output root, QGIS manual check, and local-only output-path readiness for every manifest row.
- The check does not open raster contents and does not open `svfs.zip`.

## 4. Runner Safety / Resume / Fail-Safe

The repo QGIS runner remains `DRY_RUN=True`. A human must copy it to `C:/OpenHeat-local/solweig/b85_f5_n150`, write the local copy as UTF-8 without BOM, then change only the local copy to `DRY_RUN=False`. The runner refuses manifest mismatches, refuses real execution from the Git worktree, writes outputs only under `C:/OpenHeat-local/solweig/b85_f1_tiles`, logs every row, flushes after each row, supports resume, and stops on configured failure limits.

## 5. Manual QGIS Execution Instructions

See `outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_manual_qgis_run_instructions.md`. The QGIS Console wrapper reads with `utf-8-sig`, injects `__file__`, sets `sys.argv=[runner]`, and changes `cwd` to `runner.parent`.

## 6. Postrun / Raster / Label / Stability Scripts

- Postrun status: `3000/3000_EXECUTED_OUTPUTS_VALID`
- Raster QA status: `PASS`
- Label merge status: `PASS`
- Stability status: `PASS`

Before human execution these scripts return `NOT_RUN_YET` or `PREPARED` and do not fail. Raster QA reads local raster contents only after postrun validation has confirmed all 3000 outputs.

## 7. What F5 Can Unlock

If execution and QA pass, F5 can unlock a surrogate-promotion review with forcing-day stability evidence for N150. It does not itself authorize B9.

## 8. What F5 Does Not Prove

F5 does not prove local WBGT, risk, observed truth, causal feature importance, AOI-wide prediction, or System A/B coupling.

## 9. Claim Boundaries

- Not B9.
- Not local WBGT.
- Not risk.
- Not observed truth.
- Not causal feature importance.
- No raster committed.
- No Tmrt-to-WBGT conversion.

## Execution Risk Register

| risk_item | status | evidence | mitigation |
| --- | --- | --- | --- |
| expected_run_count | PASS | 150 cells x 2 forcing days x 5 hours x 2 scenarios = 3000 | Runner refuses non-3000 manifests and non-150 cell count. |
| expected_output_count | PASS | 3000 expected Tmrt_average.tif outputs under C:/OpenHeat-local/solweig/b85_f1_tiles/b85_f5_n150/... | Postrun validator checks local run log and nonzero expected output files without opening raster contents. |
| local_only_storage_estimate | WARN | 3000 GeoTIFF outputs plus SOLWEIG auxiliaries; rough local-only estimate 0.3-2.0 GB depending compression and auxiliary files. | Do not commit rasters; monitor C:/OpenHeat-local free space before human execution. |
| resume_and_fail_safe | PASS | resume={'skip_successful_run_log_rows': True, 'skip_existing_valid_outputs': True}; fail_safe={'max_failures': 10, 'max_consecutive_failures': 5, 'stop_on_manifest_mismatch': True} | Runner skips successful existing outputs and stops on configured failure limits. |
| f3b_console_bom_temp_wrapper_issue | PASS | Manual instructions require utf-8-sig read, explicit __file__, sys.argv=[runner], cwd=runner.parent, and UTF-8 no-BOM local copy. | Preserve F3b/F3c QGIS Console hardening exactly. |
| h10_caveat_from_f4 | WARN | F4 found h10 weaker; h10 is retained for sensitivity review and not anchor evidence. | Stability summary flags h10 caveat separately. |
| b86_single_forcing_blocker | PASS | B8.6 required N150 multi-forcing before promotion/B9. | F5 prepares the N150 multi-forcing execution package only. |
| claim_boundary | PASS | not B9 / not risk / not WBGT / no Tmrt-to-WBGT conversion | Docs, runner comments, reports, and statuses repeat these boundaries. |
| no_raster_in_git | PASS | Expected outputs are local-only under C:/OpenHeat-local; forbidden-file check covers .tif/.tiff/svfs.zip/data/solweig. | Do not stage or commit rasters. |
