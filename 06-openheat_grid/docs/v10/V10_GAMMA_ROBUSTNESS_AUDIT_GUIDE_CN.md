# OpenHeat v10-gamma robustness audit guide

## 目的

这个小阶段用于回应 v10-gamma final findings report 的方法学疑问。它只读已有输出，不修改模型、不改 raster、不改 ranking。

主要检查四件事：

1. `TP_0315` 是否被错误归类；
2. old DSM-gap false-positive candidate 的定义是否透明，是否存在 co-derived / circularity 风险；
3. old top20 中 FP candidates 与 non-candidates 的 leaving-rate baseline；
4. TP_0945 这类 fully-built / dense-cell edge case 是否只是个别现象。

## 运行

```bat
scripts\v10_run_gamma_robustness_audit.bat
```

或者：

```bat
python scripts\v10_gamma_robustness_audit.py --config configs\v10\v10_gamma_robustness_config.example.json
```

## 输入

默认读取：

```text
outputs/v10_gamma_comparison/v10_vs_v08_rank_comparison.csv
outputs/v10_gamma_forecast_live/v10_gamma_hotspot_ranking_with_grid_features.csv
outputs/v10_morphology/v10_old_vs_new_building_morphology_shift.csv
outputs/v10_ranking_audit/v10_old_false_positive_candidates.csv
```

## 输出

```text
outputs/v10_gamma_robustness/v10_gamma_robustness_audit_report.md
outputs/v10_gamma_robustness/v10_gamma_top20_transition_classes.csv
outputs/v10_gamma_robustness/v10_gamma_false_positive_definition_check.csv
outputs/v10_gamma_robustness/v10_gamma_fp_vs_nonfp_top20_contingency.csv
outputs/v10_gamma_robustness/v10_gamma_dense_cell_sanity_check.csv
outputs/v10_gamma_robustness/v10_gamma_tp0315_diagnostic.csv
```

## 结果怎么解释

### TP_0315

如果 `TP_0315` 的 transition class 是：

```text
entering_v10_top_fp_candidate
```

它就不应该被写作 “old top20 retained false-positive candidate”。正确写法是：

> TP_0315 was an entering v10 top20 cell that also carried the broader v10-beta DSM-gap candidate flag.

### false-positive candidate 的 circularity

脚本会同时输出：

```text
co_derived_fp_candidate
independent_old_dsm_gap_candidate
```

其中 `co_derived_fp_candidate` 使用了 v10 reviewed-DSM diagnostics，例如 coverage gain / building-density gain，因此应描述为 co-derived diagnostic signal，不是完全独立验证。

### leaving-rate baseline

报告会比较 old top20 中：

```text
FP candidates leaving rate
non-FP candidates leaving rate
```

这比单独写 “9/12 left top20” 更稳。

### dense-cell edge case

如果 building density > 0.85 的 cells 很少，TP_0945 可以作为 isolated edge case 写入 limitation。若数量很多，则需要重新思考 dense built-up cells 的 pedestrian exposure representation。
