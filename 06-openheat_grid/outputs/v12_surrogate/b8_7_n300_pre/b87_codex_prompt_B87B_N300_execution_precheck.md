# Future Codex Prompt: B8.7b-N300 Execution Precheck

Work inside the OpenHeat-ToaPayoh project subdirectory.

Lane: B8.7b-N300-execution-precheck.

Use B8.7 outputs only after manual QA has accepted the N300 design. This future
lane may prepare a readiness matrix and, if explicitly approved by reviewers, a
local-only manifest/readiness draft. It must still not run SOLWEIG or QGIS.

Required inputs:
- outputs/v12_surrogate/b8_7_n300_pre/b87_n300_design_freeze_candidates.csv
- outputs/v12_surrogate/b8_7_n300_pre/b87_n300_manual_qa_checklist.csv
- outputs/v12_surrogate/b8_7_n300_pre/b87_n300_freeze_decision_matrix.csv
- outputs/v12_surrogate/b8_7_n300_pre/b87_true_vector_source_gap_register.csv

Forbidden:
No SOLWEIG execution, no QGIS execution, no raster reads/writes/copies, no
AOI-wide prediction, no B9, no local WBGT, no hazard_score, no risk_score, no
exposure/vulnerability score, no observed-truth claim, no causal feature
importance claim, no Tmrt-to-WBGT conversion, no System A/B coupling, and no
heavy/raw file commit.
