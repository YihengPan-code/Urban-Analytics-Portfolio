# B8.7a Status

Status: B87A_PATCHED_DESIGN_READY_FOR_REVIEW
Branch: codex/b87a-n300-design-qa-patch
Scope: N300 candidate-design QA reducer and patch package only; no execution artifacts.

## Commands Run By Suite

- `python scripts/v12_b87a_run_design_qa_patch.py --config configs/v12/systemb_b87a_n300_design_qa_patch.yaml`

## Key Results

- Manual input found: yes
- Water / pure-river review queue count: 8
- Auto replacement candidates count: 681
- v3 design row count: 150
- N150 overlap count: 0
- Duplicate cell count: 0
- Role balance: PASS=6 WARN=0 FAIL=0
- Spatial/typology/anchor/neutral: spatial PASS=4 WARN=0 FAIL=0; typology PASS=4 WARN=4 FAIL=0; anchor PASS=3 WARN=2 FAIL=0; neutral PASS=9 WARN=1 FAIL=0
- Source-review blockers: manual_source_review_blockers=3; known_connected_shade_corridor_gap=carried_to_B86G3

## Caveats

This lane is AUTO_ONLY when manual input is missing and must remain waiting for
manual QA. Even a future freeze-ready status would not authorize SOLWEIG or
QGIS execution.

## Not Created

No raster, QGIS/SOLWEIG run, N300 execution manifest, local runner, AOI-wide
prediction, B9 output, local WBGT, hazard_score, risk_score,
exposure/vulnerability score, observed-truth claim, causal feature-importance
claim, Tmrt-to-WBGT conversion, or System A/B coupling.
