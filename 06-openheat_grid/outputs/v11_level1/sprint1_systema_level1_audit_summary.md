# System A Level 1 Sprint 1 Audit Summary

Generated: 2026-05-25

## Status

- A. M2 recovery: PASS.
- B. Station x Open-Meteo pairing audit: PASS, no hard blocker found.
- C. Registry reproduction: PASS, canonical sklearn Ridge only.
- D. Final sprint report: PASS.

## Changed Files List

Scripts/config:

- `configs/v11/level1_model_registry.yaml`
- `scripts/v11_l1_recover_m2.py`
- `scripts/v11_l1_audit_station_forcing_pairing.py`
- `scripts/v11_l1_build_feature_matrix.py`
- `scripts/v11_l1_run_model_registry.py`
- `scripts/v11_l1_evaluate_predictions.py`

Removed from canonical Sprint 1 script set:

- `scripts/v11_l1_test_ridge_backend_sanity.py`

Outputs:

- `outputs/v11_level1/m2_recovery/m2_recovery_report.md`
- `outputs/v11_level1/m2_recovery/recovered_m0_m4_metrics.csv`
- `outputs/v11_level1/pairing_audit/station_openmeteo_pairing_report.md`
- `outputs/v11_level1/pairing_audit/station_grid_mapping.csv`
- `outputs/v11_level1/pairing_audit/same_timestamp_spatial_variation.csv`
- `outputs/v11_level1/pairing_audit/time_alignment_checks.csv`
- `outputs/v11_level1/reproduction/feature_matrix_manifest.csv`
- `outputs/v11_level1/reproduction/feature_matrix_all_stations_formal.csv`
- `outputs/v11_level1/reproduction/feature_matrix_hourly_mean.csv`
- `outputs/v11_level1/reproduction/feature_matrix_hourly_max.csv`
- `outputs/v11_level1/reproduction/oof_predictions_reproduction.csv`
- `outputs/v11_level1/reproduction/oof_predictions_reproduction_fallback_noncanonical.csv`
- `outputs/v11_level1/reproduction/metrics_reproduction_table.csv`
- `outputs/v11_level1/reproduction/reproduction_report.md`
- `outputs/v11_level1/sprint1_systema_level1_audit_summary.md`

## Commands Run

Initial audit/setup:

- `C:\Users\CloudStar\anaconda3\envs\openheat\python.exe scripts\v11_l1_recover_m2.py`
- `C:\Users\CloudStar\anaconda3\envs\openheat\python.exe scripts\v11_l1_audit_station_forcing_pairing.py`
- `C:\Users\CloudStar\anaconda3\envs\openheat\python.exe scripts\v11_l1_build_feature_matrix.py`

Environment diagnosis:

- `C:\Users\CloudStar\anaconda3\envs\openheat\python.exe -X faulthandler -u -c "import numpy as np; from sklearn.linear_model import Ridge; ..."`
- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat python -X faulthandler -u -c "import numpy as np; from sklearn.linear_model import Ridge; ..."`
- Manual Codex PowerShell PATH prepend test for `CONDA_PREFIX`, `CONDA_DEFAULT_ENV`, and the `openheat` env DLL paths.

Canonical reproduction:

- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\v11_l1_run_model_registry.py --ridge-backend sklearn`
- `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\v11_l1_evaluate_predictions.py`

Git/safety checks:

- `git status --short`
- `git diff --name-only | findstr /I ".tif .tiff data\\solweig data\\rasters raw archive hourly_grid_heatstress_forecast"`
- `git diff --cached --name-only`

## Environment Diagnosis

Root cause confirmed: Codex PowerShell direct env-python lacked conda activation DLL/PATH context.

- Direct call to `C:\Users\CloudStar\anaconda3\envs\openheat\python.exe` had empty `CONDA_PREFIX` / `CONDA_DEFAULT_ENV` and did not prepend `C:\Users\CloudStar\anaconda3\envs\openheat\Library\bin` and related conda env paths.
- The same sklearn Ridge smoke test crashed under direct Codex PowerShell with Windows fatal exception `0xc06d007f` in `sklearn.utils.extmath.safe_sparse_dot` / Ridge `_solve_cholesky`.
- `conda run -n openheat` passed the same smoke test.
- Manually prepending the conda env DLL/PATH context also passed the same smoke test.

Future Codex execution for sklearn/numpy/scipy/geospatial stack work should use:

```powershell
C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat --no-capture-output python ...
```

## Canonical Reproduction

Canonical reproduction uses sklearn only:

