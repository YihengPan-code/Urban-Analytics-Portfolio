# Future Codex prompt: B8.7-N300-PRE updated feature-schema design freeze

Work inside the OpenHeat-ToaPayoh project subdirectory.

Lane: B8.7-N300-PRE targeted sample design freeze.

Use these inputs:
- outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_targeted_n300_design_v2.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_n300_candidate_feature_dataset.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_feature_schema.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_feature_gap_closure_matrix.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_failure_context_feature_join.csv

Task:
Freeze an updated targeted N300 candidate design package and feature-schema review only. Use B8.6g feature coverage to flag candidates needing source review, anchor-like replication, neutral-boundary replication, shade-corridor/source acquisition, and typology/spatial support. This is not a SOLWEIG execution package.

Forbidden:
No SOLWEIG execution, no QGIS runner, no N300 SOLWEIG manifest, no raster read/write/open/copy, no AOI-wide prediction, no B9, no local WBGT, no hazard_score, no risk_score, no observed-truth claim, no causal feature-importance claim, no Tmrt-to-WBGT conversion, and no System A/B coupling.

Required outputs:
Updated N300-PRE design freeze CSV, schema coverage audit, exclusion/review register, Markdown report, and explicit keep-blocked AOI/B9 decision.
