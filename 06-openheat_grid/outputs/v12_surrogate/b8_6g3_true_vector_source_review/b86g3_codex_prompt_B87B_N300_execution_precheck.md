# Future Codex Prompt: B8.7b N300 Execution Precheck

Work inside the OpenHeat-ToaPayoh project subdirectory.

Lane: B8.7b N300 execution precheck.

Use B8.6g3 outputs as design/source-review inputs. This future lane may inspect
sample design validity, required SOLWEIG asset readiness, local-only execution
boundaries, and manifest requirements. It must still be a precheck: do not run
QGIS or SOLWEIG, and do not create raster outputs, AOI-wide predictions, B9
outputs, local WBGT, hazard_score, risk_score, exposure/vulnerability scores,
observed-truth claims, causal feature-importance claims, Tmrt-to-WBGT
conversion, or System A/B coupling.

Required starting inputs:
- outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_n300_design_v4_source_reviewed.csv
- outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_execution_precheck_readiness_matrix.csv
- outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_manual_source_review_closeout.csv

Keep no-raster commit hygiene. Any actual SOLWEIG/QGIS execution package belongs
to a later explicitly authorized lane, not B8.7b precheck.