- `ridge_backend = sklearn`
- `ridge_backend_requested = sklearn`
- `sklearn_failed = False`
- `fallback_used = False`
- imputation: `SimpleImputer(strategy=median)`
- scaling: `StandardScaler(with_mean=True, with_std=True)`
- alpha: `1.0`

No closed-form fallback, auto backend, pure-Python solver, or new model family is present in the canonical runner.

Current canonical outputs:

- `outputs/v11_level1/reproduction/oof_predictions_reproduction.csv`
- `outputs/v11_level1/reproduction/metrics_reproduction_table.csv`
- `outputs/v11_level1/reproduction/reproduction_report.md`

The current metrics table contains only sklearn backend rows. All reproduced rows with previous metrics match to within 1e-6 MAE.

Canonical run provenance:

- Model sys.executable: `C:\Users\CloudStar\anaconda3\envs\openheat\python.exe`
- Model command: `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\v11_l1_run_model_registry.py --ridge-backend sklearn`
- Evaluation command: `C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\v11_l1_evaluate_predictions.py`

Canonical metric summary:

| dataset_label | model | ridge_backend | fallback_used | rows | stations | folds | target | MAE | RMSE | bias | R2 |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| all_stations_formal | M3_weather_ridge | sklearn | False | 40389 | 27 | 27 | official_wbgt_c | 0.933191 | 1.269310 | 0.003222 | 0.646989 |
| all_stations_formal | M4_inertia_ridge | sklearn | False | 40389 | 27 | 27 | official_wbgt_c | 0.916754 | 1.255194 | 0.003477 | 0.654797 |
| all_stations_formal | M7_compact_weather_ridge | sklearn | False | 40389 | 27 | 27 | official_wbgt_c | 0.935606 | 1.288906 | 0.003504 | 0.636005 |
| hourly_max | M3_weather_ridge | sklearn | False | 1674 | 27 | 27 | official_wbgt_c_max | 0.648372 | 0.871592 | 0.001412 | 0.851440 |
| hourly_max | M4_inertia_ridge | sklearn | False | 1674 | 27 | 27 | official_wbgt_c_max | 0.638525 | 0.861520 | 0.001619 | 0.854854 |
| hourly_max | M7_compact_weather_ridge | sklearn | False | 1674 | 27 | 27 | official_wbgt_c_max | 0.682441 | 0.912251 | 0.001403 | 0.837257 |
| hourly_mean | M3_weather_ridge | sklearn | False | 1674 | 27 | 27 | official_wbgt_c_mean | 0.604970 | 0.811364 | 0.000829 | 0.839482 |
| hourly_mean | M4_inertia_ridge | sklearn | False | 1674 | 27 | 27 | official_wbgt_c_mean | 0.593217 | 0.794898 | 0.001303 | 0.845931 |
| hourly_mean | M7_compact_weather_ridge | sklearn | False | 1674 | 27 | 27 | official_wbgt_c_mean | 0.630589 | 0.840385 | 0.000946 | 0.827794 |

## Non-Canonical Fallback Artifact

The earlier fallback plumbing diagnostic OOF file was preserved separately as:

- `outputs/v11_level1/reproduction/oof_predictions_reproduction_fallback_noncanonical.csv`

It is not used by the current metrics table or reproduction report and should not be treated as canonical reproduction.

## Key Audit Outputs

- M2 was found in historical metric outputs under the name `M2_linear_proxy`; it was defined and run, not merely defined.
- Pairing audit used `outputs/v11_beta_formal/diagnostics_inputs/v11_pairs_14d_formal_20260524_40419_v091_diag.csv`.
- Pairing audit found 27 stations, distinct station/Open-Meteo coordinates, zero SGT/UTC alignment delta, and station-hour rather than hour-only hourly grouping.

## Caveats

- Metrics are calibration reproduction diagnostics for WBGT_A(hour), not validated 100m local WBGT prediction.
- No System B, SOLWEIG, v12, QGIS, raster, raw archive, or archive collector paths were intentionally edited.
- No new model families were added.
- No random train/test split was used.
- Generated `outputs/v11_level1/reproduction/*` artifacts are intentionally uncommitted; some are large.

## Do-Not-Commit Check

- `git diff --cached --name-only`: no output, so nothing is staged.
- Heavy-file guard command: no output from `git diff --name-only | findstr /I ".tif .tiff data\\solweig data\\rasters raw archive hourly_grid_heatstress_forecast"`.
- `git status --short`: worktree remains dirty with many pre-existing untracked files plus the new Level 1 files. No commit or push was made.

## Next Recommended Action

Review the Level 1 artifacts and, if acceptable, keep using `conda run -n openheat --no-capture-output python ...` for future Codex executions that invoke sklearn/numpy/scipy-backed compiled libraries.
