# OpenHeat v10-delta overhead sensitivity patch

解压到项目根目录后运行：

```bat
scripts\v10_delta_run_overhead_qa_pipeline.bat
```

检查 overhead QA 报告。如果 overhead layer 合理，再运行：

```bat
scripts\v10_delta_run_overhead_forecast_and_compare.bat
```

核心输出：

```text
outputs/v10_overhead_qa/v10_overhead_cell_QA_report.md
outputs/v10_overhead_sensitivity/v10_delta_grid_overhead_merge_QA_report.md
outputs/v10_delta_overhead_comparison/v10_base_vs_overhead_sensitivity_comparison.md
```

这不是最终 hazard map，而是 v10-gamma base ranking 的 overhead infrastructure sensitivity。高架桥面热和桥下行人遮阴必须分开解释。
