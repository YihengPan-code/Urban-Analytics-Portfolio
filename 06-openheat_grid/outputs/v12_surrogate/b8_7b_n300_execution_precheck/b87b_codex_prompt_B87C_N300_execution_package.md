# Future Codex Prompt: B8.7c N300 Execution Package

You are working in the OpenHeat-ToaPayoh project. This is a future lane only. Start only after the user explicitly authorizes creation of a real B8.7c N300 execution package.

Use B8.7b outputs as precheck inputs. You may create an actual N300 execution manifest and a local-only QGIS runner only if the user explicitly authorizes that lane. Preserve all no-raster-commit and local-only execution boundaries.

Required boundaries:
- Keep raw rasters, `svfs.zip`, SOLWEIG outputs, local met forcing files, and local run logs out of Git.
- Keep execution output paths outside the Git worktree.
- Do not create AOI-wide prediction, B9 output, local WBGT, hazard_score, risk_score, exposure/vulnerability score, Tmrt-to-WBGT conversion, observed-truth claims, causal feature-importance claims, or System A/B coupling.
- Use explicit local asset remap checks before any real execution.
- Preserve QGIS Console safety notes: `utf-8-sig` read, explicit `__file__`, `sys.argv` set to the local runner path, and `cwd` set to the local runner parent.
- Implement smoke, pilot, production chunk, resume, failure-isolation, and postrun QA gates before any label merge.

Start from:
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_run_plan_preview.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_cell_asset_readiness.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_local_path_remap_audit.csv`
- `outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_qgis_console_safety_notes.md`
