# B8.2 Benchmark Status

Status: PASS
Branch: codex/b8-surrogate-dataset-protocol
Scope: Lane B8.2 baseline surrogate/emulator benchmark for SOLWEIG-derived System B targets only.

## Commands run

- `Get-Location`
- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git status -sb -uno`
- `git status --short -- .`
- `python -m compileall scripts/v12_b8_surrogate_model_benchmark.py scripts/v12_b8_run_model_benchmark.py` (attempted; `python` was not on PATH)
- `C:\Users\CloudStar\anaconda3\envs\openheat\python.exe -m compileall scripts/v12_b8_surrogate_model_benchmark.py scripts/v12_b8_run_model_benchmark.py`
- `python scripts/v12_b8_run_model_benchmark.py --config configs/v12/systemb_surrogate_b8_model_benchmark.yaml` (attempted; `python` was not on PATH)
- `C:\Users\CloudStar\anaconda3\envs\openheat\python.exe scripts/v12_b8_run_model_benchmark.py --config configs/v12/systemb_surrogate_b8_model_benchmark.yaml`
- `git status --short -- .`
- `git ls-files --others --modified --exclude-standard -- .`
- `forbidden-file check over changed files`

## Files created / modified

- `configs/v12/systemb_surrogate_b8_model_benchmark.yaml`
- `scripts/v12_b8_surrogate_model_benchmark.py`
- `scripts/v12_b8_run_model_benchmark.py`
- `docs/v12/OpenHeat_SystemB_surrogate_baseline_benchmark_CN.md`
- `outputs/v12_surrogate/b8_model_benchmark/surrogate_model_metrics.csv`
- `outputs/v12_surrogate/b8_model_benchmark/surrogate_predictions_oof.csv.gz`
- `outputs/v12_surrogate/b8_model_benchmark/topk_overlap_by_model.csv`
- `outputs/v12_surrogate/b8_model_benchmark/stratified_error_by_feature_bin.csv`
- `outputs/v12_surrogate/b8_model_benchmark/split_family_summary.csv`
- `outputs/v12_surrogate/b8_model_benchmark/model_family_comparison_report.md`
- `outputs/v12_surrogate/b8_model_benchmark/B8_2_BENCHMARK_STATUS.md`

## Feature set used

- Feature set: `physical_core`.
- Feature count: 115.
- Numeric features: 114.
- Categorical features: 1.
- Dropped all-NaN features: 0.
- Dropped constant/non-usable features: 0.
- Hard-blocked candidate features: 0.

## Models run

- `featureless_mean`
- `ridge`
- `elasticnet`
- `random_forest`
- `extra_trees`
- `hist_gradient_boosting`

## Split families run

- `cell_grouped_holdout`
- `feature_bin_holdout`
- `hour_holdout`
- `scenario_holdout`
- `spatial_holdout`

## Key results

- Best cell-grouped model for `delta_tmrt_p90_c` by MAE: extra_trees (MAE=0.9401).
- Best spatial model for `delta_tmrt_p90_c` by MAE: extra_trees (MAE=0.9892).
- Spearman / top-k headline: extra_trees: mean cell/spatial Spearman=0.725; mean cell-level top-10% overlap=0.444.
- Skipped split count: 2.

## Caveats

- N150 only.
- Single forcing setup.
- SOLWEIG-derived labels only.
- No local WBGT.
- No risk map.
- No causal feature importance.
- No final AOI-wide prediction map.
- Tree grids were reduced for runtime and documented in the benchmark report.

## Safe to commit

- Compact B8.2 config, scripts, docs, and outputs under `outputs/v12_surrogate/b8_model_benchmark/` after review.

## Not safe to commit

- `data/solweig/`, `data/rasters/`, raw archive files, `.tif`, `.tiff`, `svfs.zip`, patch zip packages, large hourly forecast CSVs, AOI-wide prediction maps, local WBGT, hazard_score, risk_score, or System A/B coupling outputs.

## Next recommended action

- Review B8.2 metrics/report and decide whether a clearly caveated B8.3 model-card review is warranted, without promoting any model to final AOI-wide inference.
