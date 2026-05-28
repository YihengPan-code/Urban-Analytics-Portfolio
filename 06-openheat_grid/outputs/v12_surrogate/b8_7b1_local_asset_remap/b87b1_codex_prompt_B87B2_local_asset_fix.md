# Future Codex Prompt: B8.7b.2 Local Asset Fix

Use this only if B8.7b.1 is `WAITING_LOCAL_ROOTS`, `PARTIAL_MISSING_ASSETS`, or `BLOCKED_BY_MISSING_ASSETS`.

Goal:

- fill or repair `manual_inputs/b87b1_manual_local_roots.csv`;
- verify local roots by metadata only;
- repair missing or ambiguous per-cell asset mappings;
- rerun the B8.7b.1 metadata-only readiness suite.

Still forbidden:

- no QGIS execution;
- no SOLWEIG execution;
- no run-ready N300 manifest;
- no QGIS runner;
- no local runner;
- no local execution package;
- no raster read/write/copy/open;
- no AOI-wide prediction, B9, local WBGT, hazard/risk/exposure/vulnerability score, observed-truth claim, causal feature-importance claim, Tmrt-to-WBGT conversion, or System A/B coupling.
