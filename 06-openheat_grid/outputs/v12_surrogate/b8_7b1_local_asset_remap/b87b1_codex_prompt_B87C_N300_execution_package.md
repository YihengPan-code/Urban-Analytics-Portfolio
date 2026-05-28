# Future Codex Prompt: B8.7c N300 Execution Package

Future lane only. Start only after explicit user authorization to create a real B8.7c N300 execution package.

Start from B8.7b.1 outputs:

- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_cell_asset_readiness_resolved.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_cell_asset_expected_paths.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_b87c_prerequisite_checklist.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_b87c_blocker_register.csv`

Allowed only after authorization:

- create a real N300 execution manifest;
- create a local-only QGIS/local runner;
- create smoke, pilot, production chunk, and full-new-N150 gates;
- keep local-only SOLWEIG outputs and run logs outside Git.

Required boundaries:

- Do not commit rasters, `svfs.zip`, local logs, or raw SOLWEIG outputs.
- Keep all local-only outputs outside the Git worktree.
- Include smoke/pilot/production chunk gates, resume checks, failure isolation, and postrun QA before label merge.
- Do not create AOI-wide prediction, B9 output, local WBGT, hazard_score, risk_score, exposure/vulnerability score, observed-truth claim, causal feature-importance claim, Tmrt-to-WBGT conversion, or System A/B coupling.
